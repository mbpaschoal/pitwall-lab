"""Read the public F1 archive and the documented FastF1 archive mirror."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pitwall.data.archive_collection import CaptureClient

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
destination=ROOT/'data/operacao_2026/fontes_alternativas'/('lawson-timing-index-'+stamp)
destination.mkdir(parents=True,exist_ok=False)
client=CaptureClient(destination,interval=8)
try:
    for provider,filename,url in [
        ('f1-livetiming','f1-index.json','https://livetiming.formula1.com/static/2026/Index.json'),
        ('fastf1-mirror','fastf1-index.json','https://livetiming-mirror.fastf1.dev/static/2026/Index.json'),
    ]:
        data=client.capture(provider,'year_index',filename,url,response_format='bytes')
        if data and client.manifest['fontes'][-1]['status']==200:
            index=json.loads(data)
            print('INDEX KEYS',provider,list(index),flush=True)
            for meeting in index.get('Meetings',[]):
                if 'Mexico' in json.dumps(meeting):print(json.dumps(meeting,ensure_ascii=False),flush=True)
finally:
    (Path(__file__).parent/'timing-index-acquisition.json').write_text(json.dumps({'destination':str(destination.relative_to(ROOT)),'sources':client.manifest['fontes']},ensure_ascii=False,indent=2)+'\n')
    print(destination,flush=True)
