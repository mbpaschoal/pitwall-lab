"""Serial, bounded post-session collection. Never trains or emits predictions."""
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from pitwall.paths import PROJECT_ROOT
from pitwall.data.archive_collection import CaptureClient, instant, save_checkpoint
from operacao2026.fontes import _lock
from operacao2026.weekend_projection import DriverIdentityUnavailable, verify_driver_profiles

ENDPOINTS = ('race_control', 'drivers', 'session_result', 'weather', 'laps', 'stints', 'pit')
NAMES = ('Practice 1', 'Practice 2', 'Practice 3', 'Qualifying', 'Race')
SESSION_TYPES = {
    'Practice 1': ('Practice',), 'Practice 2': ('Practice',), 'Practice 3': ('Practice',),
    'Qualifying': ('Qualifying',), 'Race': ('Race',),
    'Sprint Qualifying': ('Sprint Qualifying', 'Qualifying'), 'Sprint': ('Race', 'Sprint'),
}


class ProviderAccessUnavailable(RuntimeError):
    """Public historical access is temporarily restricted; raw receipt is kept."""
    def __init__(self, status):
        self.status=status
        super().__init__('OpenF1 public access restricted (HTTP {})'.format(status))


def load_event(path):
    event = json.loads(Path(path).read_text())
    if event.get('schema') != 'pitwall-weekend-event-v1':
        raise ValueError('Unknown weekend configuration')
    if type(event.get('temporada')) is not int or event['temporada'] != 2026 or type(event.get('rodada')) is not int or not 1 <= event['rodada'] <= 24 or not re.fullmatch(r'[a-zA-Z0-9_-]+', event.get('circuito_id','')):
        raise ValueError('Invalid canonical event identity')
    sessions = event['sessions']
    names = [s['session_name'] for s in sessions]
    if not {'Practice 1', 'Qualifying', 'Race'}.issubset(names) or len(names) != len(set(names)) or any(n not in SESSION_TYPES for n in names):
        raise ValueError('Missing or duplicated session')
    if len({s['session_key'] for s in sessions}) != len(sessions) or len({s['meeting_key'] for s in sessions}) != 1:
        raise ValueError('Ambiguous session identity')
    for session in sessions:
        if session['session_type'] not in SESSION_TYPES[session['session_name']]:
            raise ValueError('Invalid session type')
        if session['year'] != event['temporada'] or session['location'] != event['location'] or session['country_name'] != event['country_name']:
            raise ValueError('Session belongs to another event')
        if instant(session['date_end']) <= instant(session['date_start']):
            raise ValueError('Invalid session interval')
    race = next(s for s in sessions if s['session_name'] == 'Race')
    if instant(race['date_start']) != instant(event['largada_utc']) or race['date_start'][:10] != event['data']:
        raise ValueError('Race/calendar mismatch')
    return event


def verify_rows(rows, session):
    if not isinstance(rows, list):
        raise ValueError('Unavailable endpoint')
    for row in rows:
        if row.get('session_key') != session['session_key'] or row.get('meeting_key') != session['meeting_key']:
            raise ValueError('Endpoint contains another session')


def finished(rows, session):
    verify_rows(rows, session)
    flags = [r for r in rows if r.get('message') == 'SESSION FINISHED'
             and (session['session_name'] not in ('Qualifying', 'Sprint Qualifying') or r.get('qualifying_phase') == 3)]
    if any(instant(r['date']) < instant(session['date_start']) for r in flags):
        raise ValueError('Finish before session start')
    return max((instant(r['date']) for r in flags), default=None)


def cached_session(entry, root):
    if entry.get('estado') != 'dados_recebidos':
        return False
    for source in entry.get('fontes', []):
        path = root / source['arquivo_local']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Previously completed snapshot changed')
    return bool(entry.get('fontes'))


def retry_deadline(manifest):
    deadlines = []
    for item in manifest.get('fontes', []):
        if item.get('status') != 429:
            continue
        value = str(item.get('retry_after', '3600'))
        try:
            deadline = instant(item['obtido_em_utc']) + timedelta(seconds=max(3600, int(value)))
        except ValueError:
            minimum=instant(item['obtido_em_utc'])+timedelta(hours=1)
            try:
                parsed=parsedate_to_datetime(value)
                deadline=max(minimum,parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc))
            except (ValueError,TypeError,OverflowError):
                deadline=minimum
        deadlines.append(deadline)
    return max(deadlines, default=None)


