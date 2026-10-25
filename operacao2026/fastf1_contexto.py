"""Integração FastF1 opcional e isolada para contexto público pós-sessão.

Este módulo não participa da matriz, da inferência ou da fonte canônica de
classificação. Ele grava apenas fotografias locais de sessões já encerradas.
"""
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re


SESSOES = frozenset(('FP1', 'FP2', 'FP3', 'Q'))
SCHEMA = 'pitwall-fastf1-session-snapshot-v1'
_SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
_HEX = re.compile(r'^[0-9a-f]{64}$')


class FastF1Indisponivel(RuntimeError):
    pass


class SessaoIndisponivel(RuntimeError):
    pass


def _utc(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError('Horário de coleta FastF1 deve ter UTC explícito.')
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _id(value):
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value) or '..' in value:
        raise ValueError('ID de snapshot FastF1 inseguro.')
    return value


def _sessao(value):
    normalized = str(value).upper()
    if normalized not in SESSOES:
        raise ValueError('Sessão FastF1 inválida. Use FP1, FP2, FP3 ou Q.')
    return normalized


def _texto(value, nome):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('{} FastF1 ausente.'.format(nome))
    return value.strip()


def _event_field(event, *keys):
    for key in keys:
        try:
            value = event[key]
        except (KeyError, TypeError, IndexError):
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _event_date(event, fallback):
    value = _event_field(event, 'EventDate', 'Date')
    if value:
        return value[:10]
    return fallback


def _event_metadata(event, sessao, esperado):
    circuito = esperado.get('Circuit', {})
    local = circuito.get('Location', {}) if isinstance(circuito, dict) else {}
    return {
        'temporada': int(esperado['season']),
        'rodada': int(esperado['round']),
        'circuito_id': _texto(circuito.get('circuitId'), 'circuito'),
        'nome': _event_field(event, 'EventName', 'OfficialEventName') or _texto(esperado.get('raceName'), 'nome do GP'),
        'cidade': _event_field(event, 'Location') or _texto(local.get('locality'), 'cidade'),
        'pais': _event_field(event, 'Country') or _texto(local.get('country'), 'país'),
        'data': _event_date(event, _texto(esperado.get('date'), 'data do GP')),
        'sessao': sessao,
    }


