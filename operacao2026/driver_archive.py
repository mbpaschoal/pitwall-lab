"""Append completed, reviewed weekends to descriptive driver comparisons.

The original 66-race projection and the predictive v1 inputs are never written.
Unknown prerequisites retain the last valid event and an explicit pending state.
"""
from copy import deepcopy
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from operacao2026 import cloud, weekend
from operacao2026.fontes import _lock
from pitwall.data.archive_collection import CaptureClient, instant, save_checkpoint
from pitwall.data.driver_conditions import ASSET as BASE, content_hash, validate
from pitwall.data.driver_updates import ASSET, empty, merge, seal


class PendingDriverUpdate(ValueError):
    pass


def native(root, race, endpoint):
    sources=[s for s in race.get('fontes',[]) if s['endpoint']==endpoint and s['status']==200]
    if len(sources)!=1:
        raise PendingDriverUpdate('native_source_unavailable:'+endpoint)
    source=sources[0];root=root.resolve();path=root/source['arquivo_local']
    if any(part.is_symlink() for part in (path,*path.parents)):
        raise ValueError('Symlink in native capture')
    path=path.resolve()
    if not path.is_relative_to(root/'data/operacao_2026/fins_de_semana'):
        raise ValueError('Native source escapes the capture archive')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:
        raise ValueError('Native source hash changed')
    return json.loads(raw), {k:v for k,v in source.items() if k!='arquivo_local'}


