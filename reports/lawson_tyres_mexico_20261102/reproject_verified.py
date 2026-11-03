"""Reproject verified cached bytes; never collect or change a recorded forecast."""
from copy import deepcopy
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from operacao2026.weekend import ENDPOINTS, load_event, project_received
from operacao2026.weekend_reconciliation import load_review

REPORT=Path(__file__).parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--captures',type=Path,required=True,help='Preserved capturas-originais.tar.gz from release v0.8.14')
parser.add_argument('--baseline',default='4166cd3c1f6fad47709f224d8226d904fbfe79bc')
parser.add_argument('--all-sessions',action='store_true',help='Normalize all cached sessions with the current projector')
args=parser.parse_args()
path=ROOT/'frontend_assets/operacao_fim_semana.json'
backup=REPORT/'public-before.json'
baseline=subprocess.check_output(['git','show',args.baseline+':frontend_assets/operacao_fim_semana.json'],cwd=ROOT)
if not backup.exists():backup.write_bytes(baseline)
assert backup.read_bytes()==baseline
state=json.loads(backup.read_text())
event=load_event(ROOT/'operacao2026/eventos/mexico2026.json')
review=load_review(ROOT,event)
assert (state['temporada'],state['rodada'],state['circuito_id'])==(2026,19,'rodriguez')
with tarfile.open(args.captures) as archive:
    by_hash={}
    for member in archive.getmembers():
        if member.isfile():
            raw=archive.extractfile(member).read()
            by_hash[sha256(raw).hexdigest()]=raw
    checks=[]
    for entry in state['sessoes']:
        session=next(s for s in event['sessions'] if s['session_key']==entry['session_key'])
        if not args.all_sessions and str(session['session_key']) not in review['sessoes']:continue
        raw={}
        for source in entry['fontes']:
            if source['endpoint'] in ENDPOINTS and source['status']==200:
                data=by_hash[source['sha256']]
                assert sha256(data).hexdigest()==source['sha256']
                raw[source['endpoint']]=json.loads(data)
        previous=deepcopy(entry)
        entry['fim_programado_utc']=session['date_end']
        project_received(entry,raw,session,review)
        timing_values=lambda rows:[{k:v for k,v in row.items() if k!='piloto_id'} for row in rows]
        assert timing_values(entry['tempos'])==timing_values(previous['tempos'])
        assert entry['dados_descritivos']['voltas_por_piloto']==previous['dados_descritivos']['voltas_por_piloto']
        assert entry.get('clima_observado')==previous.get('clima_observado')
        checks.append(dict(session_key=session['session_key'],timings_unchanged=True,laps_unchanged=True,observed_weather_unchanged=True,
            optional_id_keys_restored=sum('piloto_id' not in old and 'piloto_id' in new for old,new in zip(previous['tempos'],entry['tempos'])),
            raw_groups_verified=len(raw),state=entry['estado']))
stamp=max(s['obtido_em_utc'] for s in review['fontes'].values())
state['atualizado_em_utc']=stamp
path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
fp3=next(s for s in state['sessoes'] if s['session_key']==11399)
strategy=next(s for s in fp3['dados_descritivos']['estrategias'] if s['numero']==30)
assert fp3['estado']=='dados_recebidos' and strategy['comparavel'] is True
assert strategy['sequencia_stints'][0]['composto']=='MEDIUM'
assert strategy['sequencia_stints'][0]['idade'] is None
assert all(s['estado']=='dados_recebidos' for s in state['sessoes'])
result=dict(checked_utc=datetime.now(timezone.utc).isoformat(),sessions=checks,complete_sessions=5,total_sessions=5,
            previous_commit=args.baseline,previous_public_asset_sha256=sha256(baseline).hexdigest(),
            fp3_native_coverage=fp3['cobertura'],fp3_reviewed_coverage=fp3['cobertura_validada'],lawson=strategy,
            public_asset_sha256=sha256(path.read_bytes()).hexdigest())
(REPORT/'reprojection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['complete_sessions','total_sessions','public_asset_sha256']}))
