"""Read-only POST used by the public F1 Tempo client; no credentials."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
destination=ROOT/'data/operacao_2026/fontes_alternativas'/('lawson-tempo-'+stamp)
destination.mkdir(parents=True,exist_ok=False)
payload={'year':2026,'past_only':True}
request_bytes=json.dumps(payload).encode()
url='https://www.f1-tempo.com/api/getEvents'
request=Request(url,data=request_bytes,method='POST',headers={'Content-Type':'application/json','User-Agent':'PitwallLab/research (educational; bounded; cached)'})
try:
    with urlopen(request,timeout=60) as response:
        raw=response.read(16*1024**2+1);status=response.status
except HTTPError as error:
    raw=error.read();status=error.code
assert len(raw)<=16*1024**2
(destination/'events.json').write_bytes(raw)
receipt={'provider':'f1-tempo','url':url,'method':'POST','request':payload,'status':status,'obtido_em_utc':datetime.now(timezone.utc).isoformat(),'sha256':sha256(raw).hexdigest(),'bytes':len(raw),'arquivo':'events.json'}
(destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(Path(__file__).parent/'tempo-events-acquisition.json').write_text(json.dumps({'destination':str(destination.relative_to(ROOT)),'sources':[receipt]},indent=2)+'\n')
print(json.dumps(receipt))
if status==200:
    data=json.loads(raw)
    print(str(data)[:3500])