def collect(event_path, root=PROJECT_ROOT, now=None, client_factory=CaptureClient,
            recheck_completed=False, *, recheck_since=None):
    root = Path(root)
    event = load_event(event_path)
    from operacao2026.weekend_reconciliation import load_review, session_review
    review = load_review(root, event)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('UTC clock required')
    base = root / 'data/operacao_2026/fins_de_semana' / ('{}-{}'.format(event['circuito_id'], event['temporada']))
    with _lock(root / 'data/operacao_2026/snapshots'):
        base.mkdir(parents=True, exist_ok=True)
        previous = json.loads((base/'estado.json').read_text()) if (base/'estado.json').exists() else {}
        if previous.get('retry_after_utc') and instant(previous['retry_after_utc']) > now:
            raise RuntimeError('Provider cooldown still active')
        run = base / now.strftime('%Y%m%dT%H%M%S%fZ')
        run.mkdir(exist_ok=False)
        client = client_factory(run, 8)
        state = dict(schema='pitwall-weekend-state-v1', temporada=event['temporada'], rodada=event['rodada'],
                     circuito_id=event['circuito_id'], atualizado_em_utc=now.isoformat(), sessoes=[],
                     uso='Contexto descritivo; não altera previsão registrada.')
        try:
            # This also verifies that the currently published catalogue still agrees.
            catalog = client.capture('openf1', 'sessions', 'sessions.json',
                'https://api.openf1.org/v1/sessions?' + urlencode(dict(year=event['temporada'], country_name=event['country_name'])))
            if not isinstance(catalog, list):
                sources = client.manifest['fontes']
                if catalog is None and sources and sources[-1].get('status') in (401,403):
                    raise ProviderAccessUnavailable(sources[-1]['status'])
                raise ValueError('Session catalogue unavailable')
            for session in event['sessions']:
                matches = [s for s in catalog if s['session_key'] == session['session_key']]
                if len(matches) != 1 or any(matches[0].get(k) != session.get(k) for k in ('meeting_key','session_name','date_start','date_end','location','year')):
                    raise ValueError('Session catalogue changed; review configuration')
                old = next((s for s in previous.get('sessoes', []) if s['session_key'] == session['session_key']), {})
                entry = dict(session_key=session['session_key'], nome=session['session_name'],
                             inicio_utc=session['date_start'], fim_programado_utc=session['date_end'], estado='aguardando_sessao')
                needs_refresh = recheck_completed or (recheck_since is not None and not any(
                    source['endpoint'] == 'session_result' and source['status'] == 200
                    and instant(source['obtido_em_utc']) >= recheck_since
                    for source in old.get('fontes', [])))
                if not needs_refresh and cached_session(old, root):
                    if session_review(review,session) and old.get('revisao_fontes',{}).get('sha256') != review['sha256']:
                        old = dict(old)
                        cached = {source['endpoint']:json.loads((root/source['arquivo_local']).read_text())
                                  for source in old['fontes'] if source['endpoint'] in ENDPOINTS and source['status']==200}
                        project_received(old,cached,session,review)
                    state['sessoes'].append(old)
                    continue
                if now < instant(session['date_end']) + timedelta(minutes=10):
                    state['sessoes'].append(entry)
                    continue
                entry['estado'] = 'aguardando_publicacao'
                data = {}
                before = len(client.manifest['fontes'])
                for endpoint in ENDPOINTS:
                    rows = client.capture('openf1', endpoint, '{}/{}.json'.format(session['session_key'],endpoint),
                        'https://api.openf1.org/v1/{}?session_key={}'.format(endpoint, session['session_key']))
                    if rows is not None:
                        verify_rows(rows, session)
                        data[endpoint] = rows
                    if endpoint == 'race_control' and not finished(data.get(endpoint, []), session):
                        break
                end = finished(data.get('race_control', []), session)
                sources = [client.manifest['fontes'][0]] + client.manifest['fontes'][before:]
                entry['fontes'] = [dict(s, arquivo_local=str((run/s['arquivo']).relative_to(root))) for s in sources]
                entry['cobertura'] = {key:len(data.get(key, [])) for key in ENDPOINTS}
                if end and any(instant(source['obtido_em_utc']) < end for source in sources if source.get('status') == 200):
                    raise ValueError('Source receipt predates observed session finish')
                if end and end <= now and data.get('session_result') and data.get('drivers'):
                    entry['encerramento_observado_utc'] = end.isoformat()
                    project_received(entry, data, session, review)
                else:
                    entry['estado'] = 'encerramento_ou_resultado_pendente'
                state['sessoes'].append(entry)
            race=next((s for s in state['sessoes'] if s['nome']=='Race'),{})
            if race.get('encerramento_observado_utc'):
                from operacao2026.weekend_official import standings
                state['campeonatos']={}
                for field, teams in (('driver_standings',False),('constructor_standings',True)):
                    old=previous.get('campeonatos',{}).get(field,{})
                    fresh = old.get('disponivel') and (recheck_since is None or
                        instant(old['obtido_em_utc']) >= recheck_since)
                    state['campeonatos'][field]=old if fresh and not recheck_completed else standings(client,event,teams)
            meteo = client.capture('open-meteo','forecast','forecast.json', 'https://api.open-meteo.com/v1/forecast?' + urlencode(dict(
                latitude=event['latitude'], longitude=event['longitude'], hourly='temperature_2m,precipitation,weather_code,wind_speed_10m',
                start_date=event['sessions'][0]['date_start'][:10], end_date=event['data'], timezone='UTC', wind_speed_unit='ms')))
            available = isinstance(meteo, dict) and 'hourly' in meteo
            state['previsao_meteorologica'] = dict(natureza='previsao_arquivada', disponivel=available, url='https://open-meteo.com/', horas=[])
            if available:
                hourly = meteo['hourly']
                fields = ('temperature_2m','precipitation','wind_speed_10m')
                if any(len(hourly.get(k,[])) != len(hourly['time']) for k in fields):
                    raise ValueError('Meteorological series have different lengths')
                state['previsao_meteorologica']['horas'] = [dict(hora_utc=t+'Z', **{k:hourly[k][i] for k in fields}) for i,t in enumerate(hourly['time'])]
            state['atualizado_em_utc'] = max((f['obtido_em_utc'] for f in client.manifest['fontes']), default=now.isoformat())
        finally:
            deadline = retry_deadline(client.manifest)
            if deadline:
                state['retry_after_utc'] = deadline.isoformat()
            save_checkpoint(run/'estado.json', state)
            # Preserve the previous usable state even after a late failure.
            # Rate limits still survive restarts independently of this attempt.
            if deadline:
                save_checkpoint(base/'estado.json',dict(previous, retry_after_utc=deadline.isoformat()))
        # Only a normally completed collection can become the next checkpoint.
        save_checkpoint(base/'estado.json',state)
        return state


