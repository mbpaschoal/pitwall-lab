"""Offline, hash-bound additions to the preserved driver-conditions baseline."""
from copy import deepcopy

from pitwall.data.driver_conditions import DriverConditionsError, content_hash, validate

ASSET = 'frontend_assets/pilotos_condicoes_operacao.json'
SCHEMA = 'pitwall-driver-conditions-updates-v1'


def empty(base):
    value = dict(schema=SCHEMA, base_conteudo_sha256=base['conteudo_sha256'], events={}, pending={})
    return seal(value)


def seal(value):
    value['conteudo_sha256'] = content_hash({k:v for k,v in value.items() if k!='conteudo_sha256'})
    return value


def merge(base, updates):
    validate(base)
    if (updates.get('schema') != SCHEMA
            or updates.get('base_conteudo_sha256') != base['conteudo_sha256']
            or updates.get('conteudo_sha256') != content_hash({k:v for k,v in updates.items() if k!='conteudo_sha256'})
            or not isinstance(updates.get('events'),dict) or not isinstance(updates.get('pending'),dict)):
        raise DriverConditionsError('Invalid or incompatible driver-condition update')
    result = deepcopy(base)
    for key, event in sorted(updates['events'].items()):
        gp, rows = event['gp'], event['results']
        if key in result['gps'] or key != '{}:{}'.format(gp['temporada'],gp['rodada']):
            raise DriverConditionsError('Driver update overlaps a preserved race')
        if not rows or any(row['race_id']!=key for row in rows) or not event.get('sources'):
            raise DriverConditionsError('Missing update population or provenance')
        result['gps'][key] = deepcopy(gp)
        result['resultados'].extend(deepcopy(rows))
    q=result['qualidade']
    q.update(corridas=len(result['gps']),resultados=len(result['resultados']),
             largadas=sum(r['started'] for r in result['resultados']),
             dns=sum(not r['started'] for r in result['resultados']),
             chuva_registrada=sum(g['rain_condition']=='recorded' for g in result['gps'].values()))
    result['atualizacao_operacional'] = dict(base_corridas=base['qualidade']['corridas'],
        adicionadas=len(updates['events']),pendencias=deepcopy(updates['pending']),
        eventos={key:deepcopy(event['sources']) for key,event in updates['events'].items()})
    result['conteudo_sha256']=content_hash({k:v for k,v in result.items() if k!='conteudo_sha256'})
    return validate(result)
