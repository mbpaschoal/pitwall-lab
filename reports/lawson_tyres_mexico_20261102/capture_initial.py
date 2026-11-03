"""Bounded serial discovery: public alternatives for Lawson's first FP3 stint."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pitwall.data.archive_collection import CaptureClient

def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = ROOT/'data/operacao_2026/fontes_alternativas'/('lawson-fp3-'+stamp)
    destination.mkdir(parents=True, exist_ok=False)
    client = CaptureClient(destination, interval=8)
    requests = [
        ('openf1', 'lawson_stints', 'openf1-stints.json', 'https://api.openf1.org/v1/stints?session_key=11399&driver_number=30'),
        ('delta-trace', 'strategy', 'delta-strategy.html', 'https://delta-trace.com/2026/mexico-city/fp3/strategy'),
        ('formula1', 'fp3_report', 'formula1-fp3.html', 'https://www.formula1.com/en/latest/article/fp3-norris-pips-antonelli-and-leclerc-to-top-spot-in-final-practice-for-mexico-city-gp.1s5lDqpwmCBl5aqSGq4Ffn'),
    ]
    for provider, endpoint, filename, url in requests:
        client.capture(provider, endpoint, filename, url, response_format='bytes')
        item=client.manifest['fontes'][-1]
        print(json.dumps({k:item.get(k) for k in ('provider','endpoint','status','bytes','sha256')}) ,flush=True)
        if item['status']==429:
            raise SystemExit('Provider cooldown; stop, preserve receipt.')
    report=Path(__file__).parent/'initial-acquisition.json'
    report.write_text(json.dumps({'destination':str(destination.relative_to(ROOT)),'sources':client.manifest['fontes']},ensure_ascii=False,indent=2)+'\n')
    print(str(destination),flush=True)

if __name__=='__main__':
    main()
