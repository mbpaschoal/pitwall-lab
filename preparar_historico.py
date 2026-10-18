"""Variáveis históricas anteriores ao corte; nenhuma estimação ou treino de modelo."""
from datetime import date, datetime, timedelta, timezone
from collections import Counter, defaultdict
from decimal import Decimal
import csv
import hashlib
import io
import json
from pathlib import Path

from coletar_resultados import salvar_preservando

RAIZ = Path(__file__).resolve().parent

CHAVES = ['temporada', 'rodada', 'piloto_id']
ENTRADAS = ['posicao_classificacao', 'posicao_classificacao_repetida', 'classificacao_ausente', 'posicao_classificacao_ausente',
            'media_posicao_final_5', 'taxa_podios_5', 'n_posicoes_5', 'n_podios_5',
            'media_pontos_equipe_5', 'n_corridas_equipe_5', 'n_participacoes_equipe_5',
            'historico_piloto_insuficiente', 'historico_equipe_insuficiente',
            'equipe_pre_corrida_ausente', 'referencia_temporal_ausente']
ALVOS = ['podio']
IDENTIFICACAO = ['corrida', 'data_corrida', 'circuito_id', 'piloto', 'equipe_id',
                 'equipe_id_entrada', 'divisao', 'sessao_referencia',
                 'limite_inferior_referencia_utc', 'fim_sessao_referencia_utc',
                 'precisao_referencia', 'classificacao_nao_define_grid_gp']
AUDITORIA = ['posicao_final', 'pontos', 'status', 'grid_resultado', 'resultado_ausente']


def _inicio_utc(data, horario, campo):
    """Converte horário UTC explícito; ausência significa somente início do dia."""
    if horario in (None, ''):
        return datetime.fromisoformat(data + 'T00:00:00+00:00')
    if not isinstance(horario, str) or not horario.endswith('Z'):
        raise ValueError('Horário inválido em {}: use UTC com Z'.format(campo))
    try:
        return datetime.fromisoformat(data + 'T' + horario[:-1] + '+00:00').astimezone(timezone.utc)
    except ValueError as erro:
        raise ValueError('Horário inválido em {}'.format(campo)) from erro


def definir_referencia(corrida):
    """O início registrado é limite inferior do fim desconhecido, nunca o próprio fim."""
    legado = int(corrida['season']) in (2021, 2022) and bool(corrida.get('Sprint'))
    sessao = (corrida.get('Sprint') if legado else corrida.get('Qualifying')) or {}
    data = sessao.get('date')
    inicio = None
    horario_sessao = sessao.get('time')
    if data:
        inicio = _inicio_utc(data, horario_sessao, 'sessão de referência')
        if data > corrida['date']:
            raise ValueError('Sessão de referência posterior à corrida')
        if corrida.get('time'):
            corrida_inicio = _inicio_utc(corrida['date'], corrida['time'], 'corrida')
            if inicio >= corrida_inicio:
                raise ValueError('Sessão de referência não é anterior à corrida')
    return {'sessao_referencia': 'Sprint_2021_2022' if legado else 'Qualifying',
            'classificacao_nao_define_grid_gp': legado,
            'limite_inferior_referencia_utc': inicio.isoformat().replace('+00:00', 'Z') if inicio else None,
            'fim_sessao_referencia_utc': None,
            'precisao_referencia': 'inicio_sessao' if horario_sessao else 'inicio_dia' if data else 'desconhecida',
            'referencia_temporal_ausente': inicio is None}


