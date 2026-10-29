"""Leitor portátil do acervo descritivo; não importa coletores ou modelos."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path

ASSET = 'frontend_assets/acervo_dashboard.json'
SCHEMA = 'pitwall-acervo-dashboard-v1'
VERSAO = '2026-10-28-acervo-1'
MAX_BYTES = 12 * 1024 * 1024


class AcervoDashboardErro(ValueError):
    pass


def conteudo_sha256(gps):
    return sha256(json.dumps(gps, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _int(value, label, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AcervoDashboardErro('{} inválido no acervo.'.format(label))
    return value


def _number(value, label):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                              or not math.isfinite(value)):
        raise AcervoDashboardErro('{} inválido no acervo.'.format(label))


def _utc(value):
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if d.tzinfo is None or d.utcoffset().total_seconds() != 0:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise AcervoDashboardErro('Horário UTC inválido no acervo.')


def validar(asset):
    if not isinstance(asset, dict) or asset.get('schema') != SCHEMA or asset.get('versao') != VERSAO:
        raise AcervoDashboardErro('Versão do acervo de apresentação não reconhecida.')
    gps = asset.get('gps')
    if not isinstance(gps, dict) or not gps or asset.get('conteudo_sha256') != conteudo_sha256(gps):
        raise AcervoDashboardErro('Conteúdo ou hash do acervo não confere.')
    sessions = set()
    for key, gp in gps.items():
        if not isinstance(gp, dict) or not isinstance(gp.get('identidade'), dict):
            raise AcervoDashboardErro('Identidade de GP ausente no acervo.')
        identity = gp['identidade']
        year = _int(identity.get('temporada'), 'Temporada')
        round_ = _int(identity.get('rodada'), 'Rodada')
        if year not in (2024, 2025, 2026) or key != '{}:{}'.format(year, round_):
            raise AcervoDashboardErro('GP fora da identidade declarada no acervo.')
        if not isinstance(identity.get('circuito_id'), str) or not identity['circuito_id']:
            raise AcervoDashboardErro('Circuito ausente no acervo.')
        for name in ('sessoes', 'estrategias', 'paradas', 'equipes', 'cobertura'):
            if not isinstance(gp.get(name), list):
                raise AcervoDashboardErro('Bloco {} ausente no acervo.'.format(name))
        local_sessions = set(); session_names = {}
        for session in gp['sessoes']:
            skey = _int(session.get('session_key'), 'Sessão')
            if skey in sessions:
                raise AcervoDashboardErro('Sessão duplicada ou associada a outro GP.')
            sessions.add(skey); local_sessions.add(skey)
            _utc(session.get('inicio_utc')); _utc(session.get('fim_utc'))
            if datetime.fromisoformat(session['fim_utc'].replace('Z','+00:00')) < datetime.fromisoformat(session['inicio_utc'].replace('Z','+00:00')):
                raise AcervoDashboardErro('Fim da sessão anterior ao início.')
            session_names[skey] = session.get('nome')
            _int(session.get('n_voltas'), 'Contagem de voltas', 0)
            if not isinstance(session.get('tempos'), list):
                raise AcervoDashboardErro('Tempos da sessão ausentes.')
            numbers = set()
            for row in session['tempos']:
                number = _int(row.get('numero'), 'Número do piloto')
                if number in numbers:
                    raise AcervoDashboardErro('Piloto duplicado nos tempos de sessão.')
                numbers.add(number)
                if row.get('posicao') is not None:
                    _int(row['posicao'], 'Posição')
                if row.get('voltas') is not None:
                    _int(row['voltas'], 'Voltas do piloto', 0)
                for field in ('duracao', 'gap', 'q1', 'q2', 'q3'):
                    if row.get(field) is not None and not isinstance(row[field], str):
                        raise AcervoDashboardErro('Tempo exibido inválido.')
        climate = gp.get('clima')
        if not isinstance(climate, dict) or not isinstance(climate.get('horas'), list):
            raise AcervoDashboardErro('Clima ausente no acervo.')
        hours = set()
        for hour in climate['horas']:
            date = hour.get('data_utc'); _utc(date)
            if date in hours:
                raise AcervoDashboardErro('Hora meteorológica duplicada.')
            hours.add(date)
            for field in ('temperatura_c', 'umidade', 'precipitacao_mm', 'vento_ms', 'pressao_hpa'):
                _number(hour.get(field), field)
        for strategy in gp['estrategias']:
            if strategy.get('session_key') not in local_sessions or strategy.get('modalidade') not in ('Race', 'Sprint'):
                raise AcervoDashboardErro('Estratégia não pertence à corrida ou Sprint deste GP.')
            if session_names[strategy['session_key']] != strategy['modalidade']:
                raise AcervoDashboardErro('Modalidade da estratégia difere da sessão de origem.')
            if not isinstance(strategy.get('sequencia_stints'), list):
                raise AcervoDashboardErro('Sequência de pneus ausente.')
        if not isinstance(gp.get('historico'), dict):
            raise AcervoDashboardErro('Histórico descritivo ausente.')
    coverage = asset.get('cobertura', {})
    if coverage.get('gps') != len(gps) or coverage.get('sessoes') != len(sessions):
        raise AcervoDashboardErro('Cobertura declarada não confere com os GPs/sessões.')
    return asset


def carregar(raiz):
    root = Path(raiz).resolve()
    path = root / ASSET
    current = path
    while current != root:
        if current.is_symlink():
            raise AcervoDashboardErro('O acervo não pode usar symlink.')
        current = current.parent
    try:
        if path.stat().st_size > MAX_BYTES:
            raise AcervoDashboardErro('Acervo portátil excede o limite de tamanho.')
        raw = path.read_bytes()
        asset = json.loads(raw.decode('utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        return validar(asset)
    except AcervoDashboardErro:
        raise
    except (OSError, UnicodeDecodeError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise AcervoDashboardErro('Acervo descritivo local indisponível ou inválido: {}.'.format(error)) from error


def para_gp(asset, temporada, rodada, circuito_id=None):
    year = _int(temporada, 'Temporada'); round_ = _int(rodada, 'Rodada')
    result = asset.get('gps', {}).get('{}:{}'.format(year, round_))
    if result is None:
        return None
    identity = result.get('identidade', {})
    if identity.get('temporada') != year or identity.get('rodada') != round_:
        raise AcervoDashboardErro('Identidade do GP selecionado não confere.')
    if circuito_id is not None and identity.get('circuito_id') != circuito_id:
        raise AcervoDashboardErro('Circuito selecionado não corresponde ao acervo.')
    return deepcopy(result)
