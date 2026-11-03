"""Discover the session via FastF1's schedule, then read its public archive."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pitwall.data.archive_collection import CaptureClient

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
destination=ROOT/'data/operacao_2026/fontes_alternativas'/('lawson-mirror-'+stamp)
destination.mkdir(parents=True,exist_ok=False)
client=CaptureClient(destination,interval=8)
try:
    raw=client.capture('fastf1','schedule','schedule.json','https://raw.githubusercontent.com/theOehrly/f1schedule/master/schedule_2026.json',response_format='bytes')
    schedule=json.loads(raw)
    keys=[k for k,v in schedule['round_number'].items() if v==19 and schedule['country'][k]=='Mexico']
    if len(keys)!=1:raise ValueError('Ambiguous Mexico schedule')
    k=keys[0]
    assert schedule['session3'][k]=='Practice 3'
    path='/static/2026/{}_{}//'.format(schedule['event_date'][k][:10],schedule['event_name'][k]).replace(' ','_')
    path=path[:-1]+'{}_Practice_3/'.format(schedule['session3_date'][k][:10])
    url='https://livetiming-mirror.fastf1.dev'+path
    print('PUBLIC MIRROR SESSION',url,flush=True)
    info=client.capture('fastf1-mirror','session_info','SessionInfo.json',url+'SessionInfo.json',response_format='bytes')
    if client.manifest['fontes'][-1]['status']==200:
        metadata=json.loads(info.decode('utf-8-sig'))
        print('METADATA',json.dumps(metadata),flush=True)
        if metadata.get('Key')!=11399 or metadata.get('Meeting',{}).get('Key')!=1298:
            raise ValueError('Archive identifies another session')
        for endpoint in ['TimingAppData.jsonStream','TyreStintSeries.json','TimingData.jsonStream']:
            client.capture('fastf1-mirror',endpoint,endpoint,url+endpoint,response_format='bytes')
finally:
    (Path(__file__).parent/'mirror-acquisition.json').write_text(json.dumps({'destination':str(destination.relative_to(ROOT)),'sources':client.manifest['fontes']},ensure_ascii=False,indent=2)+'\n')
    print(destination,flush=True)
