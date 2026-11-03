"""Verify the captured alternative and prepare a documentary correction."""
from datetime import datetime, timezone
import argparse
from hashlib import sha256
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]
REPORT=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--captures',type=Path,required=True,help='Preserved capturas-originais.tar.gz from release v0.8.14')
args=parser.parse_args()
acquisition=json.loads((REPORT/'tempo-mexico-acquisition.json').read_text())
directory=ROOT/acquisition['destination']
laps=json.loads((directory/'lawson-laps.json').read_text())
results=json.loads((directory/'results.json').read_text())
assert len(laps)==28 and len(results)==22
assert next(r for r in results if r['Driver']=='LAW')['DriverNumber']=='30'
assert next(r for r in results if r['Driver']=='LAW')['Position']==9
assert [r['LapNumber'] for r in laps]==list(range(1,29))
assert all((r['Year'],r['RoundNumber'],r['Session'],r['Driver'],r['DriverNumber'],r['Team'])==(2026,20,3,'LAW','30','Racing Bulls') for r in laps)
assert all(r['Compound']=='MEDIUM' and r['Stint']==1 for r in laps[1:8])
assert laps[0]['Compound']=='nan' and laps[0]['LapTime'] is None
with tarfile.open(args.captures) as archive:
    member=sorted((m for m in archive.getmembers() if m.name.endswith('/11399/laps.json')),key=lambda m:m.name)[-1]
    raw=archive.extractfile(member).read()
    native={r['lap_number']:r for r in json.loads(raw) if r['driver_number']==30}
assert len(native)==28
assert all(native[r['LapNumber']]['lap_duration']==r['LapTime'] for r in laps if r['LapTime'] is not None)
assert all(native[r['LapNumber']]['lap_duration']==r['LapTime'] for r in laps[1:8])
review_path=ROOT/'operacao2026/adjudicacoes/2026-19-rodriguez.json'
backup=REPORT/'adjudication-before.json'
if not backup.exists():backup.write_bytes(review_path.read_bytes())
review=json.loads(backup.read_text())
for filename,name in [('results.json','gp_tempo_fp3_results'),('lawson-laps.json','gp_tempo_lawson_fp3_laps')]:
    source=next(s for s in acquisition['sources'] if s['arquivo']==filename)
    assert sha256((directory/filename).read_bytes()).hexdigest()==source['sha256']
    review['fontes'][name]={k:source[k] for k in ('provider','endpoint','url','status','obtido_em_utc','sha256')}
catalog=json.loads((REPORT/'tempo-events-acquisition.json').read_text())
source=catalog['sources'][0]
review['fontes']['gp_tempo_catalog']={k:source[k] for k in ('provider','endpoint','url','status','obtido_em_utc','sha256')}
source_event=next(r for r in json.loads((ROOT/catalog['destination']/'events.json').read_text()) if r['Country']=='Mexico')
assert (source_event['RoundNumber'],source_event['EventDate'],source_event['Location'])==(20,'01/11/2026, 00:00:00','Mexico City')
window=dict(inicio_utc='2026-10-31T17:42:06Z',fim_utc='2026-10-31T17:55:03Z',voltas=8,fonte='fp3_on_track')
correction=dict(driver_number=30,full_name='Liam LAWSON',team_name='Racing Bulls',stint_number=1,
    lap_start=1,lap_end=8,compound='MEDIUM',tyre_age_at_start=None,intervalo_sem_boxes=window,
    voltas_verificadas=[dict(lap_number=r['LapNumber'],lap_duration=r['LapTime']) for r in laps[1:8]],
    registro_inicial_sem_tempo=dict(lap_number=1,date_start=None,lap_duration=None),
    identidade_fonte=dict(year=2026,event=20,session=3,driver='LAW',driver_number='30',event_name='Mexico City Grand Prix',event_date='2026-11-01'),
    fontes=['gp_tempo_catalog','gp_tempo_fp3_results','gp_tempo_lawson_fp3_laps','fp3_on_track'],
    metodo='MEDIUM publicado no GP Tempo nas voltas 2–8. FIA confirma o primeiro trecho ininterrupto de oito voltas entre 17:42:06 e 17:55:03 UTC. Composto da volta 1 reconstruído por continuidade desse trecho; tempo e idade inicial permanecem ausentes.')
review['id']='mexico-2026-fia-openf1-gptempo-20261102'
review['sessoes']['11399']['stints_documentados']=[correction]
review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
proof=dict(identity=dict(season=2026,canonical_round=19,circuit='rodriguez',meeting_key=1298,session_key=11399,driver_number=30),
    source_identity=source_event,native_laps_sha256=sha256(raw).hexdigest(),published_non_null_times_matched=25,
    source_missing_times_retained_from_native=[12,20],compound_direct_laps=list(range(2,9)),compound='MEDIUM',
    fia_first_run=window,first_lap='Compound reconstructed by continuity of the FIA uninterrupted first run, supported by GP Tempo laps 2–8. Original timing remains absent.',
    tyre_age_at_start=None,decision='documentary_reconstruction_not_raw_observation',checked_utc=datetime.now(timezone.utc).isoformat())
(REPORT/'evidence-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(proof,ensure_ascii=False))
