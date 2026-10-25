"""Entradas, inferência congelada e emissões imutáveis da operação 2026."""
import csv
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import warnings

import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from treinar_modelo_v1 import ENTRADAS_AUTORIZADAS, _matriz, classificar_previsoes, motivos_inelegibilidade
from avaliar_modelo_v1 import _fingerprint_pipeline, _verificar_metadados

HASH_MODELO = '16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3'
HASH_META = '77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6'
HASH_ESQUEMA = '1b14e532cd3001ad6b38442cab4a14e52e63208fbe37bec77d8b464dfb98efdd'
CONSTANTE = 0.15011372251705837
TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
COMPONENTES_OPERACIONAIS = (
    'operacao2026/__init__.py', 'operacao2026/previsao.py', 'operar_2026.py',
    'operacao2026/fontes.py', 'operacao2026/fastf1_contexto.py',
    'operacao2026/openf1_qualificacao.py',
)
HELPERS_CONGELADOS = ('treinar_modelo_v1.py', 'avaliar_modelo_v1.py')


def _utc(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError('Timestamp deve ter fuso UTC explícito.')
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        raise ValueError('UTC obrigatório.')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Timestamp UTC inválido: {}'.format(value)) from error
    if parsed.tzinfo is None:
        raise ValueError('Timestamp deve ter fuso UTC explícito.')
    return parsed.astimezone(timezone.utc)


def _z(value):
    return _utc(value).isoformat().replace('+00:00', 'Z')


def _event_key(race):
    return (str(race['season']), str(race['round']))


def validar_id(value, label='ID'):
    """Aceita somente o identificador literal canônico; nunca o normaliza."""
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('{} inválido.'.format(label))
    return value


def _race_start(race):
    try:
        return _utc('{}T{}'.format(race['date'], race['time']))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Data/horário UTC da corrida inválido.') from error


def _reference(race, exigir_horario=False):
    q = race.get('Qualifying') or {}
    if not q.get('date'):
        return None
    time = q.get('time')
    if exigir_horario and not time:
        raise ValueError('Horário UTC de Qualifying é obrigatório no modo prospectivo.')
    if time and (not isinstance(time, str) or not time.endswith('Z')):
        raise ValueError('Horário de Qualifying deve ser UTC com Z.')
    text = q['date'] + 'T' + (time[:-1] if time else '00:00:00') + '+00:00'
    try:
        reference = datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError as error:
        raise ValueError('Data/horário de Qualifying inválido.') from error
    if reference >= _race_start(race):
        raise ValueError('Sessão de referência posterior ou igual à corrida.')
    return reference


def validar_identidade(evento, pagina):
    """A página de Q ou resultados deve ser exatamente a corrida do calendário."""
    expected = (_event_key(evento), evento['date'], evento['Circuit']['circuitId'])
    received = (_event_key(pagina), pagina.get('date'), pagina.get('Circuit', {}).get('circuitId'))
    if received != expected:
        raise ValueError('Identidade da página diverge do calendário (ano/rodada/data/circuito).')


def preparar_alvo(evento, registros_q, prospectivo=False):
    """A população é exclusivamente a classificação principal admitida."""
    ref = _reference(evento, exigir_horario=prospectivo)
    if not registros_q:
        return {'estado': 'aguardando_classificacao', 'evento': evento, 'referencia_utc': ref, 'registros': []}
    if ref is None:
        raise ValueError('Classificação disponível sem referência temporal de calendário.')
    rows, ids, positions = [], set(), {}
    for item in registros_q:
        try:
            driver = item['Driver']['driverId']
            team = item['Constructor']['constructorId']
        except (KeyError, TypeError) as error:
            raise ValueError('Qualifying com ID de piloto/equipe inválido.') from error
        try:
            validar_id(driver, 'ID de piloto'); validar_id(team, 'ID de equipe')
        except ValueError as error:
            raise ValueError('Qualifying com ID de piloto/equipe inválido.') from error
        if driver in ids:
            raise ValueError('piloto duplicado na classificação.')
        ids.add(driver)
        p = item.get('position')
        if p in (None, ''):
            pos = None
        else:
            try:
                pos = int(p)
            except (TypeError, ValueError) as error:
                raise ValueError('Posição de classificação inválida.') from error
            if pos <= 0:
                raise ValueError('Posição de classificação inválida.')
            positions.setdefault(pos, []).append(driver)
        rows.append({'temporada': str(evento['season']), 'rodada': str(evento['round']), 'piloto_id': driver,
                     'corrida': evento.get('raceName', ''), 'data_corrida': evento['date'],
                     'circuito_id': evento['Circuit']['circuitId'],
                     'piloto': '{} {}'.format(item['Driver'].get('givenName', ''), item['Driver'].get('familyName', '')).strip(),
                     'equipe_id': team, 'equipe_id_entrada': team, 'posicao_classificacao': pos,
                     'classificacao_ausente': 0, 'posicao_classificacao_ausente': int(pos is None),
                     'referencia_temporal_ausente': 0,
                     'limite_inferior_referencia_utc': _z(ref)})
    repeated = {p for p, drivers in positions.items() if len(drivers) > 1}
    for row in rows:
        row['posicao_classificacao_repetida'] = int(row['posicao_classificacao'] in repeated)
    return {'estado': 'pronto', 'evento': evento, 'referencia_utc': ref, 'registros': rows}


def _release(race):
    return datetime.combine(date.fromisoformat(race['date']) + timedelta(days=1), datetime.min.time(), timezone.utc)


def chaves_historicas_admitidas(alvo, calendario):
    if alvo['estado'] != 'pronto':
        return []
    key = _event_key(alvo['evento'])
    by_key = {_event_key(r): r for r in calendario}
    if key not in by_key:
        raise ValueError('Alvo ausente do calendário.')
    target_start = _race_start(alvo['evento'])
    ordered = sorted(calendario, key=lambda r: (_race_start(r), int(r['season']), int(r['round'])))
    return [_event_key(r) for r in ordered
            if _event_key(r) != key and _race_start(r) < target_start and _release(r) <= alvo['referencia_utc']]


def gerar_entradas(alvo, calendario, resultados_por_gp):
    """Gera as 15 entradas; um leitor chamável só recebe chaves já admitidas.

    O chamador operacional passa um leitor de arquivos. Assim, resultados do
    alvo/futuros não são sequer abertos para montar a matriz.
    """
    if alvo['estado'] != 'pronto':
        return [], {'resultados_lidos': [], 'janelas': []}
    admissible = chaves_historicas_admitidas(alvo, calendario)
    history = []
    for hkey in admissible:
        rows = resultados_por_gp(hkey) if callable(resultados_por_gp) else resultados_por_gp.get(hkey)
        if rows is None:
            continue
        seen = set()
        for entry in rows:
            try:
                driver = entry['Driver']['driverId']
                team = entry['Constructor']['constructorId']
                pos = int(entry['position'])
                points = Decimal(str(entry['points']))
            except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                raise ValueError('Resultado histórico inválido.') from error
            if driver in seen or pos <= 0 or points < 0 or not points.is_finite():
                raise ValueError('Piloto duplicado ou resultado histórico inválido.')
            try:
                validar_id(driver, 'ID de piloto'); validar_id(team, 'ID de equipe')
            except ValueError as error:
                raise ValueError('Resultado histórico inválido.') from error
            seen.add(driver)
        history.append((hkey, rows))
    output, audit = [], {'resultados_lidos': [key for key, _ in history], 'janelas': []}
    for raw in alvo['registros']:
        row = dict(raw)
        driver, team = row['piloto_id'], row['equipe_id_entrada']
        d = [(k, x) for k, rs in history for x in rs if x['Driver']['driverId'] == driver][-5:]
        event_teams = []
        for k, rs in history:
            members = [x for x in rs if x['Constructor']['constructorId'] == team]
            if members:
                event_teams.append((k, members))
        event_teams = event_teams[-5:]
        members = [x for _, rs in event_teams for x in rs]
        n, ne = len(d), len(members)
        row.update({'media_posicao_final_5': sum(int(x['position']) for _, x in d) / n if n else None,
                    'taxa_podios_5': sum(int(x['position']) <= 3 for _, x in d) / n if n else None,
                    'n_posicoes_5': n, 'n_podios_5': n,
                    'media_pontos_equipe_5': float(sum((Decimal(str(x['points'])) for x in members), Decimal(0)) / ne) if ne else None,
                    'n_corridas_equipe_5': len(event_teams), 'n_participacoes_equipe_5': ne,
                    'historico_piloto_insuficiente': int(n < 5), 'historico_equipe_insuficiente': int(len(event_teams) < 5),
                    'equipe_pre_corrida_ausente': 0})
        output.append(row)
        audit['janelas'].append({'piloto_id': driver, 'piloto': [list(k) for k, _ in d],
                                 'equipe': [{'evento': list(k), 'participacoes': len(rs)} for k, rs in event_teams]})
    return output, audit


def selecionar_fontes_historicas(audit, fontes_historicas):
    """Seleciona proveniência legada pelas janelas v1 já calculadas.

    A leitura integral continua auditável em ``resultados_lidos``. A seleção
    abaixo somente define quais raws congelados contribuem às cinco últimas
    participações do piloto ou aos cinco GPs da equipe, sem corte arbitrário
    por ano ou rodada.
    """
    necessarias = set()
    for janela in audit.get('janelas', []):
        necessarias.update(tuple(key) for key in janela.get('piloto', []))
        necessarias.update(tuple(item['evento']) for item in janela.get('equipe', []))
    anos = {key[0] for key in necessarias}
    admitidas, excluidas = [], []
    for original in fontes_historicas:
        source = dict(original)
        eventos = {tuple(key) for key in source.get('eventos', [])}
        temporadas = {str(year) for year in source.get('temporadas', [])}
        contribui = ((source.get('endpoint') == 'resultados' and bool(eventos & necessarias)) or
                     (source.get('endpoint') == 'calendario' and bool(temporadas & anos)))
        if contribui:
            admitidas.append(source)
        else:
            source['motivo_exclusao'] = 'ausência de contribuição às janelas v1'
            excluidas.append(source)
    return admitidas, excluidas, sorted(necessarias)


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def carregar_historico_bruto(root='data/historico', auditoria=False):
    """Lê somente calendário/resultados brutos 2021--2025 e confere manifestos."""
    calendar, results, sources = [], {}, []
    base = Path(root)
    for year in range(2021, 2026):
        folder = base / str(year)
        manifest = json.loads((folder / 'manifesto.json').read_text(encoding='utf-8'))
        for source in manifest.get('proveniencia', []):
            endpoint = source.get('endpoint')
            if endpoint not in ('calendario', 'resultados'):
                continue
            raw = (folder / source['arquivo']).read_bytes()
            if sha256(raw).hexdigest() != source.get('sha256'):
                raise ValueError('Hash histórico divergente: {}'.format(source['arquivo']))
            try:
                races = json.loads(raw.decode('utf-8'))['MRData']['RaceTable']['Races']
            except (UnicodeDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError('Página histórica inválida: {}'.format(source['arquivo'])) from error
            eventos = [_event_key(race) for race in races]
            admitted = dict(source)
            admitted.update({'arquivo': str(Path(str(year)) / source['arquivo']), 'sha256': sha256(raw).hexdigest(),
                             'origem': 'historico_congelado',
                             'eventos': [list(key) for key in eventos],
                             'temporadas': sorted({key[0] for key in eventos})})
            sources.append(admitted)
            for race in races:
                key = _event_key(race)
                if endpoint == 'calendario':
                    calendar.append(race)
                else:
                    bucket = results.setdefault(key, [])
                    existing = {x['Driver']['driverId'] for x in bucket}
                    for record in race.get('Results', []):
                        driver = record.get('Driver', {}).get('driverId')
                        if driver in existing:
                            raise ValueError('Resultado histórico duplicado: {}'.format(key))
                        try:
                            validar_id(driver, 'ID de piloto')
                            validar_id(record.get('Constructor', {}).get('constructorId'), 'ID de equipe')
                        except ValueError as error:
                            raise ValueError('Resultado histórico inválido: {}'.format(key)) from error
                        bucket.append(record)
                        existing.add(driver)
    keys = [_event_key(x) for x in calendar]
    if len(keys) != len(set(keys)) or set(keys) != set(results):
        raise ValueError('Histórico calendário/resultados incompleto ou duplicado.')
    if auditoria:
        return calendar, results, sources
    return calendar, results


@contextmanager
def _sem_fit():
    classes = (Pipeline, SimpleImputer, StandardScaler, LogisticRegression)
    saved = {}
    def blocked(*args, **kwargs):
        raise RuntimeError('fit é proibido na inferência operacional.')
    for cls in classes:
        for name in ('fit', 'fit_transform', 'partial_fit'):
            if hasattr(cls, name):
                saved[(cls, name)] = getattr(cls, name)
                setattr(cls, name, blocked)
    try:
        yield
    finally:
        for (cls, name), method in saved.items():
            setattr(cls, name, method)


def carregar_modelo(modelo='models/modelo_v1/modelo.joblib', metadados='models/modelo_v1/metadados.json', esquema='data/preparado/colunas.json'):
    if _sha(modelo) != HASH_MODELO or _sha(metadados) != HASH_META or _sha(esquema) != HASH_ESQUEMA:
        raise ValueError('Hash de artefato congelado divergente.')
    meta = json.loads(Path(metadados).read_text(encoding='utf-8'))
    schema = json.loads(Path(esquema).read_text(encoding='utf-8'))
    if meta.get('constante_treino') != CONSTANTE:
        raise ValueError('Constante congelada divergente.')
    with _sem_fit():
        payload = joblib.load(modelo)
    if not isinstance(payload, dict) or payload.get('entradas') != ENTRADAS_AUTORIZADAS:
        raise ValueError('Joblib v1 inválido.')
    pipeline = payload.get('pipeline')
    before = _verificar_metadados(meta, schema, pipeline)
    return {'pipeline': pipeline, 'meta': meta, 'schema': schema, 'fingerprint': before,
            'hashes': {'modelo': HASH_MODELO, 'metadados': HASH_META, 'esquema': HASH_ESQUEMA}}


def inferir(contexto, rows):
    eligible = [r for r in rows if not motivos_inelegibilidade(r)]
    with _sem_fit(), threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)
        probabilities = contexto['pipeline'].predict_proba(_matriz(eligible, contexto['schema']))[:, 1] if eligible else []
    by_id = {id(row): float(prob) for row, prob in zip(eligible, probabilities)}
    output = []
    for original in rows:
        row = dict(original)
        reasons = motivos_inelegibilidade(row)
        row.update({'elegivel_previsao': not reasons, 'motivos_inelegibilidade': ';'.join(reasons),
                    'probabilidade_modelo': by_id.get(id(original)), 'probabilidade_constante': CONSTANTE if not reasons else None})
        output.append(row)
    # O helper congelado espera NaN para ordenar Q ausente, mas o contrato da
    # emissão preserva None (JSON válido) nas entradas e saídas operacionais.
    para_ranking = []
    for row in output:
        copy = dict(row)
        if copy['posicao_classificacao'] is None:
            copy['posicao_classificacao'] = float('nan')
        para_ranking.append(copy)
    classificar_previsoes(para_ranking)
    rank_fields = ('ranking_modelo', 'favorito_modelo', 'ranking_classificacao',
                   'favorito_classificacao', 'empates_modelo', 'empates_classificacao')
    for row, ranked in zip(output, para_ranking):
        row.update({field: ranked.get(field) for field in rank_fields})
    after = _verificar_metadados(contexto['meta'], contexto['schema'], contexto['pipeline'])
    if after != contexto['fingerprint'] or _sha('models/modelo_v1/modelo.joblib') != HASH_MODELO:
        raise ValueError('Modelo alterado durante inferência.')
    return output


def validar_prospectivo(race_start, qualifying_start, session_end, obtido, corte, now=None):
    # Compatibilidade com a chamada v0 de cinco argumentos, usada apenas em
    # testes legados: o quinto datetime era ``now`` e o corte era a obtenção.
    if now is None and isinstance(corte, datetime):
        now, corte = corte, obtido
    now = _utc(now or datetime.now(timezone.utc))
    race, qstart, ended, got, cutoff = (_utc(x) for x in (race_start, qualifying_start, session_end, obtido, corte))
    if now >= race:
        raise ValueError('Emissão prospectiva recusada após a largada.')
    if not qstart <= ended <= got <= cutoff <= now:
        raise ValueError('Ordem prospectiva inválida: exige Q-início ≤ fim ≤ obtenção ≤ corte ≤ emissão < largada.')


def _bytes_json(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _csv(rows):
    fields = ['temporada', 'rodada', 'piloto_id', 'corrida', 'circuito_id', 'equipe_id_entrada', 'posicao_classificacao', 'elegivel_previsao', 'motivos_inelegibilidade', 'probabilidade_modelo', 'probabilidade_constante', 'ranking_modelo', 'favorito_modelo', 'ranking_classificacao', 'favorito_classificacao', 'empates_modelo', 'empates_classificacao']
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def _token(value, label):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('{} deve ser token seguro (letras, números, _ ou -).'.format(label))
    return value


def _safe_destination(root, emission_id):
    _token(emission_id, 'ID da emissão')
    parent = Path(root).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / emission_id
    if destination.parent != parent or destination.exists() or destination.is_symlink():
        raise FileExistsError('Emissão já existe ou destino inseguro: {}'.format(destination))
    return parent, destination


def _relatorio(data, lines):
    event = data.get('evento', {})
    coverage = data.get('cobertura', {})
    return ('# Operação 2026\n\nModo: {modo}\n\nEvento: {season}/{round} — {circuit}.\n\n'
            'Linhas da classificação admitida: {total}; elegíveis: {eligible}.\n\n'
            'Lacunas relevantes de resultados anteriores: {gaps}.\n\n'
            'Política de lacunas: {policy}.\n\n'
            'Limites: {limits}\n').format(modo=data.get('modo', ''), season=event.get('temporada', ''),
                                             round=event.get('rodada', ''), circuit=event.get('circuito_id', ''),
                                             total=len(lines), eligible=sum(bool(x.get('elegivel_previsao')) for x in lines),
                                             gaps=json.dumps(coverage.get('lacunas_resultados_relevantes', []), ensure_ascii=False),
                                             policy=data.get('politica_lacunas_resultados', ''),
                                             limits='; '.join(data.get('limites', [])))


def gravar_emissao(root, emission_id, data, validar_publicacao=None):
    """Cria uma emissão exclusiva após preparar todo o lote em memória."""
    if data.get('modo') == 'PROSPECTIVO' and validar_publicacao is None:
        raise ValueError('Emissão prospectiva exige validação de publicação em tempo real.')
    if bool(data.get('versao_anterior')) != bool(data.get('motivo_correcao')):
        raise ValueError('Correção exige versão anterior e motivo juntos.')
    if data.get('versao_anterior'):
        _token(data['versao_anterior'], 'Versão anterior')
    parent, dest = _safe_destination(root, emission_id)
    lines = list(data.get('linhas', []))
    entradas = {'ordem': ENTRADAS_AUTORIZADAS,
                'matriz': [{name: row.get(name) for name in ENTRADAS_AUTORIZADAS} for row in lines],
                'linhas': lines}
    cobertura = data.get('cobertura', {'registros_classificacao': len(lines),
                                       'elegiveis': sum(bool(x.get('elegivel_previsao')) for x in lines)})
    files = {'probabilidades.csv': _csv(lines), 'entradas.json': _bytes_json(entradas),
             'cobertura.json': _bytes_json(cobertura), 'historicos.json': _bytes_json(data.get('historicos_usados', {})),
             'fontes.json': _bytes_json(data.get('fontes', [])), 'relatorio.md': _relatorio(data, lines).encode('utf-8')}
    for rel, raw in data.get('raw_admitidos', {}).items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or path.suffix != '.json':
            raise ValueError('Nome de raw admitido inseguro.')
        files[str(Path('raw') / path.name)] = raw
    manifest = dict(data)
    manifest.pop('linhas', None)
    manifest.pop('raw_admitidos', None)
    manifest['hashes_saidas'] = {name: sha256(raw).hexdigest() for name, raw in files.items()}
    staging = parent / '.parcial-{}-{}'.format(emission_id, os.urandom(8).hex())
    publicado = False
    try:
        os.mkdir(staging)
        for name, raw in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(raw)
        if validar_publicacao is not None:
            emitted = validar_publicacao()
            manifest['emitido_em_utc'] = _z(emitted)
        manifest_raw = _bytes_json(manifest)
        with (staging / 'manifesto.json').open('xb') as handle:
            handle.write(manifest_raw)
        if validar_publicacao is not None:
            validar_publicacao()
        os.replace(staging, dest)
        publicado = True
        if validar_publicacao is not None:
            validar_publicacao()
    except Exception:
        if publicado:
            # A publicação cruzou a fronteira temporal: preserva somente este
            # lote recém-publicado como evidência parcial, nunca uma emissão
            # anterior que já existisse no destino.
            invalida = parent / '.parcial-invalida-{}-{}'.format(emission_id, os.urandom(8).hex())
            try:
                os.replace(dest, invalida)
            except OSError as cleanup_error:
                raise RuntimeError('Falha ao retirar emissão tardia do destino final.') from cleanup_error
        # A pasta parcial é evidência de falha, nunca é reutilizada/sobrescrita.
        raise
    return dest


def codigo_estado(root='.', componentes=COMPONENTES_OPERACIONAIS, helpers=HELPERS_CONGELADOS):
    base = Path(root)
    paths = tuple(componentes) + tuple(helpers)
    try:
        hashes = {path: _sha(base / path) for path in paths}
    except OSError:
        return {'commit': None, 'componentes_rastreados': False, 'componentes_limpos': False, 'sha256': {}}
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(base), text=True).strip()
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', '--'] + list(paths), cwd=str(base),
                                 capture_output=True, text=True).returncode == 0
        dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'] + list(paths), cwd=str(base)).returncode != 0
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'componentes_rastreados': False, 'componentes_limpos': False, 'sha256': hashes}
    return {'commit': commit, 'componentes_rastreados': tracked, 'componentes_limpos': not dirty, 'sha256': hashes}


def git_state(root='.'):
    """Compatibilidade: estado restrito aos componentes operacionais relevantes."""
    state = codigo_estado(root)
    return {'commit': state['commit'], 'dirty': not (state['componentes_rastreados'] and state['componentes_limpos']), **state}