def project_received(entry, data, session, review=None):
    from operacao2026.weekend_reconciliation import reconcile, mark_tyre_gaps, reviewed_practice_classification
    from pitwall.data.race_weather import RaceWeatherError
    normalized, audit = reconcile(data,session,review)
    classification = reviewed_practice_classification(normalized, session, review)
    entry['estado'] = ('dados_recebidos' if all(key in normalized for key in ENDPOINTS)
                      and bool(normalized.get('weather'))
                      and (classification or len(normalized['session_result']) == len(normalized['drivers'])) else 'parcial')
    if audit:
        if classification:
            audit['acoes'].append(classification)
        entry['revisao_fontes']=audit
        entry['cobertura_validada']={key:len(normalized.get(key,[])) for key in ENDPOINTS}
    for key in ('lacunas_documentadas','qualidade_clima'):
        entry.pop(key,None)
    project_session(entry,normalized,session)
    mark_tyre_gaps(entry,session,review)
    if session['session_name']=='Race' and normalized.get('weather'):
        try:
            entry['clima_observado']=observed_weather(normalized,session,review)
        except RaceWeatherError as error:
            entry['estado']='parcial'
            entry['qualidade_clima']=str(error)


def observed_weather(data, session, review=None):
    """Apply operational sensor review without changing historical audit policy.

    An isolated zero between two track readings >=20 C (at most 180 seconds
    away, in the same active interval) is retained as evidence, but blocks
    publication of that field's mean. No interpolation or replacement occurs.
    """
    from pitwall.data.race_weather import race_windows, summarize_sensors
    window = race_windows(data['race_control'], session['session_key'], not_before=session['date_start'])
    result = summarize_sensors(data['weather'], window)
    anomalies = []
    for start, end in window['intervalos_ativos']:
        points = sorted([(instant(row['date']), index, row) for index, row in enumerate(data['weather'])
                         if instant(start) <= instant(row['date']) < instant(end)], key=lambda point:point[0])
        for previous, current, following in zip(points, points[1:], points[2:]):
            if (current[2].get('track_temperature') == 0
                and all(isinstance(point[2].get('track_temperature'), (int,float)) and point[2]['track_temperature'] >= 20
                        for point in (previous, following))
                and (current[0]-previous[0]).total_seconds() <= 180
                and (following[0]-current[0]).total_seconds() <= 180):
                anomalies.append(dict(indice_fonte=current[1], data=current[2]['date'], valor=0,
                                      anterior=previous[2]['track_temperature'], posterior=following[2]['track_temperature']))
    if anomalies:
        result['campos']['track_temperature']['elegivel'] = False
        result['campos']['track_temperature']['qualidade'] = dict(codigo='zero_isolado_em_conferencia', registros=anomalies,
            uso_media='Diagnóstico bruto; não publicar como temperatura representativa.')
        from operacao2026.weekend_reconciliation import session_review, sources
        approvals = (session_review(review,session) or {}).get('exclusoes_clima',[])
        approved = [a for a in anomalies if any(instant(a['data'])==instant(p['date'])
                    and (a['valor'],a['anterior'],a['posterior']) == (p['track_temperature'],p['anterior'],p['posterior'])
                    for p in approvals)]
        if len(approved)==len(anomalies):
            selected=[dict(row) for row in data['weather']]
            for anomaly in approved:
                selected[anomaly['indice_fonte']]['track_temperature']=None
            validated=summarize_sensors(selected,window)['campos']['track_temperature']
            validated['qualidade']=dict(codigo='zero_isolado_excluido',registros=approved,n_excluidos=len(approved),
                diagnostico_bruto=result['campos']['track_temperature'],fontes=sources(review,sorted({name for p in approvals for name in p['fontes']})),
                metodo='Excluir apenas a célula adjudicada; sem interpolar. Cobertura e intervalo máximo recalculados.')
            result['campos']['track_temperature']=validated
    return result