def build(event, race, canonical, receipt, raw_results, native_receipt, circuit, now):
    """Validate exact identity and outcomes before exposing any new cohort."""
    if race.get('estado')!='dados_recebidos' or not race.get('encerramento_observado_utc'):
        raise PendingDriverUpdate('race_not_complete')
    end=instant(race['encerramento_observado_utc'])
    if end>now or instant(receipt['obtido_em_utc'])<end or instant(native_receipt['obtido_em_utc'])<end:
        raise ValueError('Source timing is inconsistent with observed race finish')
    metadata=canonical['MRData'];table=metadata['RaceTable'];races=table['Races']
    if int(metadata['offset'])!=0 or len(races)!=1:
        raise PendingDriverUpdate('canonical_result_incomplete')
    source=races[0];rows=source.get('Results',[])
    if (int(source['season']),int(source['round']),source['Circuit']['circuitId'],source['date']) != (
            event['temporada'],event['rodada'],event['circuito_id'],event['data']):
        raise ValueError('Canonical result belongs to another event')
    public={r['numero']:r for r in race.get('tempos',[])}
    natives={r['driver_number']:r for r in raw_results}
    if len(public)!=22 or len(natives)!=22 or len(rows)!=22 or int(metadata['total'])!=22:
        raise PendingDriverUpdate('result_population_incomplete')
    if any((r.get('session_key'),r.get('meeting_key'))!=(race['session_key'],event['sessions'][0]['meeting_key']) for r in raw_results):
        raise ValueError('Native results belong to another race')
    weather=race.get('clima_observado') or {}
    fields=weather.get('campos',{})
    required=('rainfall','track_temperature','air_temperature','humidity','pressure','wind_speed')
    if any(not fields.get(k,{}).get('elegivel') for k in required):
        raise PendingDriverUpdate('race_weather_not_verified')
    if weather.get('condicao_chuva') not in ('com_chuva_registrada','sem_chuva_registrada'):
        raise PendingDriverUpdate('rain_condition_unknown')
    if not circuit or circuit.get('temporada')!=event['temporada'] or circuit.get('circuito_id')!=event['circuito_id']:
        raise PendingDriverUpdate('circuit_edition_not_verified')
    identity='{}:{}'.format(event['temporada'],event['rodada']);out=[];seen=set()
    for row in rows:
        number=int(row['number']);driver=row['Driver'];pid=driver['driverId']
        if number in seen or number not in natives or number not in public:
            raise ValueError('Duplicated or unmatched canonical driver number')
        seen.add(number);observed=public[number];nr=natives[number]
        if observed.get('piloto_id') and observed['piloto_id']!=pid:
            raise ValueError('Canonical/native driver IDs disagree')
        if not observed.get('piloto_id'):
            name=' '.join((driver['givenName']+' '+driver['familyName']).split()).casefold()
            if name!=' '.join(observed['piloto'].split()).casefold():
                raise PendingDriverUpdate('driver_identity_unverified:'+str(number))
        if (row['status']=='Disqualified') != nr.get('dsq'):
            raise PendingDriverUpdate('disqualification_sources_disagree')
        position=None if nr.get('dsq') or nr.get('dns') else observed.get('posicao')
        if position is not None and position!=int(row['position']):
            raise PendingDriverUpdate('canonical_and_observed_result_disagree')
        if observed['voltas']!=int(row['laps']) or nr['number_of_laps']!=int(row['laps']):
            raise PendingDriverUpdate('canonical_and_native_laps_disagree')
        if nr.get('points')!=float(row['points']):
            raise PendingDriverUpdate('canonical_and_native_points_disagree')
        from pitwall.data.driver_source_audit import classify_start
        started,criterion=classify_start(nr,int(row['laps']),0)
        if any(type(nr.get(k)) is not bool for k in ('dnf','dns','dsq')):
            raise PendingDriverUpdate('native_outcome_unknown')
        grid=int(row['grid'])
        out.append(dict(race_id=identity,driver_id=pid,
            driver_name=driver['givenName']+' '+driver['familyName'],team_id=row['Constructor']['constructorId'],
            number=number,started=started,disqualified=nr['dsq'],retired=nr['dnf'],position=position,
            grid=grid if grid>0 else None,grid_raw=row['grid'],points=float(row['points']),
            completed_laps=int(row['laps']),canonical_status=row['status'],start_criterion=criterion,
            canonical_rank_audit=int(row['position'])))
    gp=dict(temporada=event['temporada'],rodada=event['rodada'],circuito_id=event['circuito_id'],
        session_key=race['session_key'],session_name='Race',name=event['nome'],date_utc=weather['inicio_efetivo_utc'][:10],
        race_start_utc=weather['inicio_efetivo_utc'],race_finish_utc=weather['bandeirada_utc'],
        active_intervals_utc=weather['intervalos_ativos'],weather_samples=weather['n_medicoes_ativas'],
        rain_condition='recorded' if weather['condicao_chuva']=='com_chuva_registrada' else 'not_recorded',
        direction=circuit['direction'],corners=circuit['corners'],length_km=circuit['length_km'],
        altitude_m=circuit['altitude_m'],circuit_source_url=circuit['source']['url'],
        circuit_source_sha256=circuit['source']['sha256'],atmospheric_context=None)
    for field in required[1:]:gp[field]=fields[field]['media_amostras']
    gp['wind_direction']=fields.get('wind_direction',{}).get('media_circular_graus')
    gp['wind_direction_status']='available' if gp['wind_direction'] is not None else 'indeterminate'
    gp['available_fields']=[k for k in (*required[1:],'wind_direction','corners','length_km','altitude_m') if gp.get(k) is not None]
    sources=[receipt,native_receipt,circuit['source'],circuit['altitude_source']]+deepcopy(race.get('fontes',[]))
    sources=[{k:v for k,v in s.items() if k not in ('arquivo_local','arquivo_requisicao')} for s in sources]
    return dict(gp=gp,results=out,sources=sources,
                weather_quality=deepcopy(fields['track_temperature'].get('qualidade')))


