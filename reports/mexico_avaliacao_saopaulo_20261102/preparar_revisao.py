"""Build a reviewed projection; preserve every native response and forecast."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from operacao2026 import fontes,weekend
from operacao2026.openf1_qualificacao import MAPEAMENTO_2026

report=Path(__file__).parent
acquisition=json.loads((report/'acquisition.json').read_text());base=ROOT/acquisition['destination']
for s in acquisition['sources']:
    assert s['status']==200 and sha256((base/s['arquivo']).read_bytes()).hexdigest()==s['sha256']
by_endpoint={s['endpoint']:s for s in acquisition['sources']}
canonical=json.loads((base/'jolpica-resultados.json').read_text())
fontes.validar_pagina((base/'jolpica-resultados.json').read_bytes(),'resultados',19)
race=canonical['MRData']['RaceTable']['Races'][0]
assert (race['date'],race['Circuit']['circuitId'])==('2026-11-01','rodriguez')
original={int(r['number']):r for r in race['Results']}
f1rows=json.loads((report/'f1-rows.json').read_text())[1:]
assert len(f1rows)==22 and {int(r[1]) for r in f1rows}==set(original)
state=json.loads((ROOT/'data/operacao_2026/fins_de_semana/rodriguez-2026/estado.json').read_text())
native_race=next(s for s in state['sessoes'] if s['nome']=='Race')
profile_source=next(s for s in native_race['fontes'] if s['endpoint']=='drivers')
profiles={p['driver_number']:p for p in json.loads((ROOT/profile_source['arquivo_local']).read_text())}
text=(report/'fia-final-race-extracted.txt').read_text()
assert 'Doc 86 Time 19:50' in text and 'Race Final Classification after 71 Laps' in text
winner=Decimal('8428.772');rows=[];differences=[]
for order,cells in enumerate(f1rows,1):
    position,number,_,_,laps,elapsed,points=cells;number=int(number);source=original[number];profile=profiles[number]
    mapping=MAPEAMENTO_2026.get(number)
    if mapping:
        assert source['Driver']['driverId']==mapping[0]
        assert (profile['first_name'],profile['last_name'],profile['team_name'])==tuple(mapping[2:5])
    else:
        assert number==50 and source['Driver']['driverId']=='ryo_hirakawa'
        assert (source['Driver']['givenName'],source['Driver']['familyName'])==('Ryo','Hirakawa')
        assert profile['full_name']=='Ryo HIRAKAWA' and 'Ryo HIRAKAWA' in text
    assert int(source['laps'])==int(laps)
    classified=position!='NC'
    if classified:
        assert int(position)==order
        gap=Decimal(0) if order==1 else Decimal(elapsed.removeprefix('+').removesuffix('s'))
        duration=winner+gap
        millis=int(duration*1000);hour,remaining=divmod(millis,3600000);minute,remaining=divmod(remaining,60000)
        timing='{}:{:02d}:{:06.3f}'.format(hour,minute,remaining/1000)
        line=next(line for line in text.splitlines() if re.match(r'^\s*{}\s+{}\s'.format(order,number),line))
        assert timing in line and re.search(r'\s{}\s+{}'.format(laps,re.escape(timing)),line)
    else:gap=duration=None
    row=dict(numero=number,piloto_id=source['Driver']['driverId'],full_name=profile['full_name'],team_name=profile['team_name'] or cells[3],
             ordem=order,posicao=order if classified else None,situacao='Finished' if classified else 'NC',voltas=int(laps),
             pontos=int(points),duracao=float(duration) if classified else None,gap=float(gap) if classified else None)
    if int(source['position'])!=order or float(source['points'])!=row['pontos']:
        differences.append(dict(piloto_id=row['piloto_id'],anterior=dict(posicao=int(source['position']),pontos=float(source['points'])),final=dict(posicao=row['posicao'],pontos=row['pontos'])))
    rows.append(row)
review_path=ROOT/'operacao2026/adjudicacoes/2026-19-rodriguez.json'
review=json.loads(review_path.read_text())
assert 'classificacao_final' not in review['sessoes']['11404']
for endpoint,key in [('final_race','race_final'),('race_result','race_f1_final'),('resultados','race_identity')]:
    receipt=by_endpoint[endpoint]
    review['fontes'][key]={k:receipt[k] for k in ('provider','endpoint','url','status','obtido_em_utc','sha256')}
review['id']='mexico-2026-fontes-20261102-v2'
review['sessoes']['11404']['classificacao_final']=dict(documento='FIA Doc 86',fonte='race_final',conferencia=['race_f1_final'],
    identidade_canonica='race_identity',encerramento_observado_utc=native_race['encerramento_observado_utc'],
    regra_nc='ordem mantém a ordenação administrativa dos cinco NC; posicao oficial e tempo final permanecem nulos.',linhas=rows)
review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
(report/'differences.json').write_text(json.dumps(differences,ensure_ascii=False,indent=2)+'\n')
# Explicit next-event configuration; no requests or collection before its window.
asset=json.loads((ROOT/'frontend_assets/race_weekend.json').read_text());snapshot=asset['proveniencia']['snapshot_2026']
index,_=fontes.ler_snapshot(ROOT/'data/operacao_2026/snapshots',snapshot)
cal=next(f for f in index['fontes'] if f['endpoint']=='calendario')
calendar=json.loads((ROOT/'data/operacao_2026/snapshots'/snapshot/cal['arquivo']).read_text())['MRData']['RaceTable']['Races']
event=next(r for r in calendar if r['Circuit']['circuitId']=='interlagos')
sessions=json.loads((base/'openf1-brazil-sessions.json').read_text())
assert len(sessions)==5 and {s['meeting_key'] for s in sessions}=={1299}
expected={'Practice 1':event['FirstPractice'],'Practice 2':event['SecondPractice'],'Practice 3':event['ThirdPractice'],'Qualifying':event['Qualifying'],'Race':dict(date=event['date'],time=event['time'])}
for s in sessions:
    ref=expected[s['session_name']]
    assert datetime.fromisoformat(s['date_start'])==datetime.fromisoformat(ref['date']+'T'+ref['time'].replace('Z','+00:00'))
loc=event['Circuit']['Location'];main=next(s for s in sessions if s['session_name']=='Race')
config=dict(schema='pitwall-weekend-event-v1',temporada=2026,rodada=int(event['round']),circuito_id='interlagos',nome=event['raceName'],location=main['location'],country_name='Brazil',latitude=float(loc['lat']),longitude=float(loc['long']),data=event['date'],largada_utc=event['date']+'T'+event['time'],sessions=sessions,proveniencia=[{k:v for k,v in by_endpoint[endpoint].items() if k not in ('arquivo','arquivo_requisicao')} for endpoint in ('sessions_brazil','sao_paulo_schedule')])
p=ROOT/'operacao2026/eventos/saopaulo2026.json';assert not p.exists();p.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');weekend.load_event(p)
print(json.dumps(dict(final_rows=len(rows),changed_canonical_rows=len(differences),next_event=[config['rodada'],config['circuito_id']],session_keys=[s['session_key'] for s in sessions])))