def project_session(entry, data, session):
    """Withhold each unresolved projection; keep independent validated tables."""
    from operacao2026.weekend_projection import project
    verify_driver_profiles(data, endpoints=())  # Conflicts always fail, even in another group.
    issues = []
    for key in ('tempos', 'dados_descritivos', 'qualidade_identidade', 'motivo_parcial'):
        entry.pop(key, None)
    try:
        entry['tempos'] = session_times(data, session)
    except DriverIdentityUnavailable as error:
        issues.append(dict(grupo='tempos', numeros=error.numbers))
    descriptions = {}
    for endpoint, field in (('laps', 'voltas_por_piloto'), ('stints', 'estrategias'), ('pit', 'paradas')):
        if endpoint not in data:
            continue
        try:
            subset = dict(drivers=data['drivers'], **{endpoint:data[endpoint]})
            descriptions[field] = project(subset, session)[field]
        except DriverIdentityUnavailable as error:
            issues.append(dict(grupo=field, numeros=error.numbers))
    if descriptions:
        entry['dados_descritivos'] = descriptions
    if issues:
        entry['estado'] = 'parcial'
        entry['qualidade_identidade'] = dict(codigo='cadastro_piloto_ausente',
            numero=issues[0]['numeros'][0], grupos_bloqueados=issues)
        entry['motivo_parcial'] = 'Cadastro de piloto ausente na fonte.'


def session_times(data, session):
    verify_driver_profiles(data, endpoints=('session_result',))
    drivers = {d['driver_number']:d for d in data['drivers']}
    if len(drivers) != len(data['drivers']):
        raise ValueError('Duplicated driver number')
    rows, seen = [], set()
    for result in data['session_result']:
        number = result['driver_number']
        if type(number) is not int or number <= 0 or number in seen:
            raise ValueError('Result identity invalid/duplicated')
        if number not in drivers:
            raise DriverIdentityUnavailable(number)
        seen.add(number)
        driver = drivers[number]
        from operacao2026.openf1_qualificacao import MAPEAMENTO_2026
        mapped = MAPEAMENTO_2026.get(number)
        canonical_id = (mapped[0] if mapped and
            (driver.get('first_name'),driver.get('last_name'),driver.get('team_name'))
            == (mapped[2],mapped[3],mapped[4]) else None)
        rows.append(dict(numero=number, piloto_id=canonical_id, piloto=driver.get('full_name') or driver.get('broadcast_name'),
                         equipe=driver.get('team_name'), posicao=result.get('position'),
                         duracao=result.get('duration'), gap=result.get('gap_to_leader'), voltas=result.get('number_of_laps')))
        if result.get('dsq'):
            rows[-1]['status']='DSQ'
            rows[-1]['duracao']=None
        elif result.get('dnf') and result.get('fonte_validacao'):
            rows[-1]['status']='NC'
        if result.get('fonte_validacao'):
            rows[-1]['fonte_validacao']=result['fonte_validacao']
        duration = result.get('duration')
        if session.get('session_name') in ('Qualifying', 'Sprint Qualifying') and isinstance(duration, list):
            if len(duration) > 3:
                raise ValueError('Unknown qualifying duration phases')
            for i, field in enumerate(('q1', 'q2', 'q3')):
                rows[-1][field] = duration[i] if i < len(duration) else None
    return rows


