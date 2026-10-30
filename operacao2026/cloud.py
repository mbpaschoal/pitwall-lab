"""Hosted collection and publication preparation; never trains or emits forecasts.

GitHub Actions supplies persistence, tests and publication. No personal token or
paid API is needed. A missing cache causes a new capture, never backdating.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import tarfile

from operacao2026 import weekend
from operacao2026.fontes import _lock
from pitwall.data.archive_collection import CaptureClient, instant, map_sessions, save_checkpoint
from pitwall.paths import PROJECT_ROOT

WORKFLOW = 'https://github.com/mbpaschoal/pitwall-lab/actions/workflows/coletar-dados.yml'
AUTOMATION = dict(modo='github_actions', intervalo_minutos=30, workflow=WORKFLOW)
STATE = Path('data/operacao_2026/fins_de_semana')
PUBLIC = Path('frontend_assets/operacao_fim_semana.json')


def identity(value):
    return value['temporada'], value['rodada'], value['circuito_id']


def in_window(event, now):
    start = min(instant(s['date_start']) for s in event['sessions'])
    end = max(instant(s['date_end']) for s in event['sessions'])
    return start - timedelta(hours=24) <= now <= end + timedelta(hours=48)


def cooldown(root, now):
    deadlines = []
    for path in (root / STATE).glob('*/estado.json'):
        value = json.loads(path.read_text()).get('retry_after_utc')
        if value and instant(value) > now:
            deadlines.append(value)
    return max(deadlines, default=None)


def discover(root, now, client_factory=CaptureClient):
    """Prefer explicit configurations, otherwise use canonical date/meeting joins."""
    paths = list((root / 'operacao2026/eventos').glob('*.json'))
    paths += list((root / STATE / 'configuracoes').glob('*.json'))
    active = []
    for path in paths:
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or value.get('schema') != 'pitwall-weekend-event-v1':
            continue
        event = weekend.load_event(path)
        if in_window(event, now):
            active.append(path)
    if len(active) > 1:
        raise ValueError('Overlapping event configurations')
    if active:
        return active[0]
    if now.year != 2026:
        return None
    base = root / STATE / 'descoberta'
    base.mkdir(parents=True, exist_ok=True)
    stamp = base / 'ultima_consulta.json'
    if stamp.exists() and instant(json.loads(stamp.read_text())['utc']) + timedelta(hours=12) > now:
        return None
    with _lock(root / 'data/operacao_2026/snapshots'):
        run = base / now.strftime('%Y%m%dT%H%M%S%fZ')
        client = client_factory(run, 8)
        try:
            calendar = client.capture('jolpica', 'calendar', 'calendar.json', 'https://api.jolpi.ca/ergast/f1/2026/?limit=100&offset=0')
            meta = calendar['MRData']
            races = meta['RaceTable']['Races']
            if int(meta['offset']) != 0 or int(meta['total']) != len(races) or meta['RaceTable']['season'] != '2026':
                raise ValueError('Incomplete or foreign calendar')
            candidates = [r for r in races if -2 <= (instant(r['date']+'T00:00:00Z')-now).total_seconds()/86400 <= 4]
            if not candidates:
                save_checkpoint(stamp, {'utc':now.isoformat()})
                return None
            if len(candidates) != 1:
                raise ValueError('Ambiguous weekend in calendar')
            race = candidates[0]
            catalog = client.capture('openf1', 'sessions', 'sessions.json', 'https://api.openf1.org/v1/sessions?year=2026')
            circuit = race['Circuit']
            source_event = dict(temporada=2026, rodada=int(race['round']), circuito_id=circuit['circuitId'], data_corrida=race['date'], localidade=circuit['Location']['locality'])
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', source_event['circuito_id']) or not 1 <= source_event['rodada'] <= 24:
                raise ValueError('Unsafe canonical event identity')
            mapped, failures = map_sessions([source_event], {2026:catalog}, now+timedelta(days=10))
            if failures or not mapped or len({s['meeting_key'] for s in mapped}) != 1:
                raise ValueError('Calendar/OpenF1 identity unresolved')
            meeting = mapped[0]['meeting_key']
            sessions = sorted([s for s in catalog if s['meeting_key']==meeting], key=lambda s:instant(s['date_start']))
            main = next(s for s in sessions if s['session_name']=='Race')
            event = dict(source_event, schema='pitwall-weekend-event-v1', nome=race['raceName'],
                         location=main['location'], country_name=main['country_name'],
                         latitude=float(circuit['Location']['lat']), longitude=float(circuit['Location']['long']),
                         data=main['date_start'][:10], largada_utc=main['date_start'], sessions=sessions,
                         proveniencia=[{k:v for k,v in f.items() if k!='arquivo'} for f in client.manifest['fontes']])
            directory = root / STATE / 'configuracoes'
            directory.mkdir(exist_ok=True)
            path = directory / '{}-2026.json'.format(event['circuito_id'])
            save_checkpoint(path,event)
            weekend.load_event(path)
            save_checkpoint(stamp, {'utc':now.isoformat()})
            return path if in_window(event,now) else None
        finally:
            deadline = weekend.retry_deadline(client.manifest)
            if deadline:
                save_checkpoint(base/'estado.json',{'retry_after_utc':deadline.isoformat()})


def semantic(value):
    """Do not release for a new receipt timestamp or a forecast-only refresh."""
    sessions = []
    for s in value.get('sessoes',[]):
        sessions.append({k:v for k,v in s.items() if k not in ('fontes',)})
    championships = {}
    for key, table in (value.get('campeonatos') or {}).items():
        championships[key] = {k:v for k,v in table.items() if k not in ('obtido_em_utc','url')}
    return dict(evento=identity(value), sessoes=sessions, campeonatos=championships, automacao=value.get('automacao'))


def merge_archive(previous, current):
    records = previous.get('arquivo_eventos',[]) + ([{k:v for k,v in previous.items() if k!='arquivo_eventos'}] if previous else [])
    archive = {}
    for record in records:
        key = identity(record)
        if key == identity(current):
            continue
        if key in archive and archive[key] != record:
            raise ValueError('Conflicting archived event')
        archive[key] = record
    return dict(current, arquivo_eventos=[archive[k] for k in sorted(archive)])


def collect(root=PROJECT_ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    delay = cooldown(root,now)
    if delay:
        return dict(changed=False,reason='provider_cooldown',retry_after_utc=delay)
    path = discover(root,now)
    if not path:
        return dict(changed=False,reason='outside_race_weekend')
    event = weekend.load_event(path)
    old_path = root / PUBLIC
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    marker = root/STATE/'{}-{}'.format(event['circuito_id'],event['temporada'])/'conferencia_final.json'
    race = next(s for s in event['sessions'] if s['session_name']=='Race')
    recheck = now >= instant(race['date_end'])+timedelta(hours=16) and not marker.exists()
    state = weekend.collect(path,root,now,recheck_completed=recheck)
    if recheck and all(s['estado']=='dados_recebidos' for s in state['sessoes']) and all(state.get('campeonatos',{}).get(key,{}).get('disponivel') for key in ('driver_standings','constructor_standings')):
        save_checkpoint(marker,{'utc':now.isoformat()})
    new = dict(weekend.public_status(state),automacao=AUTOMATION)
    existing = next((s for s in [old]+old.get('arquivo_eventos',[]) if s and identity(s)==identity(new)),{})
    if existing and semantic(existing)==semantic(new):
        return dict(changed=False,reason='no_substantive_change')
    save_checkpoint(old_path,merge_archive(old,new))
    return dict(changed=True,reason='new_data',evento=event['nome'],identidade=list(identity(new)),sessoes_completas=sum(s['estado']=='dados_recebidos' for s in state['sessoes']),sessoes=len(state['sessoes']))


def prepare_release(result, root=PROJECT_ROOT, now=None):
    """Version validated data changes. Git push happens only after workflow tests."""
    if result.get('changed') is not True:
        raise ValueError('No data change to release')
    root = Path(root)
    current = (root/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',current):
        raise ValueError('Invalid version')
    major,minor,patch = map(int,current.split('.'))
    version = '{}.{}.{}'.format(major,minor,patch+1)
    date = (now or datetime.now(timezone.utc)).date().isoformat()
    name = result['evento']
    notes = {
        'CHANGELOG.md':'Atualização automática de dados de {} pelo GitHub Actions. Sessões com dados recebidos: {}/{}. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.'.format(name,result['sessoes_completas'],result['sessoes']),
        'CHANGELOG.en.md':'Automatic {} data update through GitHub Actions. Sessions with received data: {}/{}. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.'.format(name,result['sessoes_completas'],result['sessoes']),
    }
    for filename,body in notes.items():
        path = root/filename
        text = path.read_text()
        first = re.search(r'^## \d+\.\d+\.\d+ — ',text,re.M)
        if not first:raise ValueError('Changelog structure missing')
        path.write_text(text[:first.start()]+'## {} — {}\n\n{}\n\n'.format(version,date,body)+text[first.start():])
    (root/'VERSION').write_text(version+'\n')
    path = root/'publicacao/templates/requirements.txt'
    path.write_text(path.read_text().replace('Pitwall Lab '+current+':','Pitwall Lab '+version+':'))
    return version


def archive_captures(root, destination):
    """Durable release asset independent of GitHub's evictable execution cache."""
    root, destination = Path(root), Path(destination)
    files = sorted((root/STATE).rglob('*'))
    if any(p.is_symlink() for p in files):
        raise ValueError('Symlink in capture archive')
    if sum(p.stat().st_size for p in files if p.is_file()) > 128*1024*1024:
        raise ValueError('Capture archive exceeds storage limit')
    with tarfile.open(destination,'w:gz') as archive:
        for path in files:
            if path.is_file():archive.add(path,arcname=path.relative_to(root),recursive=False)
    if destination.stat().st_size > 32*1024*1024:
        raise ValueError('Compressed capture archive exceeds 32 MiB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('collect','prepare-release'))
    parser.add_argument('--result',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='collect':
        result=collect()
        save_checkpoint(args.result,result)
        print(json.dumps(result,ensure_ascii=False))
    else:
        print(prepare_release(json.loads(args.result.read_text())))


if __name__=='__main__':main()
