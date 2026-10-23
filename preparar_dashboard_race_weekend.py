"""Gera o asset de apresentação Race Weekend a partir de fontes locais imutáveis."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from dashboard_dados import carregar_temporada
from operacao2026 import fontes


SNAPSHOT_2026 = 'coleta-20261020T020130Z'
SNAPSHOT_CLASSIFICACAO_PILOTOS_2026 = 'classificacao-pilotos-20261023T143930Z'
EMISSAO_SINGAPURA = 'ensaio-commit-9e65ad25b125e78b671a763a43934385c1264363'
MOTIVO_SEM_RESULTADO = (
    'snapshot local de resultados ausente; o calendário não prova que a corrida não foi concluída'
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


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


def _fontes_snapshot(root):
    base = root / 'data/operacao_2026/snapshots' / SNAPSHOT_2026
    indice_path = base / 'indice.json'
    indice = _json(indice_path)
    fontes = []
    for source in indice['fontes']:
        path = base / source['arquivo']
        digest = _sha256(path)
        if digest != source['sha256']:
            raise ValueError('Hash divergente no snapshot: {}'.format(source['arquivo']))
        fontes.append((source, path))
    return base, indice_path, fontes


def _corrida_base(event):
    return {
        'temporada': 2026,
        'rodada': int(event['round']),
        'corrida': event['raceName'],
        'data_corrida': event['date'],
        'circuito_id': event['Circuit']['circuitId'],
        'estado_qualificacao': 'indisponivel',
        'estado_previsao': 'indisponivel',
        'estado_resultado': 'indisponivel',
        'motivo_qualificacao': 'snapshot local de classificação ausente',
        'motivo_previsao': 'não há previsão registrada local válida para este GP',
        'motivo_resultado': MOTIVO_SEM_RESULTADO,
    }


def _campeonato_pilotos_2026(root):
    """Lê exclusivamente o snapshot paginado de DriverStandings da Jolpica."""
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


def _dados_2026(root):
    _, indice_path, fontes = _fontes_snapshot(root)
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
                        'resultado_observado': int(entry['position']), 'modo_previsao': None,
                    }

    emissao = root / 'reports/operacao_2026/emissoes' / EMISSAO_SINGAPURA
    manifesto_path = emissao / 'manifesto.json'
    manifesto = _json(manifesto_path)
    hash_probabilidades = _sha256(emissao / 'probabilidades.csv')
    if (
        manifesto.get('evento', {}).get('rodada') != '17'
        or manifesto.get('modo') != 'ENSAIO_RETROSPECTIVO'
        or manifesto.get('hashes_saidas', {}).get('probabilidades.csv') != hash_probabilidades
    ):
        raise ValueError('Emissão de Singapura sem modo explícito ou hash de probabilidades confirmado.')

    qualificacoes = {}
    for (endpoint, rodada_fonte), paginas in by_key.items():
        if endpoint != 'classificacao':
            continue
        for source, path in paginas:
            for classificacao in _json(path)['MRData']['RaceTable'].get('Races', []):
                rodada = int(classificacao['round'])
                if rodada_fonte is not None and rodada != int(rodada_fonte):
                    raise ValueError('Índice de classificação divergente da rodada no conteúdo.')
                resultados = classificacao.get('QualifyingResults', [])
                if resultados:
                    if rodada in qualificacoes:
                        raise ValueError('Classificação 2026 duplicada: {}.'.format(rodada))
                    qualificacoes[rodada] = (source, resultados)
                    por_rodada[rodada].update({
                        'estado_qualificacao': 'local_disponivel',
                        'motivo_qualificacao': None,
                        'fonte_qualificacao_sha256': source['sha256'],
                    })

    if 17 not in qualificacoes:
        raise ValueError('Classificação local válida de Singapura ausente.')
    qual_source, qualificacao = qualificacoes[17]
    pilotos_qualificacao = {item['Driver']['driverId']: item for item in qualificacao}
    corrida = por_rodada[17]
    corrida.update({
        'estado_previsao': 'ensaio_retrospectivo',
        'motivo_previsao': 'ensaio retrospectivo; não é previsão registrada antes da corrida',
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
            identidades['2026:17:{}'.format(piloto_id)] = identidade
            chave = (17, piloto_id)
            if chave not in previsoes_por_chave:
                raise ValueError('Previsão retrospectiva sem resultado local correspondente: {}'.format(piloto_id))
            previsoes_por_chave[chave].update({
                **identidade, 'elegivel_previsao': row['elegivel_previsao'] == 'True',
                'probabilidade_modelo': float(row['probabilidade_modelo']) if row['probabilidade_modelo'] else None,
                'ranking_modelo': int(row['ranking_modelo']) if row['ranking_modelo'] else None,
                'ranking_classificacao': int(row['ranking_classificacao']) if row['ranking_classificacao'] else None,
                'modo_previsao': 'ensaio_retrospectivo',
            })
    campeonato, fontes_campeonato = _campeonato_pilotos_2026(root)
    return {
        'corridas': corridas,
        'previsoes': list(previsoes_por_chave.values()),
        'campeonato_pilotos': campeonato,
    }, identidades, [indice_path, manifesto_path, *fontes_campeonato], {
        'modo': manifesto['modo'], 'emitido_em_utc': manifesto.get('emitido_em_utc'),
        'hashes_saidas': {'probabilidades.csv': hash_probabilidades},
        'fonte_qualificacao_sha256': qual_source['sha256'],
    }


def gerar(root, destino):
    root, destino = Path(root), Path(destino)
    identidades, identificacao_path = _identidades_historicas(root)
    nomes_equipes = _nomes_equipes_historicas(root)
    for chave, identidade in identidades.items():
        identidade['equipe'] = nomes_equipes.get(chave)
    dados_2026, identidades_2026, fontes_2026, emissao = _dados_2026(root)
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
            'snapshot_2026': SNAPSHOT_2026,
            'emissao_2026': EMISSAO_SINGAPURA,
            'emissao': emissao,
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
    parser.add_argument('--saida', type=Path, default=Path('frontend_assets/race_weekend.json'))
    args = parser.parse_args()
    destino = args.saida if args.saida.is_absolute() else args.root / args.saida
    gerar(args.root, destino)


if __name__ == '__main__':
    main()