def public_status(state):
    allowed = ('temporada','rodada','circuito_id','atualizado_em_utc','previsao_meteorologica','campeonatos')
    public = {key:state[key] for key in allowed if key in state}
    public['schema'] = 'pitwall-weekend-public-v1'
    public['sessoes'] = [{k:v for k,v in s.items() if k not in ('fontes',)} for s in state['sessoes']]
    for target, source in zip(public['sessoes'], state['sessoes']):
        target['fontes'] = [{k:v for k,v in f.items() if k in ('provider','endpoint','url','status','obtido_em_utc','sha256')} for f in source.get('fontes', [])]
    return public


def qualification_bundle(event_path, state, root=PROJECT_ROOT):
    """Preserve original bytes and receipts; no fabricated pagination or UTC."""
    import shutil
    root = Path(root)
    event = load_event(event_path)
    if any(state.get(k) != event[k] for k in ('temporada','rodada','circuito_id')):
        raise ValueError('Snapshot/event mismatch')
    entry = next((s for s in state['sessoes'] if s['nome'] == 'Qualifying'), None)
    if not entry or entry['estado'] != 'dados_recebidos':
        return None
    required = ('sessions','session_result','drivers','race_control')
    selected = []
    for endpoint in required:
        sources = [s for s in entry['fontes'] if s['endpoint'] == endpoint and s['status'] == 200]
        if len(sources) != 1:
            raise ValueError('Qualification source absent/ambiguous')
        selected.append(sources[0])
    identity = hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()[:16]
    base = root/'data/operacao_2026/fontes_alternativas'/('q-{}-{}-{}'.format(event['temporada'],event['circuito_id'],identity))
    manifest = dict(schema='pitwall-source-availability-evidence-v1',sha256_arquivos={},fontes=[])
    if not base.exists():
        base.mkdir(parents=True)
        for source in selected:
            raw = root/source['arquivo_local']
            if hashlib.sha256(raw.read_bytes()).hexdigest() != source['sha256']:
                raise ValueError('Qualification raw changed')
            name = 'openf1-q-{}.json'.format(source['endpoint'])
            shutil.copyfile(raw,base/name)
            manifest['sha256_arquivos'][name] = source['sha256']
            manifest['fontes'].append(dict(source,arquivo=name,url_solicitada=source['url']))
        save_checkpoint(base/'inventario.json',manifest)
    from operacao2026.openf1_qualificacao import carregar, MAPEAMENTO_2026
    expected = next(s for s in event['sessions'] if s['session_name']=='Qualifying')
    carregar(base,sessao_esperada=expected,prefixo='openf1-q',mapeamento=MAPEAMENTO_2026)
    return base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evento', type=Path, required=True)
    parser.add_argument('--rever-concluidas', action='store_true', help='Reconsultar dados encerrados sem apagar snapshots anteriores.')
    parser.add_argument('--publicar-status', action='store_true')
    parser.add_argument('--preparar-qualificacao', action='store_true')
    args = parser.parse_args()
    state = collect(args.evento,recheck_completed=args.rever_concluidas)
    if args.preparar_qualificacao:
        bundle = qualification_bundle(args.evento,state)
        print(json.dumps({'qualificacao':str(bundle) if bundle else None}))
    if args.publicar_status:
        save_checkpoint(PROJECT_ROOT/'frontend_assets/operacao_fim_semana.json',public_status(state))
    print(json.dumps(public_status(state),ensure_ascii=False))


if __name__ == '__main__':
    main()
