"""Admissão explícita de classificação OpenF1 já preservada, sem simular Jolpica."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VERSAO_NORMALIZACAO = 'openf1-qualificacao-v1'
ORIGEM = 'openf1'
SESSAO_ESPERADA = {'session_key': 11392, 'meeting_key': 1297, 'year': 2026,
                   'session_name': 'Qualifying', 'session_type': 'Qualifying',
                   'location': 'Austin', 'circuit_short_name': 'Austin'}
# Mapa literal específico da temporada 2026 e da sessão Austin Q; não deriva IDs por nomes.
MAPEAMENTO_2026 = {
    12: ('antonelli', 'mercedes', 'Kimi', 'Antonelli', 'Mercedes'),
    3: ('max_verstappen', 'red_bull', 'Max', 'Verstappen', 'Red Bull Racing'),
    6: ('hadjar', 'red_bull', 'Isack', 'Hadjar', 'Red Bull Racing'),
    16: ('leclerc', 'ferrari', 'Charles', 'Leclerc', 'Ferrari'),
    44: ('hamilton', 'ferrari', 'Lewis', 'Hamilton', 'Ferrari'),
    63: ('russell', 'mercedes', 'George', 'Russell', 'Mercedes'),
    81: ('piastri', 'mclaren', 'Oscar', 'Piastri', 'McLaren'),
    1: ('norris', 'mclaren', 'Lando', 'Norris', 'McLaren'),
    41: ('arvid_lindblad', 'rb', 'Arvid', 'Lindblad', 'Racing Bulls'),
    30: ('lawson', 'rb', 'Liam', 'Lawson', 'Racing Bulls'),
    10: ('gasly', 'alpine', 'Pierre', 'Gasly', 'Alpine'),
    27: ('hulkenberg', 'audi', 'Nico', 'Hulkenberg', 'Audi'),
    5: ('bortoleto', 'audi', 'Gabriel', 'Bortoleto', 'Audi'),
    43: ('colapinto', 'alpine', 'Franco', 'Colapinto', 'Alpine'),
    14: ('alonso', 'aston_martin', 'Fernando', 'Alonso', 'Aston Martin'),
    87: ('bearman', 'haas', 'Oliver', 'Bearman', 'Haas F1 Team'),
    31: ('ocon', 'haas', 'Esteban', 'Ocon', 'Haas F1 Team'),
    18: ('stroll', 'aston_martin', 'Lance', 'Stroll', 'Aston Martin'),
    55: ('sainz', 'williams', 'Carlos', 'Sainz', 'Williams'),
    23: ('albon', 'williams', 'Alexander', 'Albon', 'Williams'),
    11: ('perez', 'cadillac', 'Sergio', 'Perez', 'Cadillac'),
    77: ('bottas', 'cadillac', 'Valtteri', 'Bottas', 'Cadillac'),
}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value):
    if not isinstance(value, str):
        raise ValueError('UTC OpenF1 ausente.')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('UTC OpenF1 inválido.')
    return parsed.astimezone(timezone.utc)


def _z(value):
    return _utc(value).isoformat().replace('+00:00', 'Z')


def _carregar_json(base, inventario, nome):
    esperado = inventario.get('sha256_arquivos', {}).get(nome)
    path = base / nome
    if not isinstance(esperado, str) or not path.is_file() or _sha(path) != esperado:
        raise ValueError('Hash OpenF1 divergente: {}.'.format(nome))
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('JSON OpenF1 inválido: {}.'.format(nome)) from error


def _fonte(inventario, nome):
    for item in inventario.get('fontes', []):
        if item.get('arquivo') == nome:
            return dict(item)
    raise ValueError('Recibo OpenF1 ausente: {}.'.format(nome))


def carregar(base, *, sessao_esperada=None, prefixo="openf1-austin-q", mapeamento=None):
    esperado_sessao = SESSAO_ESPERADA if sessao_esperada is None else sessao_esperada
    mapping = MAPEAMENTO_2026 if mapeamento is None else mapeamento
    if esperado_sessao.get("session_name") != "Qualifying" or esperado_sessao.get("session_type") != "Qualifying":
        raise ValueError("A sessão precisa ser Qualifying principal.")
    if not prefixo.replace("-", "").isalnum():
        raise ValueError("Prefixo inválido.")
    base = Path(base)
    inventario = _carregar_json(base, {'sha256_arquivos': {'inventario.json': _sha(base / 'inventario.json')}}, 'inventario.json')
    if inventario.get('schema') != 'pitwall-source-availability-evidence-v1':
        raise ValueError('Inventário OpenF1 com schema inválido.')
    nomes = tuple(prefixo + '-' + endpoint + '.json' for endpoint in ('sessions','session_result','drivers','race_control'))
    dados = {nome: _carregar_json(base, inventario, nome) for nome in nomes}
    sessoes = [item for item in dados[nomes[0]] if all(item.get(k) == v for k, v in esperado_sessao.items())]
    if len(sessoes) != 1:
        raise ValueError('Sessão OpenF1 Q ausente ou ambígua.')
    sessao = sessoes[0]
    chave = (sessao['session_key'], sessao['meeting_key'])
    resultados, pilotos = dados[nomes[1]], dados[nomes[2]]
    if len(resultados) != 22 or len(pilotos) != 22:
        raise ValueError('Cobertura OpenF1 incompleta.')
    por_numero = {}
    for piloto in pilotos:
        if (piloto.get('session_key'), piloto.get('meeting_key')) != chave:
            raise ValueError('Piloto OpenF1 de outra sessão/evento.')
        numero = piloto.get('driver_number')
        if numero in por_numero:
            raise ValueError('Piloto OpenF1 duplicado.')
        por_numero[numero] = piloto
    registros, posicoes, numeros = [], set(), set()
    for resultado in sorted(resultados, key=lambda item: item.get('position') if type(item.get('position')) is int else 999):
        if (resultado.get('session_key'), resultado.get('meeting_key')) != chave:
            raise ValueError('Resultado OpenF1 de outra sessão/evento.')
        numero, posicao = resultado.get('driver_number'), resultado.get('position')
        if numero in numeros or numero not in por_numero:
            raise ValueError('Piloto OpenF1 duplicado ou ausente.')
        if type(posicao) is not int or posicao <= 0 or posicao in posicoes:
            raise ValueError('Posição OpenF1 inválida ou duplicada.')
        if numero not in mapping:
            raise ValueError('Mapeamento literal OpenF1 ausente: {}.'.format(numero))
        piloto = por_numero[numero]
        driver_id, constructor_id, first, last, equipe = mapping[numero]
        if (piloto.get('first_name'), piloto.get('last_name'), piloto.get('team_name')) != (first, last, equipe):
            raise ValueError('Identidade OpenF1 diverge do mapeamento literal: {}.'.format(numero))
        numeros.add(numero); posicoes.add(posicao)
        registros.append({'position': str(posicao),
                          'Driver': {'driverId': driver_id, 'givenName': first, 'familyName': last},
                          'Constructor': {'constructorId': constructor_id, 'name': equipe},
                          'openf1_driver_number': numero})
    if set(mapping) != numeros or posicoes != set(range(1, 23)):
        raise ValueError('Cobertura OpenF1 incompleta.')
    fechamento = [item for item in dados[nomes[3]]
                  if (item.get('session_key'), item.get('meeting_key')) == chave
                  and item.get('message') == 'SESSION FINISHED' and item.get('qualifying_phase') == 3]
    if len(fechamento) != 1:
        raise ValueError('Encerramento OpenF1 de Q3 ausente ou ambíguo.')
    encerramento = _z(fechamento[0].get('date'))
    fontes = []
    for nome in nomes:
        fonte = _fonte(inventario, nome)
        if fonte.get('status') != 200 or fonte.get('sha256') != inventario['sha256_arquivos'][nome]:
            raise ValueError('Recibo OpenF1 diverge do raw.')
        fontes.append({'origem': ORIGEM, 'normalizacao': VERSAO_NORMALIZACAO,
                       'arquivo': nome, 'sha256': fonte['sha256'], 'url_solicitada': fonte['url_solicitada'],
                       'url_real': fonte['url_real'], 'status': fonte['status'], 'obtido_em_utc': _z(fonte['obtido_em_utc']),
                       'session_key': sessao['session_key'], 'meeting_key': sessao['meeting_key'],
                       'endpoint': nome.replace(prefixo + '-', '').replace('.json', '')})
    return {'origem': ORIGEM, 'normalizacao': VERSAO_NORMALIZACAO, 'sessao': sessao,
            'encerramento_utc': encerramento, 'registros': registros, 'fontes': fontes,
            'diretorio': str(base), 'arquivos': [base / nome for nome in nomes]}
