#!/usr/bin/env python3
"""CLI da operação 2026: coleta separada, estado, ensaio e emissão manual."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

from operacao2026 import fontes, previsao

ROOT = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / 'data/operacao_2026/snapshots'
EMISSOES = ROOT / 'reports/operacao_2026/emissoes'


def _fonte_api(name):
    try:
        return getattr(fontes, name)
    except AttributeError as error:
        raise RuntimeError('Interface de fontes pendente: {}. Não execute fluxo integrado antes da junção.'.format(name)) from error


def _races(pages):
    out = []
    for _, payload in pages:
        try:
            out.extend(payload['MRData']['RaceTable']['Races'])
        except (KeyError, TypeError) as error:
            raise ValueError('Página do snapshot sem envelope Jolpica válido.') from error
    return out


def _calendar(snapshot):
    index = _fonte_api('ler_indice')(SNAPSHOTS, snapshot)
    _, pages = _fonte_api('ler_snapshot')(SNAPSHOTS, snapshot, carregar=True, endpoints=['calendario'])
    calendar = _races(pages.get('calendario', []))
    if not calendar:
        raise ValueError('Snapshot sem calendário válido.')
    return index, calendar, pages


def _selecionar_snapshot(snapshot, endpoint, rodadas):
    """Lê endpoint/rodada canônicos; mocks v0 sem ``rodadas`` continuam legíveis."""
    reader = _fonte_api('ler_snapshot')
    rounds = {str(round_) for round_ in rodadas}
    try:
        return reader(SNAPSHOTS, snapshot, carregar=True, endpoints={endpoint}, rodadas=rounds)
    except TypeError as error:
        if 'rodadas' not in str(error):
            raise
        aliases = ['{}_{}'.format(endpoint, round_) for round_ in sorted(rounds, key=int)]
        index, legacy = reader(SNAPSHOTS, snapshot, carregar=True, endpoints=aliases)
        return index, {endpoint: [item for alias in aliases for item in legacy.get(alias, [])]}


def _event_with_q(snapshot, calendar, circuit, prospectivo=False):
    event = fontes.discover_event(calendar, circuit)
    endpoint = 'classificacao'
    _, pages = _selecionar_snapshot(snapshot, endpoint, {event['round']})
    qpages = pages.get(endpoint, [])
    q = []
    for race in _races(qpages):
        previsao.validar_identidade(event, race)
        q.extend(race.get('QualifyingResults', []))
    return event, endpoint, previsao.preparar_alvo(event, q, prospectivo=prospectivo), pages


def _resultados_2026(snapshot, calendar, alvo):
    keys = previsao.chaves_historicas_admitidas(alvo, calendar)
    rounds = {round_ for season, round_ in keys if season == '2026'}
    _, pages = _selecionar_snapshot(snapshot, 'resultados', rounds)
    results = {}
    for endpoint, entries in pages.items():
        if endpoint != 'resultados':
            continue
        for race in _races(entries):
            previsao.validar_identidade(next(item for item in calendar if previsao._event_key(item) == previsao._event_key(race)), race)
            key = previsao._event_key(race)
            bucket = results.setdefault(key, [])
            seen = {x['Driver']['driverId'] for x in bucket}
            for record in race.get('Results', []):
                driver = record.get('Driver', {}).get('driverId')
                if not driver or driver in seen:
                    raise ValueError('Paginação de resultados contém piloto duplicado.')
                bucket.append(record)
                seen.add(driver)
    return results, pages


def _fontes(index, pages):
    allowed = {entry['arquivo'] for entries in pages.values() for entry, _ in entries}
    return [entry for entry in index.get('fontes', []) if entry.get('arquivo') in allowed]


def _raw_admitidos(snapshot, pages):
    base = (SNAPSHOTS / snapshot).resolve()
    output = {}
    for entries in pages.values():
        for source, _ in entries:
            relative = Path(source['arquivo'])
            path = (base / relative).resolve()
            if path.parent != (base / 'raw').resolve() or not path.is_file():
                raise ValueError('Arquivo raw admitido fora do snapshot.')
            output[path.name] = path.read_bytes()
    return output


def _validar_fontes_prospectivas(pages, fontes_historicas, sessao_encerrada_em, corte):
    """Todas as fontes operacionais admitidas devem caber na janela observada."""
    encerramento, cutoff = previsao._utc(sessao_encerrada_em), previsao._utc(corte)
    for endpoint, entries in pages.items():
        for source, _ in entries:
            try:
                obtained = previsao._utc(source['obtido_em_utc'])
            except (KeyError, ValueError, TypeError) as error:
                raise ValueError('Fonte admitida sem obtenção UTC válida.') from error
            if obtained > cutoff:
                raise ValueError('Fonte admitida posterior ao corte prospectivo.')
            if endpoint == 'classificacao' and obtained < encerramento:
                raise ValueError('Página de classificação anterior ao encerramento confirmado.')
    for source in fontes_historicas:
        try:
            obtained = previsao._utc(source['obtido_em_utc'])
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError('Fonte histórica admitida sem obtenção UTC válida.') from error
        if obtained > cutoff:
            raise ValueError('Fonte histórica admitida posterior ao corte prospectivo.')


def _historicos(audit, results):
    def registros(keys):
        return [{'evento': list(key), 'resultados': results[key]}
                for key in keys if key in results]
    return {'janelas': audit['janelas'],
            'resultados_lidos': registros(audit.get('resultados_lidos', [])),
            'resultados_fornecidos': registros(audit.get('resultados_fornecidos', []))}


def _lacunas_resultados_anteriores(index, alvo, calendar, results):
    """Bloqueia indisponibilidade conhecida em GPs já admitidos ao alvo."""
    quality = index.get('qualidade', {})
    declared = quality.get('lacunas_resultados', []) if isinstance(quality, dict) else []
    declared = {str(round_) for round_ in declared if isinstance(round_, (str, int))}
    gaps = []
    for key in previsao.chaves_historicas_admitidas(alvo, calendar):
        if key[0] != '2026':
            continue
        causes = []
        if key[1] in declared:
            causes.append('índice registra resultado indisponível')
        if key not in results or not results[key]:
            causes.append('resultado indisponível no snapshot selecionado')
        if causes:
            gaps.append({'temporada': key[0], 'rodada': key[1], 'causa': '; '.join(causes)})
    if gaps:
        detail = '; '.join('rodada {}: {}'.format(item['rodada'], item['causa']) for item in gaps)
        raise ValueError('Lacuna de resultado anterior bloqueia a emissão: {}.'.format(detail))
    return gaps


def _emissao_data(mode, event, index, pages, lines, audit, results, model, extra):
    lacunas = list(audit.get('lacunas_resultados_relevantes', []))
    data = {'versao': 'operacao_2026_v1', 'modo': mode,
            'evento': {'temporada': str(event['season']), 'rodada': str(event['round']),
                       'circuito_id': event['Circuit']['circuitId']},
            'source_snapshots': [index['snapshot_id']], 'fontes': _fontes(index, pages),
            'raw_admitidos': _raw_admitidos(index['snapshot_id'], pages), 'historicos_usados': _historicos(audit, results),
            'fontes_historicas_admitidas': list(audit.get('fontes_historicas_admitidas', [])),
            'fontes_historicas_excluidas': list(audit.get('fontes_historicas_excluidas', [])),
            'fontes_historicas_abertas': list(audit.get('fontes_historicas_abertas', [])),
            'cobertura': {'registros_classificacao': len(lines),
                          'elegiveis': sum(bool(x.get('elegivel_previsao')) for x in lines),
                          'lacunas_resultados_relevantes': lacunas},
            'politica_lacunas_resultados': ('Bloqueio conservador: qualquer GP principal anterior admitido '
                                            'ao alvo sem resultado disponível bloqueia a emissão.'),
            'modelos': model['hashes'], 'git': previsao.codigo_estado(str(ROOT)), 'linhas': lines}
    data.update(extra)
    return data


def cmd_coletar(args):
    """A única rota de rede, delegada ao coletor sequencial de fontes."""
    dest = _fonte_api('coletar_snapshot')(SNAPSHOTS, snapshot_id=args.id, atualizar=args.atualizar,
                                         circuitos=args.classificacao_circuito)
    print('Snapshot criado: {}'.format(dest))


def cmd_estado(args):
    index, calendar, _ = _calendar(args.snapshot)
    event, _, state, _ = _event_with_q(args.snapshot, calendar, 'americas')
    print(json.dumps({'snapshot': index['snapshot_id'], 'austin': {'round': event['round'], 'date': event['date']},
                      'estado': state['estado'], 'registros_classificacao': len(state['registros'])}, ensure_ascii=False, indent=2))


def _preparar_fluxo(snapshot, circuit, prospectivo=False):
    index, calendar, calendar_pages = _calendar(snapshot)
    event, _, state, qpages = _event_with_q(snapshot, calendar, circuit, prospectivo=prospectivo)
    if state['estado'] != 'pronto':
        return index, calendar, event, state, {**calendar_pages, **qpages}, None, None, None
    historic = previsao.carregar_historico_bruto(str(ROOT / 'data/historico'), auditoria=True)
    if len(historic) == 2:  # Mocks legados continuam retornando somente calendário/resultados.
        historic_calendar, historic_results = historic
        fontes_historicas = []
    else:
        historic_calendar, historic_results, fontes_historicas = historic
    results_2026, result_pages = _resultados_2026(snapshot, calendar, state)
    results = dict(historic_results)
    results.update(results_2026)
    lacunas = _lacunas_resultados_anteriores(index, state, calendar, results_2026)
    rows_completas, audit = previsao.gerar_entradas(state, historic_calendar + calendar, results)
    admitidas, excluidas, chaves_necessarias = previsao.selecionar_fontes_historicas(audit, fontes_historicas)
    resultados_fornecidos = {key: results[key] for key in chaves_necessarias if key in results}
    rows, audit_fornecido = previsao.gerar_entradas(state, historic_calendar + calendar, resultados_fornecidos)
    matriz_completa = [{name: row.get(name) for name in previsao.ENTRADAS_AUTORIZADAS} for row in rows_completas]
    matriz_fornecida = [{name: row.get(name) for name in previsao.ENTRADAS_AUTORIZADAS} for row in rows]
    if matriz_fornecida != matriz_completa:
        raise ValueError('Subconjunto histórico diverge da matriz v1 completa.')
    audit['resultados_fornecidos'] = audit_fornecido['resultados_lidos']
    audit['fontes_historicas_abertas'] = fontes_historicas
    audit['fontes_historicas_admitidas'] = admitidas
    audit['fontes_historicas_excluidas'] = excluidas
    audit['lacunas_resultados_relevantes'] = lacunas
    return index, calendar, event, state, {**calendar_pages, **qpages, **result_pages}, results, rows, audit


def cmd_ensaio(args):
    index, _, event, state, pages, results, rows, audit = _preparar_fluxo(args.snapshot, 'marina_bay')
    if state['estado'] != 'pronto':
        print('ENSAIO RETROSPECTIVO: aguardando classificação; nenhuma probabilidade emitida.')
        return
    model = previsao.carregar_modelo()
    probs = previsao.inferir(model, rows)
    eid = args.id or 'ensaio-{}-{}'.format(event['round'], datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    data = _emissao_data('ENSAIO_RETROSPECTIVO', event, index, pages, probs, audit, results, model, {
        'corte_historico_utc': previsao._z(state['referencia_utc']),
        'emitido_em_utc': previsao._z(datetime.now(timezone.utc)),
        'limites': ['Ensaio retrospectivo: obtenção atual não prova disponibilidade histórica.',
                    'Resultados do alvo e posteriores não foram abertos como entradas.']})
    print('ENSAIO RETROSPECTIVO: {}'.format(previsao.gravar_emissao(EMISSOES, eid, data)))


def _url(value):
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError('Fonte de encerramento deve ser URL http(s) válida.')
    return value


def cmd_emitir(args):
    _url(args.fonte_encerramento)
    index, _, event, state, pages, results, rows, audit = _preparar_fluxo(args.snapshot, 'americas', prospectivo=True)
    if state['estado'] != 'pronto':
        raise ValueError('Aguardando classificação de Austin; nenhuma probabilidade é emitida.')
    q_endpoint = 'classificacao'
    q_sources = _fontes(index, {q_endpoint: pages.get(q_endpoint, [])})
    if not q_sources:
        raise ValueError('Snapshot não contém proveniência da classificação de Austin.')
    try:
        obtained = max(previsao._utc(source['obtido_em_utc']) for source in q_sources)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Classificação sem obtenção UTC válida.') from error
    race_start = '{}T{}'.format(event['date'], event.get('time', ''))
    if not event.get('time'):
        raise ValueError('Austin sem horário de largada UTC; emissão prospectiva bloqueada.')
    now = datetime.now(timezone.utc)
    previsao.validar_prospectivo(race_start, state['referencia_utc'], args.sessao_encerrada_em, obtained, args.corte, now)
    _validar_fontes_prospectivas(pages, (audit or {}).get('fontes_historicas_admitidas', []),
                                 args.sessao_encerrada_em, args.corte)
    git = previsao.codigo_estado(str(ROOT))
    if not git['componentes_rastreados'] or not git['componentes_limpos']:
        raise ValueError('Emissão prospectiva exige componentes operacionais commitados e limpos.')
    model = previsao.carregar_modelo()
    probs = previsao.inferir(model, rows)
    # Checagem imediatamente anterior à escrita: inferência não pode atravessar a largada.
    emitido = datetime.now(timezone.utc)
    previsao.validar_prospectivo(race_start, state['referencia_utc'], args.sessao_encerrada_em, obtained, args.corte, emitido)
    data = _emissao_data('PROSPECTIVO', event, index, pages, probs, audit, results, model, {
        'sessao_qualifying_inicio_utc': previsao._z(state['referencia_utc']),
        'sessao_qualifying_encerrada_utc': previsao._z(args.sessao_encerrada_em),
        'fonte_encerramento': args.fonte_encerramento, 'corte_utc': previsao._z(args.corte),
        'obtido_classificacao_utc': previsao._z(obtained), 'emitido_em_utc': previsao._z(emitido), 'git': git,
        'versao_anterior': args.versao_anterior, 'motivo_correcao': args.motivo_correcao,
        'limites': ['Resultados do alvo e posteriores não foram abertos como entradas.']})
    def validar_publicacao():
        atual = datetime.now(timezone.utc)
        previsao.validar_prospectivo(race_start, state['referencia_utc'], args.sessao_encerrada_em,
                                     obtained, args.corte, atual)
        return atual
    print('EMISSÃO PROSPECTIVA: {}'.format(previsao.gravar_emissao(
        EMISSOES, args.id, data, validar_publicacao=validar_publicacao)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('coletar')
    p.add_argument('--id')
    p.add_argument('--atualizar', action='store_true')
    p.add_argument('--classificacao-circuito', action='append')
    p.set_defaults(func=cmd_coletar)
    p = sub.add_parser('estado')
    p.add_argument('--snapshot', required=True)
    p.set_defaults(func=cmd_estado)
    p = sub.add_parser('ensaio')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--id')
    p.set_defaults(func=cmd_ensaio)
    p = sub.add_parser('emitir')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--sessao-encerrada-em', required=True, help='UTC observado, por exemplo 2026-10-24T22:00:00Z')
    p.add_argument('--fonte-encerramento', required=True, help='URL da confirmação de encerramento observada')
    p.add_argument('--corte', required=True, help='UTC de admissão, após a coleta/classificação')
    p.add_argument('--versao-anterior')
    p.add_argument('--motivo-correcao')
    p.set_defaults(func=cmd_emitir)
    args = parser.parse_args(argv)
    if args.cmd == 'coletar' and args.classificacao_circuito is None:
        args.classificacao_circuito = ['americas', 'marina_bay']
    try:
        args.func(args)
    except (ValueError, RuntimeError, FileExistsError, OSError) as error:
        print('Operação bloqueada: {}'.format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())