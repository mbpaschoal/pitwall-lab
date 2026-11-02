"""Capture only reviewed Mexico gaps, serially; preserve every raw receipt."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pitwall.data.archive_collection import CaptureClient

SOURCES = [
    ('fia', 'revised_entry', 'fia-entry.pdf', 'https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_revised_entry_list.pdf'),
    ('fia', 'fp3_classification', 'fia-fp3-classification.pdf', 'https://www.fia.com/sites/default/files/2026_19_mex_f1_p3_timing_thirdpracticesessionclassification_v01.pdf'),
    ('fia', 'q_classification', 'fia-q-classification.pdf', 'https://www.fia.com/sites/default/files/2026_19_mex_f1_q0_timing_qualifyingsessionprovisionalclassification_v01.pdf'),
    ('fia', 'fp3_on_track', 'fia-fp3-on-track.pdf', 'https://www.fia.com/sites/default/files/2026_19_mex_f1_p3_timing_thirdpracticesessionontrackanalysis_v01.pdf'),
    ('fia', 'q_on_track', 'fia-q-on-track.pdf', 'https://www.fia.com/sites/default/files/2026_19_mex_f1_q0_timing_qualifyingsessionontrackanalysis_v01.pdf'),
    ('fia', 'race_weather', 'fia-race-weather.pdf', 'https://www.fia.com/sites/default/files/2026_19_mex_f1_r0_timing_raceweatherreport_v01.pdf'),
    ('formula1', 'fp3_results', 'f1-fp3.html', 'https://www.formula1.com/en/results/2026/races/1298/mexico/practice/3'),
    ('formula1', 'q_results', 'f1-q.html', 'https://www.formula1.com/en/results/2026/races/1298/mexico/qualifying'),
    ('f1-livetiming', 'archive_index', 'f1-archive-index.json', 'https://livetiming.formula1.com/static/2026/Index.json'),
    ('fia', 'q_final', 'fia-q-final.pdf', 'https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_qualifying_classification.pdf'),
    ('fia', 'q_lawson_decision', 'fia-q-lawson-dq.pdf', 'https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_infringement_-_car_30_-_technical_nonconformity.pdf'),
    ('formula1dashboard', 'sessions', 'f1dashboard-sessions.json', 'https://api.formula1dashboard.com/api/v1/sessions?year=2026&meeting_key=1298'),
    ('formula1dashboard', 'fp3_laps', 'f1dashboard-fp3-laps.json', 'https://api.formula1dashboard.com/api/v1/laps?year=2026&meeting_key=1298&session_key=11399'),
    ('formula1dashboard', 'q_laps', 'f1dashboard-q-laps.json', 'https://api.formula1dashboard.com/api/v1/laps?year=2026&meeting_key=1298&session_key=11400'),
]

if __name__ == '__main__':
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = ROOT / 'data/operacao_2026/fontes_alternativas' / ('mexico-pendencias-' + stamp)
    destination.mkdir(exist_ok=False)
    print('DESTINATION', destination, flush=True)
    client = CaptureClient(destination, interval=8)
    for provider, endpoint, filename, url in SOURCES:
        client.capture(provider, endpoint, filename, url, response_format='bytes')
        if client.manifest['fontes'][-1]['status'] == 429:
            raise SystemExit('Provider rate limit; raw response preserved. Stop before another request.')
    (Path(__file__).parent / 'acquisition.json').write_text(json.dumps(dict(destination=str(destination.relative_to(ROOT)), sources=len(client.manifest['fontes'])),indent=2)+'\n')
