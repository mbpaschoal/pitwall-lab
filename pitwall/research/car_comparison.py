"""Build a retrospective all-team presentation asset; never fit or emit forecasts."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import statistics

TEAMS = {
    'mclaren': 'McLaren', 'mercedes': 'Mercedes', 'red_bull': 'Red Bull', 'ferrari': 'Ferrari',
    'williams': 'Williams', 'racing_bulls': 'Racing Bulls', 'aston_martin': 'Aston Martin',
    'haas': 'Haas', 'audi': 'Audi', 'alpine': 'Alpine', 'cadillac': 'Cadillac',
}
TEAM_NAMES = {'Red Bull Racing': 'red_bull', 'Haas F1 Team': 'haas',
              **{name: key for key, name in TEAMS.items()}}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(asset):
    body={k:v for k,v in asset.items() if k!='content_sha256'}
    return hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def seconds(text):
    if not isinstance(text,str) or not re.fullmatch(r'\d+:\d{2}\.\d{3}',text):return None
    a,b=text.split(':');value=60*int(a)+float(b)
    return value if value>0 and float(b)<60 else None


def legal_q1(row):
    return seconds(row.get('Q1')) if row and row.get('Pos.') not in ('DQ','DSQ','RT') else None


def driver_name(row):
    return re.sub(r'(?<=[a-zÀ-ÿ])[A-Z]{3}$','',row['Driver']).strip()


def classify_component(name):
    s=name.lower()
    if 'floor' in s or 'diffuser' in s:return 'floor'
    if 'front wing' in s or 'nose' in s:return 'front_wing'
    if 'rear wing' in s or 'beam wing' in s or 'brace wing' in s:return 'rear_wing'
    if 'suspension' in s:return 'suspension'
    if 'corner' in s or 'drum' in s or 'wheel' in s:return 'wheels_brakes'
    if any(x in s for x in ('sidepod','cover','cooling','louvre','bodywork')):return 'body_cooling'
    return 'other'


def evaluate_driver(row, reference, laps, mixed):
    reasons=[];time=legal_q1(row);ref_time=legal_q1(reference)
    if time is None:reasons.append('no_legal_q1_time')
    if ref_time is None:reasons.append('no_legal_reference')
    if mixed:reasons.append('wet_or_mixed_session')
    def matches(r,t):
        return [x for x in laps if t is not None and x['driver_number']==int(r['No.'])
                and x['lap_seconds'] is not None and abs(x['lap_seconds']-t)<=.002 and x['eligible_base']]
    a=matches(row,time) if row else [];b=matches(reference,ref_time) if reference else []
    candidates=[(x,y) for x in a for y in b if x['compound']==y['compound']]
    if not candidates:reasons.append('no_matching_dry_laps_same_compound')
    pair=min(candidates,key=lambda p:(p[0]['lap_number'],p[1]['lap_number'])) if candidates else None
    flag_free=any(not x['potential_flag_or_recovery_lap'] and not y['potential_flag_or_recovery_lap'] for x,y in candidates)
    return {'q1_seconds':time,'gap_percent':100*(time/ref_time-1) if not reasons else None,
            'eligible':not reasons,'eligible_no_flags':not reasons and flag_free,
            'exclusion_reasons':reasons,'reference_number':int(reference['No.']) if reference else None,
            'reference_seconds':ref_time,
            'lap_evidence':{'driver_lap':pair[0]['lap_number'],'reference_lap':pair[1]['lap_number'],
                            'compound':pair[0]['compound'],'driver_tyre_age':pair[0]['tyre_age_at_lap_start'],
                            'reference_tyre_age':pair[1]['tyre_age_at_lap_start']} if pair else None}


def team_metric(drivers, no_flags=False):
    eligible=[r['q1']['gap_percent'] for r in drivers if r['q1']['eligible_no_flags' if no_flags else 'eligible']]
    # One driver's measured time does not stand in for a complete two-car team observation.
    complete=len(drivers)==2 and len(eligible)==2
    return {'gap_percent':statistics.mean(eligible) if complete else None,
            'eligible_drivers':len(eligible),'expected_drivers':2,
            'status':'complete' if complete else ('partial' if eligible else 'unavailable')}


def build(source_root, declarations_path, canonical_root):
    source_root=Path(source_root);canonical_root=Path(canonical_root)
    initial=source_root/'exa-results/carros-f1-2026-11-23'
    previous=source_root/'reports/carros_desempenho_20261123_v1'
    official=read(initial/'desempenho_todos_pilotos.json')
    events=read(previous/'eventos.json')
    quality={x['round']:x for x in read(previous/'qualidade_sessoes.json') if x['session']=='qualifying'}
    declarations={(r['round'],r['team_id']):r for r in read(declarations_path)}
    software={(4 if r['event']=='miami' else 15,TEAM_NAMES[r['team']]):r for r in
              read(source_root/'reports/carros_especificacoes_20261123_v1/software_secu_por_equipe.json')}
    contexts={r['rodada']:r for r in read(canonical_root/'frontend_assets/contexto_editorial.json')['eventos'] if r['temporada']==2026}
    for source in read(initial/'manifesto_desempenho.json'):
        data=(initial/source['local_file']).read_bytes()
        assert len(data)==source['bytes'] and hashlib.sha256(data).hexdigest()==source['sha256']
    capture_by_url={s['url']:s for s in read(initial/'manifesto_desempenho.json')}
    qlaps=defaultdict(list)
    for lap in read(previous/'voltas_com_filtros.json'):
        if lap['session']=='qualifying':qlaps[lap['round']].append(lap)
    result=[]
    for event in events:
        rnd=event['round'];context=contexts[rnd]
        assert event['race']['date_start'][:10]==context['data'],(rnd,'event date mismatch')
        race=[x for x in official if x['round']==rnd and x['session']=='race_result']
        qs=[x for x in official if x['round']==rnd and x['session']=='qualifying']
        qrows={int(x['values']['No.']):x['values'] for x in qs}
        legal=[r for r in qrows.values() if legal_q1(r) is not None]
        reference=min(legal,key=lambda r:(legal_q1(r),int(r['No.']))) if legal else None
        grouped=defaultdict(list)
        for source in race:
            r=source['values'];number=int(r['No.']);team=TEAM_NAMES[r['Team']]
            q=qrows.get(number)
            if q:assert TEAM_NAMES[q['Team']]==team
            grouped[team].append({'number':number,'name':driver_name(r),'team_id':team,
                'qualifying_status':q['Pos.'] if q else 'not_listed',
                'q1':evaluate_driver(q,reference,qlaps[rnd],quality[rnd]['wet_or_mixed_session']),
                'race_position':int(r['Pos.']) if r['Pos.'].isdigit() else None,
                'race_status':r['Time / Retired'],'race_points':float(r['Pts.']),
                'race_is_result_not_pace':True})
        assert set(grouped)==set(TEAMS)
        teams=[]
        for team_id,name in TEAMS.items():
            declaration=json.loads(json.dumps(declarations[rnd,team_id]))
            for component in declaration['components']:
                component['category']=classify_component(component['component_original'])
                component['used_exact_driver_session']=None
                component['version_id']=None
            if declaration['event_scope_status']!='source_document_event':
                declaration['status']='event_identity_review'
            else:
                declaration['status']='no_updates_declared' if declaration['no_updates_declared'] else 'updates_declared'
            drivers=sorted(grouped[team_id],key=lambda d:d['number'])
            teams.append({'team_id':team_id,'name':name,'drivers':drivers,
                          'q1':team_metric(drivers),'q1_no_flags':team_metric(drivers,True),
                          'declaration':declaration,'full_specification_per_driver_session':None})
            teams[-1]['secu_software']=software.get((rnd,team_id))
        qurl=event['official_race_url'].rsplit('/',1)[0]+'/qualifying'
        source=capture_by_url[qurl]
        result.append({'season':2026,'round':rnd,'event':context['corrida'],'circuit_id':context['circuito_id'],
                       'date':context['data'],'meeting_key':event['meeting_key'],
                       'qualifying_session_key':event['qualifying']['session_key'],
                       'wet_or_mixed_qualifying':quality[rnd]['wet_or_mixed_session'],
                       'reference':{'number':int(reference['No.']),'name':driver_name(reference),'q1_seconds':legal_q1(reference)} if reference else None,
                       'source':{'qualifying_url':qurl,'race_url':event['official_race_url'],
                                 'qualifying_captured_at_utc':source.get('network_retrieved_at_utc'),
                                 'qualifying_capture_date_utc':source.get('network_capture_date_utc'),
                                 'qualifying_last_verified_at_utc':source.get('last_verified_at_utc'),
                                 'qualifying_sha256':source['sha256']},
                       'teams':teams})
    asset={'schema':'pitwall-car-comparison-v1','season':2026,'through_round':max(x['round'] for x in result),
           'built_at_utc':datetime.now(timezone.utc).isoformat(),'retrospective':True,'forecast_input':False,
           'metric':'Q1 gap to fastest legal Q1 time, same compound and valid observed dry laps; team mean requires both drivers',
           'causal_effect_estimated':False,'race_pace_estimated':False,
           'events':result,'teams':TEAMS,
           'unknowns':['fuel','complete_car_spec_by_driver_session','component_causal_gain','rival_development_effect'],
           'source_inputs':[{'path':str(p.relative_to(source_root)) if p.is_relative_to(source_root) else str(p),
                             'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in
                            [initial/'desempenho_todos_pilotos.json',previous/'voltas_com_filtros.json',Path(declarations_path),
                             source_root/'reports/carros_especificacoes_20261123_v1/software_secu_por_equipe.json']]}
    asset['content_sha256']=digest(asset)
    return asset


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--declarations',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    asset=build(args.source_root.resolve(),args.declarations.resolve(),root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(asset,ensure_ascii=False,indent=2,allow_nan=False))
    print(json.dumps({'events':len(asset['events']),'teams':len(TEAMS),
                      'complete_team_gp_q1':sum(t['q1']['status']=='complete' for e in asset['events'] for t in e['teams']),
                      'driver_event_rows':sum(len(t['drivers']) for e in asset['events'] for t in e['teams']),
                      'component_entries':sum(len(t['declaration']['components']) for e in asset['events'] for t in e['teams']),
                      'content_sha256':asset['content_sha256']}))


if __name__=='__main__':main()