def _normalizar(value):
    """Converte apenas dados tabulares públicos em JSON determinístico."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, 'item'):
        try:
            return _normalizar(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, datetime):
        return _utc(value)
    if isinstance(value, dict):
        return {str(key): _normalizar(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalizar(item) for item in value]
    return str(value)


def _dados_nao_carregados(error):
    return (error.__class__.__name__ == 'DataNotLoadedError'
            and error.__class__.__module__.startswith('fastf1.'))


def _atributo_publico(sessao, nome, padrao=None):
    try:
        return getattr(sessao, nome, padrao)
    except Exception as error:
        if _dados_nao_carregados(error):
            raise SessaoIndisponivel('Sessão FastF1 ainda não está disponível publicamente: {}.'.format(error)) from error
        raise


def _resultados(sessao):
    tabela = _atributo_publico(sessao, 'results', None)
    if tabela is None:
        return []
    try:
        rows = tabela.to_dict('records')
    except (AttributeError, TypeError, ValueError) as error:
        raise SessaoIndisponivel('FastF1 não publicou resultados tabulares para esta sessão.') from error
    except Exception as error:
        if _dados_nao_carregados(error):
            raise SessaoIndisponivel('FastF1 não publicou resultados tabulares para esta sessão.') from error
        raise
    if not isinstance(rows, list):
        raise SessaoIndisponivel('FastF1 não publicou resultados tabulares para esta sessão.')
    return _normalizar(rows)


def _modulo(modulo_fastf1):
    if modulo_fastf1 is not None:
        return modulo_fastf1
    try:
        return importlib.import_module('fastf1')
    except ImportError as error:
        raise FastF1Indisponivel(
            'FastF1 opcional não está instalado neste ambiente; instale-o manualmente antes da coleta.'
        ) from error


def _load(sessao):
    try:
        sessao.load(telemetry=False, weather=False, messages=False)
    except Exception as error:
        raise SessaoIndisponivel('Sessão FastF1 ainda não está disponível publicamente: {}.'.format(error)) from error


def _session_key(sessao):
    info = _atributo_publico(sessao, 'session_info', None)
    try:
        value = info['Key']
    except (KeyError, TypeError, IndexError) as error:
        raise SessaoIndisponivel('FastF1 não forneceu session key para esta sessão.') from error
    if value is None or not str(value).strip():
        raise SessaoIndisponivel('FastF1 não forneceu session key para esta sessão.')
    return str(value)


def coletar_sessao(root, snapshot_id, evento_jolpica, sessao, modulo_fastf1=None, agora=None):
    """Coleta uma única sessão já disponível; não faz polling nem toca Jolpica."""
    root = Path(root)
    snapshot_id, sessao = _id(snapshot_id), _sessao(sessao)
    destino = root / snapshot_id
    if destino.exists():
        raise FileExistsError('Snapshot FastF1 já existe e foi preservado: {}.'.format(destino))
    modulo = _modulo(modulo_fastf1)
    cache = root / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    try:
        modulo.Cache.enable_cache(str(cache))
        objeto = modulo.get_session(int(evento_jolpica['season']), int(evento_jolpica['round']), sessao)
    except Exception as error:
        raise SessaoIndisponivel('Sessão {} ainda não está disponível publicamente: {}.'.format(sessao, error)) from error
    _load(objeto)
    dados = {
        'schema': SCHEMA,
        'snapshot_id': snapshot_id,
        'fonte': 'FastF1',
        'obtido_em_utc': _utc(agora),
        'sessao': sessao,
        'session_key': _session_key(objeto),
        'gp': _event_metadata(_atributo_publico(objeto, 'event', {}), sessao, evento_jolpica),
        'resultados_publicos': _resultados(objeto),
    }
    raw = (json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    digest = sha256(raw).hexdigest()
    indice = {
        'schema': SCHEMA,
        'snapshot_id': snapshot_id,
        'fonte': 'FastF1',
        'obtido_em_utc': dados['obtido_em_utc'],
        'sessao': sessao,
        'session_key': dados['session_key'],
        'gp': dados['gp'],
        'arquivo': 'sessao.json',
        'sha256': digest,
    }
    destino.mkdir(parents=True)
    try:
        (destino / 'sessao.json').write_bytes(raw)
        (destino / 'indice.json').write_text(
            json.dumps(indice, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8'
        )
    except Exception:
        for path in (destino / 'sessao.json', destino / 'indice.json'):
            if path.exists():
                path.unlink()
        destino.rmdir()
        raise
    return indice


def validar_snapshot(root, snapshot_id):
    snapshot_id = _id(snapshot_id)
    base = Path(root) / snapshot_id
    try:
        indice = json.loads((base / 'indice.json').read_text(encoding='utf-8'))
        raw = (base / 'sessao.json').read_bytes()
        dados = json.loads(raw.decode('utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Snapshot FastF1 ausente ou ilegível.') from error
    if not isinstance(indice, dict) or indice.get('schema') != SCHEMA or indice.get('snapshot_id') != snapshot_id:
        raise ValueError('Índice FastF1 inválido.')
    if not isinstance(indice.get('sha256'), str) or not _HEX.fullmatch(indice['sha256']) or sha256(raw).hexdigest() != indice['sha256']:
        raise ValueError('Hash do snapshot FastF1 divergente.')
    if not isinstance(dados, dict) or dados.get('schema') != SCHEMA or dados.get('snapshot_id') != snapshot_id:
        raise ValueError('Conteúdo FastF1 inválido.')
    for chave in ('schema', 'snapshot_id', 'fonte', 'obtido_em_utc', 'sessao', 'session_key', 'gp'):
        if indice.get(chave) != dados.get(chave):
            rotulo = 'GP' if chave == 'gp' else chave
            raise ValueError('{} FastF1 divergente entre índice e sessão hasheada.'.format(rotulo))
    if dados.get('fonte') != 'FastF1':
        raise ValueError('Fonte FastF1 inválida.')
    if dados.get('sessao') != indice.get('sessao') or _sessao(dados.get('sessao')) != dados.get('sessao'):
        raise ValueError('Sessão FastF1 divergente.')
    if str(dados.get('session_key')) != str(indice.get('session_key')):
        raise ValueError('Session key FastF1 divergente.')
    gp = dados.get('gp')
    if not isinstance(gp, dict):
        raise ValueError('GP FastF1 ausente.')
    for key in ('temporada', 'rodada'):
        if not isinstance(gp.get(key), int) or gp[key] < 1:
            raise ValueError('GP FastF1 com {} inválida.'.format(key))
    for key in ('circuito_id', 'nome', 'cidade', 'pais', 'data'):
        _texto(gp.get(key), key)
    if not isinstance(dados.get('resultados_publicos'), list):
        raise ValueError('Resultados públicos FastF1 inválidos.')
    indice = dict(indice)
    indice['_conteudo_validado'] = dados
    return indice


def validar_contexto_emissao(root, snapshot_id, evento_jolpica, sessao_esperada='Q'):
    """Valida enriquecimento; não retorna entradas nem afeta a inferência."""
    indice = validar_snapshot(root, snapshot_id)
    sessao_esperada = _sessao(sessao_esperada)
    if indice['sessao'] != sessao_esperada:
        raise ValueError('Snapshot FastF1 é de {}, mas a emissão só aceita {} como contexto.'.format(
            indice['sessao'], sessao_esperada
        ))
    gp = indice['_conteudo_validado']['gp']
    for chave, esperado in (
        ('temporada', int(evento_jolpica['season'])),
        ('rodada', int(evento_jolpica['round'])),
        ('circuito_id', evento_jolpica['Circuit']['circuitId']),
    ):
        if gp.get(chave) != esperado:
            raise ValueError('Snapshot FastF1 de {} divergente da emissão Jolpica.'.format(chave))
    return indice
