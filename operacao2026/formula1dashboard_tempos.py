"""Leitura offline e normalização explícita de sessões Formula1Dashboard."""
import hashlib
import json
from pathlib import Path

from operacao2026.openf1_qualificacao import MAPEAMENTO_2026


ORIGEM = 'formula1dashboard'
VERSAO_NORMALIZACAO = 'formula1dashboard-tempos-v1'
SESSOES = {
    'Practice 1': ('TL1', 11389),
    'Practice 2': ('TL2', 11390),
    'Practice 3': ('TL3', 11391),
    'Qualifying': ('Q', 11392),
}
CONSTRUTORES_EXTERNOS_2026 = {
    1: 'mclaren', 2: 'ferrari', 3: 'red_bull', 4: 'mercedes', 5: 'aston_martin',
    6: 'haas', 7: 'alpine', 8: 'rb', 9: 'williams', 42: 'audi', 43: 'cadillac',
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(base, fonte):
    path = base / fonte['arquivo']
    if not path.is_file() or _sha256(path) != fonte.get('sha256'):
        raise ValueError('Hash Formula1Dashboard divergente: {}.'.format(fonte.get('arquivo')))
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('JSON Formula1Dashboard inválido: {}.'.format(fonte.get('arquivo'))) from erro


def _segundos(valor):
    if valor is None:
        return None
    if not isinstance(valor, str) or ':' not in valor:
        raise ValueError('Tempo Formula1Dashboard inválido.')
    minuto, segundo = valor.split(':', 1)
    try:
        return int(minuto) * 60 + float(segundo)
    except ValueError as erro:
        raise ValueError('Tempo Formula1Dashboard inválido.') from erro


def _fonte(inventario, endpoint):
    achados = [item for item in inventario.get('fontes', []) if item.get('endpoint') == endpoint]
    if len(achados) != 1:
        raise ValueError('Recibo Formula1Dashboard ausente ou ambíguo: {}.'.format(endpoint))
    return dict(achados[0])


def _identidade(linha):
    temporada = linha.get('driver_season')
    if not isinstance(temporada, dict):
        raise ValueError('Identidade Formula1Dashboard ausente.')
    numero, externo = temporada.get('driver_number'), temporada.get('constructor_id')
    if not isinstance(numero, int) or not isinstance(externo, int):
        raise ValueError('Número/equipe Formula1Dashboard inválidos.')
    if numero not in MAPEAMENTO_2026 or externo not in CONSTRUTORES_EXTERNOS_2026:
        if temporada.get('role') == 'rookie_practice':
            return None, numero, externo, temporada
        raise ValueError('Mapeamento literal Formula1Dashboard ausente: {}.'.format(numero))
    piloto_id, equipe_id, primeiro, ultimo, equipe = MAPEAMENTO_2026[numero]
    nome = '{} {}'.format(primeiro, ultimo)
    if linha.get('driver_name') != nome or linha.get('team_name') != equipe:
        raise ValueError('Identidade Formula1Dashboard diverge do mapeamento literal: {}.'.format(numero))
    if CONSTRUTORES_EXTERNOS_2026[externo] != equipe_id:
        raise ValueError('Equipe Formula1Dashboard diverge do mapeamento literal: {}.'.format(numero))
    return {'piloto_id': piloto_id, 'equipe_id': equipe_id, 'piloto': nome, 'equipe': equipe}, numero, externo, temporada


def carregar(base):
    base = Path(base)
    inventario_path = base / 'inventario.json'
    try:
        inventario = json.loads(inventario_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ValueError('Inventário Formula1Dashboard inválido.') from erro
    if inventario.get('schema') != 'pitwall-formula1dashboard-sessions-v1':
        raise ValueError('Inventário Formula1Dashboard com schema inválido.')
    identidade = inventario.get('identidade')
    if identidade != {'temporada': 2026, 'rodada': 18, 'meeting_key': 1297,
                      'corrida': 'United States Grand Prix', 'cidade': 'Austin', 'circuito_id': 'americas'}:
        raise ValueError('Evento Formula1Dashboard inválido.')
    fontes = {nome: _fonte(inventario, nome) for nome in ('grand-prix', 'sessions', 'results')}
    grand_prix, sessoes, resultados = (_json(base, fontes[nome]) for nome in ('grand-prix', 'sessions', 'results'))
    evento = [item for item in grand_prix if item.get('meeting_key') == 1297 and item.get('round') == 18
              and item.get('year') == 2026 and item.get('name') == 'United States Grand Prix'
              and item.get('city') == 'Austin']
    if len(evento) != 1:
        raise ValueError('Evento Formula1Dashboard ausente ou ambíguo.')
    chaves = {item.get('session_name'): item.get('session_key') for item in sessoes if item.get('session_name') in SESSOES}
    if chaves != {nome: chave for nome, (_, chave) in SESSOES.items()}:
        raise ValueError('Sessão Formula1Dashboard ausente ou divergente.')
    grupos = {nome: [] for nome in SESSOES}
    for linha in resultados:
        tipo = linha.get('session_type')
        if tipo not in SESSOES:
            raise ValueError('Sessão Formula1Dashboard fora do escopo.')
        if (linha.get('year'), linha.get('round'), linha.get('meeting_key'), linha.get('session_key')) != (2026, 18, 1297, SESSOES[tipo][1]):
            raise ValueError('Resultado Formula1Dashboard de outro evento ou sessão.')
        grupos[tipo].append(linha)
    if sum(map(len, grupos.values())) != 88 or any(len(linhas) != 22 for linhas in grupos.values()):
        raise ValueError('Cobertura Formula1Dashboard incompleta.')
    saida = {}
    for tipo, (chave, session_key) in SESSOES.items():
        linhas, posicoes, numeros = [], set(), set()
        for bruto in sorted(grupos[tipo], key=lambda valor: (valor.get('position', 999), valor.get('driver_id', 999))):
            posicao = bruto.get('position')
            if not isinstance(posicao, int) or posicao <= 0 or posicao in posicoes:
                raise ValueError('Posição Formula1Dashboard inválida ou duplicada.')
            canonica, numero, externo, temporada = _identidade(bruto)
            if numero in numeros:
                raise ValueError('Número Formula1Dashboard duplicado.')
            numeros.add(numero); posicoes.add(posicao)
            tempo = bruto.get('time')
            linha = {
                'posicao': posicao, 'numero_carro': numero, 'piloto': bruto.get('driver_name'),
                'piloto_id': None if canonica is None else canonica['piloto_id'],
                'equipe': bruto.get('team_name'), 'equipe_id': None if canonica is None else canonica['equipe_id'],
                'driver_id_externo': bruto.get('driver_id'), 'constructor_id_externo': externo,
                'papel': temporada.get('role'), 'tempo': tempo, 'tempo_segundos': _segundos(tempo),
                'gap_lider': bruto.get('gap_to_leader'), 'gap_anterior': bruto.get('gap_to_previous'),
                'voltas': bruto.get('laps'), 'status': bruto.get('completion_status_code'),
                'q1': bruto.get('q1_time'), 'q1_segundos': _segundos(bruto.get('q1_time')),
                'q2': bruto.get('q2_time'), 'q2_segundos': _segundos(bruto.get('q2_time')),
                'q3': bruto.get('q3_time'), 'q3_segundos': _segundos(bruto.get('q3_time')),
                'q1_status': bruto.get('q1_completion_status_code'), 'q2_status': bruto.get('q2_completion_status_code'),
                'q3_status': bruto.get('q3_completion_status_code'),
            }
            if canonica is None and linha['papel'] != 'rookie_practice':
                raise ValueError('Participante Formula1Dashboard sem identidade canônica.')
            linhas.append(linha)
        if posicoes != set(range(1, 23)):
            raise ValueError('Cobertura de posições Formula1Dashboard incompleta.')
        validos = [item['tempo_segundos'] for item in linhas if item['tempo_segundos'] is not None]
        fonte = fontes['results']
        saida[chave] = {'session_type': tipo, 'session_key': session_key, 'linhas': linhas,
                         'cobertura': len(linhas), 'obtido_em_utc': fonte['obtido_em_utc'],
                         'sha256': fonte['sha256'], 'url': fonte['url_real'],
                         'menor_tempo_segundos': min(validos) if validos else None}
    return {'origem': ORIGEM, 'normalizacao': VERSAO_NORMALIZACAO, 'snapshot_id': inventario['snapshot_id'],
            'evento': identidade, 'sessoes': saida, 'fontes': fontes, 'arquivos': [inventario_path, *(base / f['arquivo'] for f in fontes.values())]}
