"""Offline weekend preparation, never a forecast or an emission-ready verdict."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from operacao2026 import cloud, weekend
from pitwall.dashboard.tarot_catalog import load_catalog, artwork_for, read_artwork
from pitwall.paths import PROJECT_ROOT


def qualification_status(event, public, now):
    """Observed Q is a prerequisite; the predictive snapshot still needs review."""
    race_start = cloud.instant(event['largada_utc'])
    if now >= race_start:
        return 'janela_prospectiva_encerrada'
    q = next(s for s in event['sessions'] if s['session_name'] == 'Qualifying')
    records = [r for r in [public] + public.get('arquivo_eventos', [])
               if r and cloud.identity(r) == cloud.identity(event)]
    if len(records) > 1:
        raise ValueError('Ambiguous event in public archive')
    rows = [s for s in records[0].get('sessoes', []) if s.get('session_key') == q['session_key']] if records else []
    if len(rows) > 1:
        raise ValueError('Ambiguous qualifying session')
    if not rows or rows[0].get('estado') != 'dados_recebidos':
        return 'aguardando_classificacao'
    end = rows[0].get('encerramento_observado_utc')
    if not end:
        return 'aguardando_encerramento_observado'
    if not cloud.instant(q['date_start']) < cloud.instant(end) <= now < race_start:
        raise ValueError('Observed qualifying timing is inconsistent')
    # Received descriptive data is not the validated predictive snapshot.
    return 'classificacao_recebida_snapshot_preditivo_pendente'


def inspect(event_path, root=PROJECT_ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Timezone-aware inspection clock required')
    event = weekend.load_event(event_path)
    q = next(s for s in event['sessions'] if s['session_name'] == 'Qualifying')
    if cloud.instant(q['date_end']) >= cloud.instant(event['largada_utc']):
        raise ValueError('Qualifying must precede race start')
    canonical = json.loads((root/'frontend_assets/race_weekend.json').read_text())
    races = [r for r in canonical['dados_2026']['corridas']
             if cloud.identity(r) == cloud.identity(event)]
    if len(races) != 1 or races[0]['data_corrida'] != event['data']:
        raise ValueError('Canonical calendar and weekend identity differ')
    race_programme = [s for s in races[0]['programacao'] if s['sessao'] == 'Corrida']
    if len(race_programme) != 1 or cloud.instant(race_programme[0]['data']+'T'+race_programme[0]['hora']) != cloud.instant(event['largada_utc']):
        raise ValueError('Canonical race start differs')
    catalog = load_catalog(root)
    pairs = sorted({(e['driver_id'],e['team_id']) for e in catalog['team_cards']
                    if event['temporada'] in e['years']})
    cards = []
    for driver, team in pairs:
        row = dict(driver_id=driver,team_id=team)
        poses = []
        for pose in (0,1,2):
            entry = artwork_for(catalog,row,pose,event['temporada'])
            content = read_artwork(root,entry) if entry else None
            if content is None:
                raise ValueError('Missing verified team artwork: {} / {} / {}'.format(driver,team,pose))
            poses.append(dict(pose=pose,sha256=hashlib.sha256(content).hexdigest()))
        if len({p['sha256'] for p in poses}) != 3:
            raise ValueError('Three distinct artwork variants required')
        cards.append(dict(driver=driver,team=team,poses=poses))
    public = json.loads((root/cloud.PUBLIC).read_text())
    return dict(schema='pitwall-weekend-readiness-v1',checked_utc=now.astimezone(timezone.utc).isoformat(),
                identity=list(cloud.identity(event)),meeting_key=q['meeting_key'],qualifying_session=q['session_key'],
                collection_window_start=(min(cloud.instant(s['date_start']) for s in event['sessions'])-timedelta(hours=24)).isoformat(),
                qualification_status=qualification_status(event,public,now),
                forecast_emitted_by_this_check=False,forecast_emission_attempted=False,
                limitation='Preparation only; predictive inputs, actual roster and historical coverage must be validated after Q.',
                verified_team_pairs=len(cards),verified_cards=3*len(cards),cards=cards,
                first_free_access_after_q=(cloud.instant(q['date_end'])+timedelta(minutes=30)).isoformat())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evento',type=Path)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--check-upcoming',action='store_true',help='Offline seven-day circuit-reference gate')
    args=parser.parse_args()
    if args.check_upcoming:
        print(json.dumps(check_upcoming(),ensure_ascii=False));return
    if not args.evento or not args.report:
        parser.error('--evento and --report are required for a preparation receipt')
    result=inspect(args.evento)
    # A new receipt may not overwrite an earlier preparation artifact.
    with args.report.open('x') as output:
        json.dump(result,output,ensure_ascii=False,indent=2);output.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cards'},ensure_ascii=False))


def check_upcoming(root=PROJECT_ROOT,now=None):
    root=Path(root);now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Timezone-aware clock required')
    races=json.loads((root/'frontend_assets/race_weekend.json').read_text())['dados_2026']['corridas']
    reviews=json.loads((root/'operacao2026/driver_circuit_reviews.json').read_text())
    due=[r for r in races if 0 <= (datetime.fromisoformat(r['data_corrida']).date()-now.date()).days <= 7]
    missing=[]
    for race in due:
        key='{}:{}'.format(race['temporada'],race['circuito_id']);review=reviews.get(key,{})
        if (review.get('temporada')!=race['temporada'] or review.get('circuito_id')!=race['circuito_id']
                or review.get('direction') not in ('horario','anti_horario','misto_oito')
                or not review.get('source',{}).get('sha256')):
            missing.append(key)
    if missing:raise RuntimeError('Upcoming circuits need review / Circuitos próximos aguardam revisão: '+', '.join(missing))
    return dict(status='ready',horizon_days=7,verified_events=len(due),new_acquisition=False)


if __name__=='__main__':main()
