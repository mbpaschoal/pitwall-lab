"""Gera o asset de apresentação Race Weekend a partir de fontes locais imutáveis."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from dashboard_dados import carregar_temporada
from operacao2026 import fontes, formula1dashboard_tempos
from registro_emissoes import carregar as carregar_registro_emissoes


SNAPSHOT_2026 = 'austin-pos-corrida-20261026T111018Z-r2'
SNAPSHOT_CLASSIFICACAO_PILOTOS_2026 = 'classificacao-pilotos-20261023T143930Z'
SNAPSHOT_FORMULA1DASHBOARD_AUSTIN = 'austin-tempos-f1dashboard-20261025T143617Z-r2'

MOTIVO_SEM_RESULTADO = (
    'snapshot local de resultados ausente; o calendário não prova que a corrida não foi concluída'
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def _utc(valor):
    if not isinstance(valor, str) or not valor.endswith('Z'):
        raise ValueError('UTC sem sufixo Z')
    return datetime.fromisoformat(valor.replace('Z','+00:00')).astimezone(timezone.utc)


def _nome(driver):
    given = str(driver.get('givenName', '')).strip()
    family = str(driver.get('familyName', '')).strip()
    nome = ' '.join(parte for parte in (given, family) if parte)
    return nome or None


def _identidades_historicas(root):
    path = root / 'data/preparado/identificacao.csv'
    identidades = {}
    with path.open(encoding='utf-8', newline='') as arquivo:
        for row in csv.DictReader(arquivo):
            temporada = int(row['temporada'])
            if temporada not in (2024, 2025):
                continue
            chave = '{}:{}:{}'.format(temporada, row['rodada'], row['piloto_id'])
            identidades[chave] = {
                'piloto': row['piloto'] or None,
                'equipe_id': row['equipe_id_entrada'] or row['equipe_id'] or None,
            }
    return identidades, path


def _nomes_equipes_historicas(root):
    """Lê o nome de Constructor no resultado local do mesmo GP, sem usar equipe atual."""
    nomes = {}
    for temporada in (2024, 2025):
        for path in sorted((root / 'data' / 'historico' / str(temporada) / 'raw').glob('resultados_*.json')):
            for corrida in _json(path)['MRData']['RaceTable'].get('Races', []):
                rodada = int(corrida['round'])
                for resultado in corrida.get('Results', []):
                    piloto_id = resultado['Driver']['driverId']
                    equipe = resultado['Constructor'].get('name') or None
                    chave = '{}:{}:{}'.format(temporada, rodada, piloto_id)
                    anterior = nomes.setdefault(chave, equipe)
                    if anterior != equipe:
                        raise ValueError('Nome de equipe histórico divergente: {}.'.format(chave))
    return nomes


def _fontes_snapshot(root, snapshot=SNAPSHOT_2026):
    """Lê snapshot somente após revalidar hashes e paginação do coletor."""
    raiz_snapshots = root / 'data/operacao_2026/snapshots'
    indice, _ = fontes.ler_snapshot(raiz_snapshots, snapshot)
    base = raiz_snapshots / snapshot
    indice_path = base / 'indice.json'
    return base, indice_path, [(source, base / source['arquivo']) for source in indice['fontes']]


def _paginas_qualificacao_comprovadas(paginas, evento):
    """Valida e ordena uma Q paginada de um único snapshot/endpoint/evento."""
    por_offset = {}
    for source, path in paginas:
        if source.get('endpoint') != 'classificacao':
            raise ValueError('Fonte declarada não é classificação.')
        offset = int(source['parametros']['offset'])
        if offset in por_offset:
            raise ValueError('Offset duplicado na classificação declarada.')
        por_offset[offset] = (source, path)
    if not por_offset:
        raise ValueError('Fonte de classificação declarada ausente do snapshot da emissão.')
    temporada = evento.get('season', evento.get('temporada'))
    rodada = evento.get('round', evento.get('rodada'))
    circuito = evento.get('Circuit', {}).get('circuitId', evento.get('circuito_id'))
    esperado = {
        'season': str(temporada), 'round': str(rodada),
        'date': evento['data'], 'Circuit': {'circuitId': circuito},
    }
    def buscar(offset):
        source, path = por_offset[offset]
        return dict(source, bytes=path.read_bytes())
    try:
        validadas = fontes.paginas_completas(buscar, 'classificacao', evento['rodada'], esperado)
    except (KeyError, ValueError) as erro:
        raise ValueError('Classificação paginada inválida para o evento declarado.') from erro
    ordenadas = [por_offset[int(item['parametros']['offset'])] for item in validadas]
    resultados = []
    for _, path in ordenadas:
        corrida = _json(path)['MRData']['RaceTable']['Races'][0]
        resultados.extend(corrida.get('QualifyingResults', []))
    return ordenadas, resultados


def _corrida_base(event):
    local = event.get('Circuit', {}).get('Location', {})
    programacao = []
    for campo, nome in (
        ('FirstPractice', 'Treino livre 1'),
        ('SecondPractice', 'Treino livre 2'),
        ('ThirdPractice', 'Treino livre 3'),
        ('SprintQualifying', 'Classificação Sprint'),
        ('Sprint', 'Sprint'),
        ('Qualifying', 'Classificação'),
    ):
        sessao = event.get(campo)
        if isinstance(sessao, dict) and sessao.get('date'):
            programacao.append({
                'sessao': nome,
                'data': sessao['date'],
                'hora': sessao.get('time') or 'Horário indisponível',
            })
    programacao.append({
        'sessao': 'Corrida',
        'data': event['date'],
        'hora': event.get('time') or 'Horário indisponível',
    })
    return {
        'temporada': 2026,
        'rodada': int(event['round']),
        'corrida': event['raceName'],
        'cidade': local.get('locality') or 'Cidade indisponível',
        'pais': local.get('country') or 'País indisponível',
        'data': event['date'],
        'data_corrida': event['date'],
        'circuito_id': event['Circuit']['circuitId'],
        'circuito_nome': event['Circuit'].get('circuitName') or 'Circuito indisponível',
        'programacao': programacao,
        'estado_qualificacao': 'indisponivel',
        'estado_previsao': 'indisponivel',
        'estado_resultado': 'indisponivel',
        'motivo_qualificacao': 'snapshot local de classificação ausente',
        'motivo_previsao': 'não há previsão registrada local válida para este GP',
        'motivo_resultado': MOTIVO_SEM_RESULTADO,
        'resultado_posterior_validado': False,
        'participantes_esperados_previsao': None,
    }


def _estado_operacao(corrida):
    """Estado de apresentação; não altera emissão, fonte ou probabilidades."""
    if corrida['estado_previsao'] == 'ensaio_retrospectivo':
        return 'ensaio_retrospectivo'
    if corrida['estado_previsao'] == 'previsao_registrada':
        return 'previsao_registrada'
    if corrida['estado_resultado'] == 'observado_local':
        return 'resultado_observado'
    if corrida['estado_qualificacao'] == 'local_disponivel':
        return 'classificacao_disponivel'
    return 'aguardando_dados'


def _tempos_formula1dashboard(root, rodada, previsoes_por_piloto):
    """Contexto pós-emissão, somente para apresentação; nunca altera o modelo v1."""
    base = root / 'data' / 'operacao_2026' / 'formula1dashboard' / SNAPSHOT_FORMULA1DASHBOARD_AUSTIN
    dados = formula1dashboard_tempos.carregar(base)
    if dados['evento']['rodada'] != rodada or dados['evento']['circuito_id'] != 'americas':
        raise ValueError('Snapshot Formula1Dashboard associado ao evento incorreto.')
    sessoes = {}
    for chave, sessao in dados['sessoes'].items():
        linhas = []
        menores_q = {
            fase: min((item[fase + '_segundos'] for item in sessao['linhas'] if item[fase + '_segundos'] is not None), default=None)
            for fase in ('q1', 'q2', 'q3')
        }
        for original in sessao['linhas']:
            item = dict(original)
            piloto = previsoes_por_piloto.get(item['piloto_id']) if item['piloto_id'] else None
            item['ranking_modelo'] = piloto.get('ranking_modelo') if piloto else None
            item['probabilidade_modelo'] = piloto.get('probabilidade_modelo') if piloto else None
            item['motivo_exclusao_comparacao'] = (
                'substituto de treino sem identidade canônica na previsão do GP'
                if item['piloto_id'] is None else None
            )
            melhor = sessao['menor_tempo_segundos']
            item['gap_percentual_lider'] = (
                None if item['tempo_segundos'] is None or melhor is None else 100 * (item['tempo_segundos'] / melhor - 1)
            )
            item['gaps_percentuais_fases'] = {
                fase: None if item[fase + '_segundos'] is None or menores_q[fase] is None else
                100 * (item[fase + '_segundos'] / menores_q[fase] - 1)
                for fase in ('q1', 'q2', 'q3')
            }
            linhas.append(item)
        sessoes[chave] = {**sessao, 'linhas': linhas}
    return {
        'disponivel': True, 'origem': dados['origem'], 'normalizacao': dados['normalizacao'],
        'snapshot_id': dados['snapshot_id'], 'evento': dados['evento'], 'sessoes': sessoes,
        'aviso_modelo': ('Tempos obtidos após a emissão prospectiva; são contexto descritivo e não integraram as 15 entradas do modelo v1.'),
    }, dados['arquivos']


def _participante_da_emissao(rodada, piloto_id, identidade, linha, existente=None, prospectivo=False):
    """Combina emissão e classificação sem exigir o resultado do GP-alvo."""
    participante = dict(existente or {
        'temporada': 2026, 'rodada': rodada, 'piloto_id': piloto_id,
        'resultado_observado': None, 'status_resultado': None,
    })
    participante.update({
        **identidade,
        'elegivel_previsao': linha['elegivel_previsao'] == 'True',
        'probabilidade_modelo': float(linha['probabilidade_modelo']) if linha['probabilidade_modelo'] else None,
        'ranking_modelo': int(linha['ranking_modelo']) if linha['ranking_modelo'] else None,
        'ranking_classificacao': int(linha['ranking_classificacao']) if linha['ranking_classificacao'] else None,
    })
    if prospectivo:
        participante.update({'resultado_observado': None, 'status_resultado': None, 'podio': None})
    return participante


def _campeonato_pilotos_2026(root):
    """Lê DriverStandings pós-Austin somente após validar o inventário paginado."""
    inventario_path = root / 'data/operacao_2026/pos_corrida/austin-20261026T111018Z/inventario.json'
    if inventario_path.is_file():
        try:
            inventario = _json(inventario_path)
            identidade = inventario['identidade']
            if (inventario.get('schema') != 'pitwall-pos-corrida-austin-captura-v1'
                    or inventario.get('estado') != 'coleta_concluida'
                    or identidade != {'temporada': 2026, 'rodada': 18, 'circuito_id': 'americas', 'data': '2026-10-25'}):
                raise ValueError('inventário pós-corrida inválido')
            metadados_endpoint = inventario['endpoints']['classificacao_pilotos']
            if metadados_endpoint.get('estado') != 'completo':
                raise ValueError('classificação pós-Austin incompleta no inventário')
            fontes_driver = [item for item in inventario['fontes'] if item.get('endpoint') == 'classificacao_pilotos']
            if not fontes_driver:
                raise ValueError('fonte DriverStandings pós-Austin ausente')
            por_offset, standings, arquivos = {}, [], [inventario_path]
            total_esperado = int(metadados_endpoint['total'])
            limite = None
            for fonte in fontes_driver:
                if (fonte.get('status') != 200 or fonte.get('origem') != 'rede'
                        or not str(fonte.get('url_real', '')).startswith('https://api.jolpi.ca/ergast/f1/2026/18/driverstandings/')
                        or _utc(fonte['obtido_em_utc']) > _utc(inventario['encerrado_em_utc'])):
                    raise ValueError('proveniência DriverStandings pós-Austin inválida')
                offset, limite_pagina = int(fonte['parametros']['offset']), int(fonte['parametros']['limit'])
                if offset in por_offset or limite_pagina <= 0:
                    raise ValueError('offset DriverStandings pós-Austin duplicado ou inválido')
                if limite is None:
                    limite = limite_pagina
                elif limite != limite_pagina:
                    raise ValueError('limite DriverStandings pós-Austin divergente')
                raw = inventario_path.parent / fonte['arquivo']
                if _sha256(raw) != fonte['sha256']:
                    raise ValueError('hash pós-corrida divergente')
                dados = _json(raw)['MRData']
                tabela = dados['StandingsTable']
                if (int(dados['limit']) != limite_pagina or int(dados['offset']) != offset
                        or int(dados['total']) != total_esperado or str(tabela['season']) != '2026'
                        or int(tabela['round']) != 18):
                    raise ValueError('metadados DriverStandings pós-Austin divergentes')
                listas = tabela['StandingsLists']
                if len(listas) != 1 or str(listas[0]['season']) != '2026' or int(listas[0]['round']) != 18:
                    raise ValueError('identidade DriverStandings pós-Austin divergente')
                por_offset[offset] = fonte
                standings.extend(listas[0].get('DriverStandings', []))
                arquivos.append(raw)
            if (limite is None or set(por_offset) != set(range(0, total_esperado, limite))
                    or len(standings) != total_esperado
                    or len({item['Driver']['driverId'] for item in standings}) != total_esperado):
                raise ValueError('classificação pós-Austin incompleta ou duplicada')
            itens = []
            for item in standings:
                piloto, equipes = item['Driver'], item.get('Constructors', [])
                itens.append({
                    'posicao': int(item['position']), 'pontos': float(item['points']),
                    'vitorias': int(item['wins']), 'piloto_id': piloto['driverId'],
                    'piloto': _nome(piloto), 'equipe': ' / '.join(x['name'] for x in equipes) or None,
                })
            return {
                'disponivel': True,
                'snapshot_id': '{}:classificacao_pilotos'.format(inventario['snapshot_canonico']),
                'rodada_referencia': 18, 'obtido_em_utc': max(item['obtido_em_utc'] for item in fontes_driver),
                'paginas_validadas': len(por_offset), 'url_base': por_offset[min(por_offset)]['url_real'],
                'escopo': 'DriverStandings pós-Austin da Jolpica-F1, derivado do inventário paginado separado das probabilidades por GP.',
                'classificacao': sorted(itens, key=lambda x: (x['posicao'], x['piloto_id'])),
            }, arquivos
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as erro:
            return {'disponivel': False, 'motivo': 'Classificação pós-Austin indisponível: {}.'.format(erro), 'classificacao': []}, [inventario_path]
    base = root / 'data' / 'operacao_2026' / 'snapshots' / SNAPSHOT_CLASSIFICACAO_PILOTOS_2026
    indice_path = base / 'indice.json'
    try:
        indice = _json(indice_path)
        paginacao = indice['paginacao']
        fontes_classificacao = indice['fontes']
        if (
            indice.get('schema') != 'pitwall-driverstandings-snapshot-v1'
            or indice.get('endpoint') != 'driverstandings'
            or indice.get('temporada') != 2026
            or not paginacao.get('completa')
            or paginacao.get('paginas_coletadas') != paginacao.get('paginas_esperadas')
            or len(fontes_classificacao) != paginacao.get('paginas_esperadas')
        ):
            raise ValueError('metadados de paginação incompletos')
        standings, offsets, arquivos = [], set(), [indice_path]
        for fonte in sorted(fontes_classificacao, key=lambda item: item['offset']):
            if fonte.get('endpoint') != 'driverstandings' or not str(fonte.get('url', '')).startswith(indice['url_base']):
                raise ValueError('fonte DriverStandings inválida')
            arquivo = base / fonte['arquivo']
            if _sha256(arquivo) != fonte['sha256']:
                raise ValueError('hash divergente em DriverStandings')
            dados = _json(arquivo)
            metadados = dados['MRData']
            if int(metadados['offset']) != int(fonte['offset']) or int(metadados['limit']) != int(fonte['limit']) or int(metadados['total']) != int(fonte['total']):
                raise ValueError('metadados da página DriverStandings divergentes')
            lista = metadados['StandingsTable']['StandingsLists']
            if len(lista) != 1 or int(metadados['StandingsTable']['round']) != int(indice['rodada_referencia']):
                raise ValueError('rodada de referência DriverStandings divergente')
            offsets.add(int(fonte['offset']))
            standings.extend(lista[0].get('DriverStandings', []))
            arquivos.append(arquivo)
        total = int(paginacao['total'])
        limite = int(paginacao['limit'])
        esperado = set(range(0, total, limite))
        if offsets != esperado or len(standings) != total or len({item['Driver']['driverId'] for item in standings}) != total:
            raise ValueError('paginação DriverStandings incompleta ou duplicada')
        classificacao = []
        for item in standings:
            piloto = item['Driver']
            equipes = item.get('Constructors', [])
            classificacao.append({
                'posicao': int(item['position']),
                'pontos': float(item['points']),
                'vitorias': int(item['wins']),
                'piloto_id': piloto['driverId'],
                'piloto': _nome(piloto),
                'equipe': ' / '.join(equipe['name'] for equipe in equipes) or None,
            })
        classificacao.sort(key=lambda item: (item['posicao'], item['piloto_id']))
        return {
            'disponivel': True,
            'snapshot_id': indice['snapshot_id'],
            'rodada_referencia': int(indice['rodada_referencia']),
            'obtido_em_utc': indice['obtido_em_utc'],
            'paginas_validadas': len(fontes_classificacao),
            'url_base': indice['url_base'],
            'escopo': 'DriverStandings da Jolpica-F1, preservado em snapshot local paginado.',
            'classificacao': classificacao,
        }, arquivos
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as erro:
        return {
            'disponivel': False,
            'motivo': 'Classificação de pilotos Jolpica indisponível: {}. Probabilidades por GP permanecem separadas.'.format(erro),
            'classificacao': [],
        }, [indice_path]


def _dados_2026(root, snapshot=None):
    _, indice_path, fontes = _fontes_snapshot(root) if snapshot is None else _fontes_snapshot(root,snapshot)
    by_key = {}
    for source, path in fontes:
        by_key.setdefault((source['endpoint'], source.get('rodada')), []).append((source, path))
    calendar_pages = by_key.get(('calendario', None), [])
    if len(calendar_pages) != 1:
        raise ValueError('Snapshot 2026 deve conter uma página válida de calendário.')
    _, calendar_path = calendar_pages[0]
    calendar = _json(calendar_path)['MRData']['RaceTable']['Races']
    corridas = [_corrida_base(event) for event in calendar]
    por_rodada = {item['rodada']: item for item in corridas}
    if len(por_rodada) != len(corridas):
        raise ValueError('Calendário 2026 contém rodada duplicada.')
    identidades = {}
    previsoes_por_chave = {}

    # As fontes e as páginas válidas do índice, e não um intervalo fixo de rodadas,
    # determinam a cobertura local de resultados.
    for (endpoint, rodada_fonte), paginas in by_key.items():
        if endpoint != 'resultados':
            continue
        for source, path in paginas:
            races = _json(path)['MRData']['RaceTable'].get('Races', [])
            for result in races:
                rodada = int(result['round'])
                if rodada_fonte is not None and rodada != int(rodada_fonte):
                    raise ValueError('Índice de resultados divergente da rodada no conteúdo.')
                corrida = por_rodada.get(rodada)
                if corrida is None:
                    raise ValueError('Resultado local para rodada ausente do calendário: {}'.format(rodada))
                if not result.get('Results'):
                    continue
                corrida.update({
                    'estado_resultado': 'observado_local',
                    'motivo_resultado': None,
                    'fonte_resultado_sha256': source['sha256'],
                    'resultado_obtido_em_utc': source.get('obtido_em_utc'),
                    'resultado_data_fonte': result.get('date'),
                    'resultado_circuito_id': result.get('Circuit', {}).get('circuitId'),
                })
                for entry in result['Results']:
                    driver = entry['Driver']
                    team = entry['Constructor']
                    piloto_id = driver['driverId']
                    chave = (rodada, piloto_id)
                    if chave in previsoes_por_chave:
                        raise ValueError('Resultado 2026 duplicado: {}.'.format(chave))
                    identidade = {
                        'piloto': _nome(driver),
                        'equipe_id': team['constructorId'],
                        'equipe': team.get('name') or None,
                    }
                    identidades['2026:{}:{}'.format(rodada, piloto_id)] = identidade
                    previsoes_por_chave[chave] = {
                        'temporada': 2026, 'rodada': rodada, 'piloto_id': piloto_id,
                        **identidade, 'elegivel_previsao': False, 'probabilidade_modelo': None,
                        'ranking_modelo': None, 'ranking_classificacao': None,
                        'resultado_observado': int(entry['position']),
                        'status_resultado': entry.get('status') or None,
                        'modo_previsao': None,
                    }

    registros = carregar_registro_emissoes(root)
    eventos_com_emissao = {(rodada, circuito_id) for (temporada, rodada, circuito_id) in registros if temporada == 2026}
    qualificacoes = {}
    fontes_qualificacao_por_rodada = {}
    for (endpoint, rodada_fonte), paginas in by_key.items():
        if endpoint != 'classificacao':
            continue
        por_evento = {}
        for source, path in paginas:
            races = _json(path)['MRData']['RaceTable'].get('Races', [])
            if not races:
                continue
            for classificacao in races:
                rodada = int(classificacao['round'])
                if rodada_fonte is not None and rodada != int(rodada_fonte):
                    raise ValueError('Índice de classificação divergente da rodada no conteúdo.')
                chave_evento = (rodada, classificacao['Circuit']['circuitId'])
                por_evento.setdefault(chave_evento, []).append((source, path, classificacao))
        for (rodada, circuito_id), paginas_evento in por_evento.items():
            # Uma emissão declara sua própria Q: a Q-base não participa nem da identidade
            # nem da proveniência desse evento, mesmo quando possui os mesmos bytes.
            if (rodada, circuito_id) in eventos_com_emissao:
                continue
            corrida = por_rodada.get(rodada)
            if corrida is None or corrida['circuito_id'] != circuito_id:
                raise ValueError('Classificação local para evento ausente ou divergente do calendário.')
            if len(paginas_evento) == 1 and len(_json(paginas_evento[0][1])['MRData']['RaceTable'].get('Races', [])) > 1:
                source, path, classificacao = paginas_evento[0]
                ordenadas, resultados = [(source, path)], classificacao.get('QualifyingResults', [])
            else:
                ordenadas, resultados = _paginas_qualificacao_comprovadas(
                    [(source, path) for source, path, _ in paginas_evento], corrida)
            if resultados:
                qualificacoes[rodada] = (ordenadas[0][0], resultados)
                fontes_qualificacao_por_rodada[rodada] = [source['sha256'] for source, _ in ordenadas]
                corrida.update({
                    'estado_qualificacao': 'local_disponivel',
                    'motivo_qualificacao': None,
                    'fonte_qualificacao_sha256': ordenadas[0][0]['sha256'],
                    'fontes_qualificacao_sha256': [source['sha256'] for source, _ in ordenadas],
                })

    fontes_emissoes = []
    snapshots_emissoes = {}
    for (temporada, rodada, _), registro in sorted(registros.items()):
        if temporada != 2026:
            continue
        snapshot = registro['snapshot']
        if registro.get('origem_qualificacao') == 'openf1':
            resultados_qualificacao = list(registro.get('registros_qualificacao') or [])
            fontes_q = list(registro.get('fontes_qualificacao') or [])
            arquivos_q = list(registro.get('arquivos_qualificacao') or [])
            if not resultados_qualificacao or not fontes_q or not arquivos_q:
                raise ValueError('Emissão OpenF1 sem classificação comprovada.')
            qualificacoes[rodada] = (fontes_q[0], resultados_qualificacao)
            fontes_qualificacao_por_rodada[rodada] = [source['sha256'] for source in fontes_q]
            fontes_emissoes.extend(arquivos_q)
            por_rodada[rodada].update({
                'estado_qualificacao': 'local_disponivel', 'motivo_qualificacao': None,
                'fonte_qualificacao_sha256': fontes_q[0]['sha256'],
                'fontes_qualificacao_sha256': [source['sha256'] for source in fontes_q],
            })
            continue
        if snapshot not in snapshots_emissoes:
            _, indice_emissao, fontes_emissao = _fontes_snapshot(root, snapshot)
            snapshots_emissoes[snapshot] = fontes_emissao
            fontes_emissoes.append(indice_emissao)
        declaradas = {(fonte['arquivo'], fonte['sha256']) for fonte in registro['fontes_qualificacao']}
        selecionadas = [(source, path) for source, path in snapshots_emissoes[snapshot]
                       if (source.get('arquivo'), source.get('sha256')) in declaradas]
        if len(selecionadas) != len(declaradas):
            raise ValueError('Fonte de classificação declarada ausente do snapshot da emissão.')
        corrida_declarada = por_rodada.get(rodada)
        if corrida_declarada is None:
            raise ValueError('Emissão para rodada ausente do calendário.')
        ordenadas, resultados_qualificacao = _paginas_qualificacao_comprovadas(selecionadas, corrida_declarada)
        fontes_emissoes.extend(path for _, path in ordenadas)
        qualificacoes[rodada] = (ordenadas[0][0], resultados_qualificacao)
        fontes_qualificacao_por_rodada[rodada] = [source['sha256'] for source, _ in ordenadas]
        por_rodada[rodada].update({
            'estado_qualificacao': 'local_disponivel',
            'motivo_qualificacao': None,
            'fonte_qualificacao_sha256': ordenadas[0][0]['sha256'],
            'fontes_qualificacao_sha256': [source['sha256'] for source, _ in ordenadas],
        })
    emissoes_proveniencia = {}
    emissao_legada = None
    for (temporada, rodada, circuito_id), registro in sorted(registros.items()):
        if temporada != 2026:
            continue
        if rodada not in por_rodada or rodada not in qualificacoes:
            raise ValueError('Emissão sem classificação local válida para a rodada {}.'.format(rodada))
        emissao = root / registro['diretorio']
        manifesto_path = emissao / 'manifesto.json'
        qual_source, qualificacao = qualificacoes[rodada]
        pilotos_qualificacao = {item['Driver']['driverId']: item for item in qualificacao}
        corrida = por_rodada[rodada]
        corrida['participantes_esperados_previsao'] = sorted(pilotos_qualificacao)

        if corrida['estado_resultado'] == 'observado_local':
            try:
                identidade_resultado_valida = (
                    corrida.get('resultado_circuito_id') == circuito_id
                    and corrida.get('resultado_data_fonte') == corrida['data']
                    and isinstance(corrida.get('fonte_resultado_sha256'), str)
                    and corrida['fonte_resultado_sha256']
                )
                obtido_resultado = _utc(corrida['resultado_obtido_em_utc'])
                if not identidade_resultado_valida:
                    raise ValueError('identidade/proveniência do resultado inválida')
                if registro['modo'] == 'PROSPECTIVO' and (
                    obtido_resultado <= _utc(registro['emitido_em_utc'])
                    or obtido_resultado <= datetime.combine(
                        datetime.fromisoformat(corrida['data']).date(), datetime.min.time(), timezone.utc,
                    )
                ):
                    raise ValueError('proveniência temporal do resultado posterior inválida')
            except (KeyError, TypeError, ValueError) as erro:
                corrida.update({
                    'estado_resultado': 'indisponivel',
                    'motivo_resultado': 'resultado rejeitado: {}'.format(erro),
                    'fonte_resultado_sha256': None,
                    'resultado_posterior_validado': False,
                })
                for (rodada_item, _), participante in previsoes_por_chave.items():
                    if rodada_item == rodada:
                        participante.update({'resultado_observado': None, 'status_resultado': None, 'podio': None})
            else:
                # O selo só serve à auditoria posterior de uma emissão prospectiva.
                corrida['resultado_posterior_validado'] = registro['modo'] == 'PROSPECTIVO'

        if corrida['circuito_id'] != circuito_id:
            raise ValueError('Emissão associada ao circuito incorreto para a rodada {}.'.format(rodada))
        estado = 'previsao_registrada' if registro['modo'] == 'PROSPECTIVO' else 'ensaio_retrospectivo'
        motivo = ('previsão registrada antes da corrida' if estado == 'previsao_registrada'
                  else 'ensaio retrospectivo; não é previsão registrada antes da corrida')
        corrida.update({
            'estado_previsao': estado,
            'motivo_previsao': motivo,
            'emissao_sha256': _sha256(manifesto_path),
        })
        with (emissao / 'probabilidades.csv').open(encoding='utf-8', newline='') as arquivo:
            for row in csv.DictReader(arquivo):
                piloto_id = row['piloto_id']
                encontrado = pilotos_qualificacao.get(piloto_id)
                if encontrado is None:
                    raise ValueError('Piloto da emissão sem classificação local: {}'.format(piloto_id))
                identidade = {
                    'piloto': _nome(encontrado['Driver']),
                    'equipe_id': encontrado['Constructor']['constructorId'],
                    'equipe': encontrado['Constructor'].get('name') or None,
                }
                identidades['2026:{}:{}'.format(rodada, piloto_id)] = identidade
                chave = (rodada, piloto_id)
                participante = _participante_da_emissao(
                    rodada, piloto_id, identidade, row, previsoes_por_chave.get(chave),
                    prospectivo=False,
                )
                participante['modo_previsao'] = estado
                previsoes_por_chave[chave] = participante
        for (rodada_item, piloto_id), participante in previsoes_por_chave.items():
            if rodada_item == rodada and piloto_id not in pilotos_qualificacao:
                participante['motivos_inelegibilidade'] = (
                    'ausente da classificação capturada; probabilidade não calculada'
                )
        chave_evento = '{}:{}:{}'.format(temporada, rodada, circuito_id)
        proveniencia = {
            'evento': registro['evento'], 'modo': registro['modo'],
            'emitido_em_utc': registro['emitido_em_utc'],
            'hashes_saidas': {'probabilidades.csv': registro['hash_probabilidades']},
            'fonte_qualificacao_sha256': qual_source['sha256'],
            'fontes_qualificacao_sha256': fontes_qualificacao_por_rodada[rodada],
        }
        emissoes_proveniencia[chave_evento] = proveniencia
        if rodada == 17 or emissao_legada is None:
            emissao_legada = proveniencia
    if emissao_legada is None:
        emissao_legada = {}
    for corrida in corridas:
        corrida['estado_operacao'] = _estado_operacao(corrida)
    campeonato, fontes_campeonato = _campeonato_pilotos_2026(root)
    previsoes_austin = {
        piloto_id: participante for (rodada, piloto_id), participante in previsoes_por_chave.items()
        if rodada == 18
    }
    try:
        tempos_austin, fontes_tempos = _tempos_formula1dashboard(root, 18, previsoes_austin)
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        tempos_austin, fontes_tempos = {
            'disponivel': False,
            'motivo': 'Tempos Formula1Dashboard indisponíveis: {}.'.format(erro),
            'sessoes': {},
        }, []
    return {
        'corridas': corridas,
        'previsoes': list(previsoes_por_chave.values()),
        'campeonato_pilotos': campeonato,
        'tempos_sessoes': {'18': tempos_austin},
    }, identidades, [indice_path, *fontes_emissoes, *fontes_campeonato, *fontes_tempos], {
        **emissao_legada, 'emissoes': emissoes_proveniencia,
    }


def gerar(root, destino, snapshot=None):
    root, destino = Path(root).resolve(), Path(destino)
    identidades, identificacao_path = _identidades_historicas(root)
    nomes_equipes = _nomes_equipes_historicas(root)
    for chave, identidade in identidades.items():
        identidade['equipe'] = nomes_equipes.get(chave)
    dados_2026, identidades_2026, fontes_2026, emissao = _dados_2026(root) if snapshot is None else _dados_2026(root,snapshot)
    identidades.update(identidades_2026)
    fontes = [identificacao_path, *fontes_2026]
    for temporada in (2024, 2025):
        pacote = carregar_temporada(root, temporada)
        for item in pacote['previsoes']:
            identidade = identidades.get('{}:{}:{}'.format(temporada, item['rodada'], item['piloto_id']))
            if identidade is None:
                identidades['{}:{}:{}'.format(temporada, item['rodada'], item['piloto_id'])] = {
                    'piloto': None, 'equipe_id': None, 'equipe': None,
                }
    asset = {
        'versao': 2,
        'temporadas': [2024, 2025, 2026],
        'identidades': identidades,
        'dados_2026': dados_2026,
        'proveniencia': {
            'gerador': 'preparar_dashboard_race_weekend.py',
            'snapshot_2026': snapshot or SNAPSHOT_2026,
            'emissao_2026': '2026:17:marina_bay',
            'emissao': emissao,
            'emissoes': emissao['emissoes'],
            'fontes_sha256': {str(path.relative_to(root)): _sha256(path) for path in fontes},
            'sem_recalculo': True,
        },
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(asset, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return asset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--snapshot', default=None, help='Snapshot 2026 validado; padrão histórico preservado.')
    parser.add_argument('--saida', type=Path, default=Path('frontend_assets/race_weekend.json'))
    args = parser.parse_args()
    destino = args.saida if args.saida.is_absolute() else args.root / args.saida
    gerar(args.root, destino, args.snapshot)


if __name__ == '__main__':
    main()