def update(root, state, event, now=None, client_factory=CaptureClient):
    root=Path(root);now=now or datetime.now(timezone.utc)
    base=validate(json.loads((root/BASE).read_text()));path=root/ASSET
    old=json.loads(path.read_text()) if path.exists() else empty(base)
    merge(base,old)  # A corrupt published update must not silently disappear.
    race=next((s for s in state.get('sessoes',[]) if s['nome']=='Race'),{})
    if cloud.identity(state)!=cloud.identity(event):
        raise ValueError('Weekend state belongs to another event')
    key='{}:{}'.format(event['temporada'],event['rodada'])
    if key in base['gps'] or not race.get('encerramento_observado_utc'):
        return dict(changed=False,status='waiting_or_baseline')
    expected=next(s for s in event['sessions'] if s['session_name']=='Race')
    if race['session_key']!=expected['session_key'] or instant(race['encerramento_observado_utc'])>now:
        raise ValueError('Race identity or observed finish is invalid')
    value=deepcopy(old)
    try:
        circuits=json.loads((root/'operacao2026/driver_circuit_reviews.json').read_text())
        circuit=circuits.get('{}:{}'.format(event['temporada'],event['circuito_id']))
        if not circuit:raise PendingDriverUpdate('circuit_edition_not_verified')
        results,native_receipt=native(root,race,'session_result')
        directory=root/cloud.STATE/('{}-{}'.format(event['circuito_id'],event['temporada']))/'pilotos'
        directory.mkdir(parents=True,exist_ok=True);cache=directory/'consulta.json'
        with _lock(root/'data/operacao_2026/snapshots'):
            record=json.loads(cache.read_text()) if cache.exists() else None
            if record and instant(record['receipt']['obtido_em_utc'])+timedelta(hours=6)>now:
                raw=(root/record['path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=record['receipt']['sha256']:raise ValueError('Canonical cache changed')
                canonical=json.loads(raw);receipt=record['receipt']
            else:
                run=directory/now.strftime('%Y%m%dT%H%M%S%fZ')
                run.mkdir(parents=True,exist_ok=False)
                client=client_factory(run,8)
                try:
                    canonical=client.capture('jolpica','race_results','results.json',
                        'https://api.jolpi.ca/ergast/f1/{}/{}/results/?limit=100&offset=0'.format(event['temporada'],event['rodada']))
                except RuntimeError:
                    if not weekend.retry_deadline(client.manifest):raise
                    canonical=None
                if canonical is None:
                    deadline=weekend.retry_deadline(client.manifest)
                    if deadline:
                        retry_path=root/cloud.STATE/'pilotos-retry/estado.json'
                        retry_path.parent.mkdir(parents=True,exist_ok=True)
                        save_checkpoint(retry_path,
                                        dict(retry_after_utc=deadline.isoformat()))
                    raise PendingDriverUpdate('canonical_result_unavailable')
                receipt=client.manifest['fontes'][-1]
                save_checkpoint(cache,dict(path=str((run/'results.json').relative_to(root)),receipt=receipt))
            candidate=build(event,race,canonical,receipt,results,native_receipt,circuit,now)
        previous=value['events'].get(key)
        # Refreshed identical receipts are not a new data delivery.
        same=previous and all(content_hash(previous.get(k))==content_hash(candidate.get(k)) for k in ('gp','results','weather_quality'))
        if not same:value['events'][key]=candidate
        value['pending'].pop(key,None)
    except PendingDriverUpdate as error:
        value['pending'][key]=dict(code=str(error),race_finish_utc=race['encerramento_observado_utc'],event=event['nome'])
    seal(value);merge(base,value)
    changed=value!=old
    if changed:save_checkpoint(path,value)
    return dict(changed=changed,status='pending' if key in value['pending'] else 'updated',
                pending=value['pending'],races=len(base['gps'])+len(value['events']))


def check_pending(root, now=None):
    root=Path(root);now=now or datetime.now(timezone.utc)
    base=validate(json.loads((root/BASE).read_text()));value=json.loads((root/ASSET).read_text())
    merge(base,value)
    overdue={key:item for key,item in value['pending'].items()
             if instant(item['race_finish_utc'])+timedelta(hours=6)<=now}
    if overdue:
        raise RuntimeError('Driver analyses need review / Análises de pilotos aguardam conferência: '+json.dumps(overdue,ensure_ascii=False))
    return dict(pending=value['pending'],overdue=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('check',))
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(json.dumps(check_pending(args.root),ensure_ascii=False))
