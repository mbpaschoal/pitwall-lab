"""Run an explicit, bounded public-source plan serially, retaining every receipt."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pitwall.data.archive_collection import CaptureClient

plan=Path(sys.argv[1])
requests=json.loads(plan.read_text())
if not isinstance(requests,list) or not 1<=len(requests)<=8:
    raise ValueError('Expected 1–8 explicitly reviewed public sources')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
destination=ROOT/'data/operacao_2026/fontes_alternativas'/('lawson-'+plan.stem+'-'+stamp)
destination.mkdir(parents=True,exist_ok=False)
client=CaptureClient(destination,interval=8)
try:
    for item in requests:
        client.capture(item['provider'],item['endpoint'],item['filename'],item['url'],response_format='bytes')
finally:
    (plan.parent/(plan.stem+'-acquisition.json')).write_text(json.dumps({'destination':str(destination.relative_to(ROOT)),'sources':client.manifest['fontes'],'failures':client.manifest['falhas']},ensure_ascii=False,indent=2)+'\n')
    print(destination,flush=True)