def preparar(calendario, resultados, classificacoes):
    """Junção externa e janelas por participações anteriores ao limite conservador.

    Datas de liberação são uma regra do estudo (dia UTC seguinte ao GP), não
    timestamps de publicação oficial dos resultados. Não há imputação nem treino.
    """
    def chave(corrida):
        return corrida['season'], corrida['round']

    eventos = {}
    for corrida in calendario:
        k = chave(corrida)
        if k in eventos:
            raise ValueError('Calendário com duplicação de temporada/rodada: {}'.format(k))
        ano = int(corrida['season'])
        if ano not in range(2021, 2026):
            raise ValueError('Temporada fora do protocolo fixado: {}'.format(ano))
        if date.fromisoformat(corrida['date']).year != ano:
            raise ValueError('Ano/data incoerentes no calendário')
        eventos[k] = corrida

    por_resultado, por_classificacao = defaultdict(dict), defaultdict(dict)
    for fonte, campo, destino in [(resultados, 'Results', por_resultado),
                                  (classificacoes, 'QualifyingResults', por_classificacao)]:
        for corrida in fonte:
            k = chave(corrida)
            if k not in eventos:
                raise ValueError('Junção incoerente: corrida fora do calendário {}'.format(k))
            esperada = eventos[k]
            if (corrida['date'] != esperada['date'] or
                    corrida['Circuit']['circuitId'] != esperada['Circuit']['circuitId']):
                raise ValueError('Junção incoerente: data/circuito diferentes {}'.format(k))
            for registro in corrida[campo]:
                piloto = registro['Driver']['driverId']
                if piloto in destino[k]:
                    raise ValueError('Duplicação temporada/rodada/piloto: {}'.format(k + (piloto,)))
                destino[k][piloto] = registro
    if set(por_resultado) != set(eventos):
        raise ValueError('Resultados incompletos em relação ao calendário')
    repetidas_classificacao = {}
    for k, registros in por_classificacao.items():
        por_posicao = defaultdict(list)
        for piloto, registro in registros.items():
            if registro.get('position') not in (None, ''):
                posicao = int(registro['position'])
                if posicao < 1:
                    raise ValueError('Posição da classificação inválida: {}'.format(k))
                por_posicao[posicao].append(piloto)
        repetidas = {posicao: sorted(pilotos) for posicao, pilotos in por_posicao.items()
                     if len(pilotos) > 1}
        if repetidas:
            repetidas_classificacao[k] = repetidas
    for k, registros in por_resultado.items():
        posicoes = [int(r['position']) for r in registros.values()]
        if len(set(posicoes)) != len(posicoes) or not {1, 2, 3}.issubset(posicoes):
            raise ValueError('Posições finais duplicadas ou pódio incompleto: {}'.format(k))

    ordem = sorted(eventos, key=lambda k: (eventos[k]['date'], eventos[k].get('time', ''), int(k[0]), int(k[1])))
    liberacao = {k: (date.fromisoformat(eventos[k]['date']) + timedelta(days=1)).isoformat() + 'T00:00:00Z'
                 for k in ordem}
    linhas, janelas = [], []
    qualidade = {}
    for k in ordem:
        corrida = eventos[k]
        ref = definir_referencia(corrida)
        corte = ref['limite_inferior_referencia_utc']
        anteriores = [p for p in ordem if p != k and corte and liberacao[p] <= corte]
        r_atual, q_atual = por_resultado[k], por_classificacao[k]
        ano = k[0]
        if ano not in qualidade:
            qualidade[ano] = {'temporada': ano, 'corridas': 0, 'registros_resultados': 0,
                             'registros_classificacao': 0, 'linhas_preparadas': 0,
                             'classificacao_ausente': 0, 'posicao_classificacao_ausente': 0,
                             'linhas_posicao_classificacao_repetida': 0,
                             'posicoes_classificacao_repetidas': [],
                             'resultado_ausente': 0, 'referencia_temporal_ausente': 0,
                             'historico_piloto_n': Counter(), 'historico_equipe_corridas_n': Counter(),
                             'diferencas_participantes': [], 'por_corrida': []}
        qual = qualidade[ano]
        qual['corridas'] += 1
        qual['registros_resultados'] += len(r_atual)
        qual['registros_classificacao'] += len(q_atual)
        qual['por_corrida'].append({'rodada': k[1], 'resultados': len(r_atual),
                                    'classificacao': len(q_atual), 'podios': 3})
        for posicao, pilotos in sorted(repetidas_classificacao.get(k, {}).items()):
            qual['posicoes_classificacao_repetidas'].append(
                {'rodada': k[1], 'posicao': posicao, 'pilotos': pilotos},
            )
        diferenca = {'rodada': k[1], 'so_resultados': sorted(set(r_atual) - set(q_atual)),
                     'so_classificacao': sorted(set(q_atual) - set(r_atual))}
        if diferenca['so_resultados'] or diferenca['so_classificacao']:
            qual['diferencas_participantes'].append(diferenca)
        for piloto in sorted(set(r_atual) | set(q_atual)):
            atual, classificacao = r_atual.get(piloto), q_atual.get(piloto)
            if atual and classificacao and atual['Constructor']['constructorId'] != classificacao['Constructor']['constructorId']:
                raise ValueError('Junção incoerente: equipe diferente na classificação e corrida: {}'.format(k + (piloto,)))
            identidade = classificacao if classificacao is not None else atual
            assert identidade is not None  # União externa garante ao menos uma origem.
            equipe = classificacao['Constructor']['constructorId'] if classificacao else None
            # O resultado atual fornece somente alvo/auditoria. A equipe de entrada vem da classificação.
            hist_piloto = [(p, por_resultado[p][piloto]) for p in anteriores if piloto in por_resultado[p]][-5:]
            hist_equipe = [(p, [r for r in por_resultado[p].values() if r['Constructor']['constructorId'] == equipe])
                           for p in anteriores] if equipe else []
            hist_equipe = [(p, rs) for p, rs in hist_equipe if rs][-5:]
            participacoes = [r for _, grupo in hist_equipe for r in grupo]
            n, n_equipe = len(hist_piloto), len(participacoes)
            posicao_q = classificacao.get('position') if classificacao else None
            posicao_q_int = int(posicao_q) if posicao_q not in (None, '') else None
            posicao_classificacao_repetida = int(
                posicao_q_int in repetidas_classificacao.get(k, {}) if posicao_q_int is not None else False,
            )
            linha = dict(zip(CHAVES, [k[0], k[1], piloto]))
            linha.update({'corrida': corrida['raceName'], 'data_corrida': corrida['date'],
                          'circuito_id': corrida['Circuit']['circuitId'],
                          'piloto': identidade['Driver']['givenName'] + ' ' + identidade['Driver']['familyName'],
                          'equipe_id': identidade['Constructor']['constructorId'], 'equipe_id_entrada': equipe,
                          'divisao': 'treino' if int(ano) <= 2023 else 'validacao' if ano == '2024' else 'teste_final_reservado',
                          **ref,
                          'posicao_classificacao': posicao_q_int,
                          'posicao_classificacao_repetida': posicao_classificacao_repetida,
                          'classificacao_ausente': int(classificacao is None),
                          'posicao_classificacao_ausente': int(posicao_q in (None, '')),
                          'media_posicao_final_5': sum(int(r['position']) for _, r in hist_piloto) / n if n else None,
                          'taxa_podios_5': sum(int(r['position']) <= 3 for _, r in hist_piloto) / n if n else None,
                          'n_posicoes_5': n, 'n_podios_5': n,
                          'media_pontos_equipe_5': float(sum((Decimal(r['points']) for r in participacoes), Decimal(0)) / n_equipe) if n_equipe else None,
                          'n_corridas_equipe_5': len(hist_equipe), 'n_participacoes_equipe_5': n_equipe,
                          'historico_piloto_insuficiente': int(n < 5),
                          'historico_equipe_insuficiente': int(len(hist_equipe) < 5),
                          'equipe_pre_corrida_ausente': int(equipe is None),
                          'podio': int(int(atual['position']) <= 3) if atual else None,
                          'posicao_final': int(atual['position']) if atual else None,
                          'pontos': atual['points'] if atual else None,
                          'status': atual.get('status') if atual else None,
                          'grid_resultado': atual.get('grid') if atual else None,
                          'resultado_ausente': int(atual is None)})
            linhas.append(linha)
            janelas.append({**{c: linha[c] for c in CHAVES}, 'limite_inferior_referencia_utc': corte,
                            'piloto': [{'temporada': p[0], 'rodada': p[1], 'liberado_pelo_protocolo_utc': liberacao[p]} for p, _ in hist_piloto],
                            'equipe': [{'temporada': p[0], 'rodada': p[1], 'participacoes': len(rs), 'liberado_pelo_protocolo_utc': liberacao[p]} for p, rs in hist_equipe]})
            qual['linhas_preparadas'] += 1
            for campo in ('classificacao_ausente', 'posicao_classificacao_ausente', 'resultado_ausente', 'referencia_temporal_ausente'):
                qual[campo] += int(linha[campo])
            qual['linhas_posicao_classificacao_repetida'] += posicao_classificacao_repetida
            qual['historico_piloto_n'][str(n)] += 1
            qual['historico_equipe_corridas_n'][str(len(hist_equipe))] += 1
    return {'linhas': linhas, 'auditoria_janelas': janelas, 'qualidade': qualidade}


