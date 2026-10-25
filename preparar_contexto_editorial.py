"""Gera o contrato editorial comum a partir dos calendários já versionados.

Este módulo não consulta rede, não modifica artefatos científicos e não cria
inferências. Ele consolida somente o contexto factual de apresentação do GP.
"""
import argparse
import json
from pathlib import Path


TEMPORADAS = (2024, 2025, 2026)


def _ler_json(caminho):
    try:
        return json.loads(caminho.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('Não foi possível ler {}.'.format(caminho)) from erro


def _evento_calendario(evento, temporada):
    try:
        rodada = int(evento['round'])
        circuito = evento['Circuit']
        local = circuito['Location']
        saida = {
            'temporada': temporada,
            'rodada': rodada,
            'corrida': str(evento['raceName']),
            'data': str(evento['date']),
            'circuito_id': str(circuito['circuitId']),
            'circuito_nome': str(circuito['circuitName']),
            'cidade': str(local['locality']),
            'pais': str(local['country']),
        }
    except (KeyError, TypeError, ValueError) as erro:
        raise ValueError('Calendário {} contém evento inválido.'.format(temporada)) from erro
    if rodada < 1 or any(not valor for valor in saida.values()):
        raise ValueError('Calendário {} contém contexto obrigatório vazio.'.format(temporada))
    return saida


def _historico(raiz, temporada):
    caminho = raiz / 'data' / 'historico' / str(temporada) / 'raw' / 'calendario_offset_0000.json'
    dados = _ler_json(caminho)
    try:
        eventos = dados['MRData']['RaceTable']['Races']
    except (KeyError, TypeError) as erro:
        raise ValueError('Calendário {} não contém corridas.'.format(temporada)) from erro
    if not isinstance(eventos, list) or not eventos:
        raise ValueError('Calendário {} está vazio.'.format(temporada))
    return [_evento_calendario(evento, temporada) for evento in eventos]


def _atual(raiz):
    dados = _ler_json(raiz / 'frontend_assets' / 'race_weekend.json')
    try:
        eventos = dados['dados_2026']['corridas']
    except (KeyError, TypeError) as erro:
        raise ValueError('Asset Race Weekend sem corridas 2026 válidas.') from erro
    if not isinstance(eventos, list) or not eventos:
        raise ValueError('Calendário 2026 está vazio.')
    saida = []
    for evento in eventos:
        try:
            item = {
                'temporada': 2026,
                'rodada': int(evento['rodada']),
                'corrida': str(evento['corrida']),
                'data': str(evento['data']),
                'circuito_id': str(evento['circuito_id']),
                'circuito_nome': str(evento['circuito_nome']),
                'cidade': str(evento['cidade']),
                'pais': str(evento['pais']),
            }
        except (KeyError, TypeError, ValueError) as erro:
            raise ValueError('Calendário 2026 contém evento inválido.') from erro
        if item['rodada'] < 1 or any(not valor for valor in item.values()):
            raise ValueError('Calendário 2026 contém contexto obrigatório vazio.')
        saida.append(item)
    return saida


def gerar(raiz, destino):
    raiz, destino = Path(raiz), Path(destino)
    eventos = _historico(raiz, 2024) + _historico(raiz, 2025) + _atual(raiz)
    chaves = [(item['temporada'], item['rodada']) for item in eventos]
    if len(chaves) != len(set(chaves)):
        raise ValueError('Calendários contêm temporada/rodada duplicada.')
    eventos.sort(key=lambda item: (item['temporada'], item['rodada']))
    ativo = {'versao': 1, 'temporadas': list(TEMPORADAS), 'eventos': eventos}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ativo, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return ativo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--saida', type=Path, default=Path('frontend_assets/contexto_editorial.json'))
    args = parser.parse_args()
    destino = args.saida if args.saida.is_absolute() else args.root / args.saida
    gerar(args.root, destino)


if __name__ == '__main__':
    main()