def gravar_preparacao(info, saida, relatorios, fontes_sha256=None):
    """Relatórios só de integridade; preflight de todo o lote, comprovante por último."""
    def csv_texto(colunas, linhas):
        buffer = io.StringIO(newline='')
        escritor = csv.DictWriter(buffer, fieldnames=colunas, lineterminator='\n', extrasaction='ignore')
        escritor.writeheader()
        escritor.writerows(linhas)
        return buffer.getvalue()

    def json_texto(valor):
        return json.dumps(valor, ensure_ascii=False, indent=2, sort_keys=True) + '\n'

    linhas = info['linhas']
    colunas = CHAVES + IDENTIFICACAO + ENTRADAS + ALVOS + AUDITORIA
    if len(set(colunas)) != len(colunas):
        raise ValueError('Papéis de colunas sobrepostos')
    schema = {'chaves': CHAVES, 'identificacao': IDENTIFICACAO, 'entradas': ENTRADAS,
              'alvos': ALVOS, 'auditoria_proibida_como_entrada': AUDITORIA,
              'nulos_csv': 'campo vazio', 'protocolo': 'docs/protocolo_temporal.md',
              'dicionario': 'docs/dicionario_variaveis.md'}
    tabelas = {'base_historica.csv': csv_texto(colunas, linhas),
               'identificacao.csv': csv_texto(CHAVES + IDENTIFICACAO, linhas),
               'entradas.csv': csv_texto(CHAVES + ENTRADAS, linhas),
               'alvos.csv': csv_texto(CHAVES + ALVOS, linhas),
               'auditoria_resultados.csv': csv_texto(CHAVES + AUDITORIA, linhas),
               'colunas.json': json_texto(schema),
               'auditoria_janelas.json': json_texto(info['auditoria_janelas'])}
    for divisao in ['treino', 'validacao', 'teste_final_reservado']:
        tabelas[divisao + '.csv'] = csv_texto(colunas, [l for l in linhas if l['divisao'] == divisao])
    corridas = {}
    for linha in linhas:
        k = (linha['temporada'], linha['rodada'])
        evento = {c: linha[c] for c in ['temporada', 'rodada', 'data_corrida', 'divisao']}
        if k in corridas and corridas[k] != evento:
            raise ValueError('Pilotos da mesma corrida têm divisões ou datas diferentes')
        corridas[k] = evento
    tabelas['divisoes.csv'] = csv_texto(['temporada', 'rodada', 'data_corrida', 'divisao'], corridas.values())

    resumo_md = ['# Qualidade da base histórica — etapa 3',
                 'Somente integridade, cobertura e disponibilidade de histórico. Nenhum modelo treinado ou desempenho medido, inclusive em 2025.',
                 '| Temporada | GPs | Resultados | Classificação | União preparada | Sem classificação | Sem posição de classificação | Posições repetidas/ambíguas | Linhas sinalizadas | Sem resultado |',
                 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    textos = {}
    for ano, q in sorted(info['qualidade'].items()):
        resumo_md.append('| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |'.format(
            ano, q['corridas'], q['registros_resultados'], q['registros_classificacao'],
            q['linhas_preparadas'], q['classificacao_ausente'], q['posicao_classificacao_ausente'],
            len(q['posicoes_classificacao_repetidas']), q['linhas_posicao_classificacao_repetida'], q['resultado_ausente']))
        partes = ['# Qualidade — temporada {}'.format(ano),
                  '**2025 é teste final reservado: este relatório não mede desempenho.**' if ano == '2025' else 'Relatório de integridade e cobertura, não desempenho de previsão.',
                  'GPs: {}. Registros de resultados: {}. Registros de classificação: {}. Linhas na união: {}. Duplicações: 0 (inconsistências bloqueiam a preparação).'.format(q['corridas'], q['registros_resultados'], q['registros_classificacao'], q['linhas_preparadas']),
                  'Sem registro de classificação: {}. Sem posição de classificação: {}. Posições repetidas/ambíguas: {} ocorrência(s), {} linha(s) sinalizada(s). Sem resultado/alvo conhecido: {}. Sem referência temporal: {}.'.format(q['classificacao_ausente'], q['posicao_classificacao_ausente'], len(q['posicoes_classificacao_repetidas']), q['linhas_posicao_classificacao_repetida'], q['resultado_ausente'], q['referencia_temporal_ausente']),
                  '## Histórico disponível por linha',
                  '| Observações anteriores | Linhas: piloto | Linhas: GPs da equipe |', '|---|---:|---:|']
        for n in range(6):
            partes.append('| {} | {} | {} |'.format(n, q['historico_piloto_n'].get(str(n), 0), q['historico_equipe_corridas_n'].get(str(n), 0)))
        partes += ['Contagem zero significa ausência de histórico na amostra, não necessariamente estreia. Pouco histórico não é completado com dados futuros.',
                   '## Cobertura por corrida', '| Rodada | Resultados | Classificação | Pódios para integridade |', '|---|---:|---:|---:|']
        for c in q['por_corrida']:
            partes.append('| {} | {} | {} | {} |'.format(c['rodada'], c['resultados'], c['classificacao'], c['podios']))
        partes += ['## Posições de classificação repetidas/ambíguas',
                   'A posição original da classificação é preservada em todas as linhas. Quando dois ou mais pilotos têm a mesma posição, `posicao_classificacao_repetida=1` sinaliza a ambiguidade. Não inferimos posição única nem substituímos pelo grid dos resultados.',
                   '| Rodada | Ocorrência preservada |', '|---|---|']
        for repetida in q['posicoes_classificacao_repetidas']:
            partes.append('| {} | posição {}: {} |'.format(repetida['rodada'], repetida['posicao'], ', '.join(repetida['pilotos'])))
        if not q['posicoes_classificacao_repetidas']:
            partes.append('| — | nenhuma |')
        partes += ['## Participantes sem correspondência',
                   'Listamos todos os IDs sem correspondência. Ausência não prova sua causa: retirada, substituição e revisões de classificação são possibilidades, não conclusões automáticas. Sem resultado, o alvo fica desconhecido; sem classificação, a posição e a equipe pré-corrida ficam ausentes. Nenhuma linha é removida.',
                   '| Rodada | Apenas nos resultados (sem classificação) | Apenas na classificação (sem resultado) |', '|---|---|---|']
        for d in q['diferencas_participantes']:
            partes.append('| {} | {} | {} |'.format(d['rodada'], ', '.join(d['so_resultados']) or 'nenhum', ', '.join(d['so_classificacao']) or 'nenhum'))
        if not q['diferencas_participantes']:
            partes.append('| — | nenhum | nenhum |')
        partes += ['## Limites e rastreabilidade',
                   'A completude é relativa ao calendário e aos totais das respostas preservadas, não uma auditoria independente de todos os documentos esportivos. Verifique os manifestos em `data/historico/{}/`. Não presumimos vinte registros por GP.'.format(ano),
                   'Datas de coleta desconhecidas continuam desconhecidas. O fim das sessões não foi inventado. As janelas usam o protocolo conservador descrito em `docs/protocolo_temporal.md`; os dados históricos podem conter revisões posteriores ao corte.',
                   'O dicionário em `docs/dicionario_variaveis.md` define os denominadores, os IDs de equipe e o tratamento de não largadas/desclassificações.']
        texto = ''
        anterior_tabela = False
        for parte in partes:
            tabela = parte.startswith('|')
            texto += ('\n' if tabela and anterior_tabela else '\n\n') + parte
            anterior_tabela = tabela
        textos['qualidade_{}.md'.format(ano)] = texto.lstrip() + '\n'
    resumo_md += ['', '2024 já foi explorado na etapa 2 e é validação, não teste intocado. A preparação de 2025 é mecânica e não orienta escolhas de variáveis ou ajustes.',
                  'Todos os participantes das duas fontes permanecem na união externa. O universo é retrospectivo, não uma lista de inscritos congelada no corte.',
                  'Detalhes por temporada nos arquivos `qualidade_2021.md` a `qualidade_2025.md`. Metodologia e fontes em `docs/protocolo_temporal.md` e `docs/dicionario_variaveis.md`.']
    textos['qualidade.md'] = '\n'.join(resumo_md) + '\n'
    textos['qualidade.json'] = json_texto(info['qualidade'])
    destinos = [(saida / nome, texto) for nome, texto in tabelas.items()]
    destinos += [(relatorios / nome, texto) for nome, texto in textos.items()]
    comprovante = {'completa': True, 'versao_preparacao': 1, 'registros': len(linhas),
                   'corridas': len(corridas), 'por_temporada': info['qualidade'],
                   'fontes_sha256': fontes_sha256 or {},
                   'arquivos_sha256': {('dados/' if p.parent == saida else 'relatorios/') + p.name:
                                       hashlib.sha256(texto.encode('utf-8')).hexdigest() for p, texto in destinos}}
    destinos.append((saida / 'verificacao.json', json_texto(comprovante)))
    for caminho, texto in destinos:
        if caminho.exists() and caminho.read_bytes() != texto.encode('utf-8'):
            raise FileExistsError('Arquivo existente diferente: {}. Preserve um backup antes de regenerar; nada será sobrescrito.'.format(caminho))
    for caminho, texto in destinos:
        salvar_preservando(caminho, texto)
    return comprovante


def executar(raiz_dados=RAIZ / 'data/historico', saida=RAIZ / 'data/preparado',
             relatorios=RAIZ / 'reports/historico'):
    """Somente cache: nenhuma consulta de rede nem análise de desempenho."""
    from coletar_historico import carregar_temporada
    calendario, resultados, classificacoes = [], [], []
    fontes = {}
    for temporada in range(2021, 2026):
        conjunto = carregar_temporada(str(temporada), raiz_dados=raiz_dados)
        calendario.extend(conjunto['calendario'])
        resultados.extend(conjunto['resultados'])
        classificacoes.extend(conjunto['classificacao'])
        for arquivo in sorted((raiz_dados / str(temporada)).rglob('*.json')):
            fontes[str(arquivo.relative_to(raiz_dados))] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    info = preparar(calendario, resultados, classificacoes)
    comprovante = gravar_preparacao(info, saida, relatorios, fontes)
    print('PREPARAÇÃO COMPLETA: {} corridas, {} linhas. Sem treino de modelos; 2025 reservado.'.format(
        comprovante['corridas'], comprovante['registros']))
    return info


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasta-dados', type=Path, default=RAIZ / 'data/historico')
    parser.add_argument('--saida', type=Path, default=RAIZ / 'data/preparado')
    parser.add_argument('--relatorios', type=Path, default=RAIZ / 'reports/historico')
    args = parser.parse_args()
    try:
        executar(args.pasta_dados, args.saida, args.relatorios)
    except (OSError, ValueError) as erro:
        print('Falha na preparação: {}. Nenhuma base parcial foi declarada completa; preserve os arquivos antes de recuperar a coleta.'.format(erro), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Preparação interrompida; arquivos anteriores preservados.', file=sys.stderr)
        sys.exit(130)
