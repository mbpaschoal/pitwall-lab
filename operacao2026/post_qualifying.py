"""Prepare and register one prospectively gated v1 emission per admitted event.

The existing scientific producer remains the authority. No training, inferred
finish, corrections to existing emissions or automatic source adjudication.
"""
from datetime import datetime, timedelta, timezone
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from operacao2026 import cloud, fontes, weekend
from pitwall.data.archive_collection import instant, save_checkpoint
from pitwall.paths import PROJECT_ROOT

POLICY = Path('operacao2026/forecast_policy.json')
REGISTRY = Path('operacao2026/eventos/emissoes_registradas.json')


def utc_now():
    return datetime.now(timezone.utc)


def command(root, args):
    return subprocess.check_output([sys.executable, '-B', *args], cwd=root,
                                   text=True, stderr=subprocess.PIPE)


def source_control(root, event_path):
    names = ['operacao2026/post_qualifying.py', str(POLICY), str(event_path.relative_to(root))]
    for review in policy(root).get('roster_reviews', []):
        if review['identity'] == list(cloud.identity(weekend.load_event(event_path))):
            names.append(review['source']['file'])
    subprocess.run(['git', 'ls-files', '--error-unmatch', '--', *names], cwd=root,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', *names], cwd=root, check=True)
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def policy(root):
    value = json.loads((root/POLICY).read_text())
    if (value.get('schema') != 'pitwall-automatic-forecast-policy-v1'
            or not 1 <= value['max_attempts'] <= 4
            or value['retry_hours'] < 2 or value['publication_margin_minutes'] < 60):
        raise ValueError('Invalid automatic forecast policy')
    return value


def publication_guard(root, forecast, now=None):
    """Recheck immediately before Git publication, including conflict recovery."""
    if not forecast or forecast.get('status') != 'prepared':
        return
    root = Path(root)
    declaration = forecast['declaration']
    identity = list(cloud.identity(declaration))
    rule = policy(root)
    if identity not in rule['events'] or identity != forecast['identity']:
        raise ValueError('Forecast event is not admitted for publication')
    if not re.fullmatch(r'auto-[A-Za-z0-9_-]+', declaration['snapshot']):
        raise ValueError('Unexpected automatic snapshot identity')
    if not re.fullmatch(r'reports/operacao_2026/emissoes/auto-prospectivo-[A-Za-z0-9_-]+', declaration['diretorio']):
        raise ValueError('Unexpected automatic emission directory')
    events = []
    for path in (root/'operacao2026/eventos').glob('*.json'):
        if isinstance(value := json.loads(path.read_text()), dict) and value.get('schema') == 'pitwall-weekend-event-v1':
            events.append(weekend.load_event(path))
    matches = [e for e in events if list(cloud.identity(e)) == identity]
    if len(matches) != 1 or instant(matches[0]['largada_utc']) != instant(forecast['race_start_utc']):
        raise ValueError('Forecast publication calendar differs')
    now = now or utc_now()
    margin = timedelta(minutes=rule['publication_margin_minutes'])
    if now >= instant(forecast['race_start_utc']) - margin:
        raise ValueError('Forecast publication window closed; preserve the unpublished emission')


def relative_file(root, name):
    root = root.resolve()
    path = root/name
    if Path(name).is_absolute() or '..' in Path(name).parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe forecast artifact')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Forecast artifact escapes checkout')
    return path


def finish_evidence(root, entry, q, now):
    sources = [s for s in entry['fontes'] if s['endpoint'] == 'race_control' and s['status'] == 200]
    if len(sources) != 1:
        raise ValueError('Observed Q3 finish source absent or ambiguous')
    source = sources[0]
    raw = relative_file(root, source['arquivo_local']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Observed finish source changed')
    records = [r for r in json.loads(raw) if (r.get('session_key'), r.get('meeting_key')) ==
               (q['session_key'], q['meeting_key']) and r.get('message') == 'SESSION FINISHED'
               and r.get('qualifying_phase') == 3]
    if len(records) != 1:
        raise ValueError('Unique observed Q3 finish required')
    end = records[0]['date']
    if not (instant(q['date_start']) < instant(end) <= instant(source['obtido_em_utc']) <= now):
        raise ValueError('Observed qualifying chronology differs')
    if instant(end) != instant(entry['encerramento_observado_utc']):
        raise ValueError('Descriptive finish and raw Q3 finish differ')
    return end, source['url']


def register_and_project(root, prepared, run=command):
    """Stage presentation and undo a new registration if projection fails.

    Failed projection bytes stay with the retained attempt. Recovery can reuse
    the immutable emission instead of treating it as already fully registered.
    """
    declaration = prepared['declaration']
    path = root/REGISTRY
    previous_raw = path.read_bytes() if path.exists() else None
    previous = json.loads(previous_raw) if previous_raw is not None else []
    matches = [d for d in previous if cloud.identity(d) == cloud.identity(declaration)]
    if matches and matches != [declaration]:
        raise ValueError('Another forecast is already registered for this event')
    if not matches:
        # Validate first; a rejected declaration never replaces the registry.
        from registro_emissoes import DECLARACOES, validar_declaracoes
        validar_declaracoes(root, (*DECLARACOES, *previous, declaration))
    base = root/cloud.STATE/'forecasts'/'{}-{}'.format(declaration['temporada'], declaration['circuito_id'])
    base.mkdir(parents=True, exist_ok=True)
    projection = Path(tempfile.mkdtemp(prefix='projection-', dir=base))/'race_weekend.json'
    try:
        if not matches:
            save_checkpoint(path, previous + [declaration])
        run(root, ['preparar_dashboard_race_weekend.py', '--root', str(root),
                   '--snapshot', declaration['snapshot'], '--saida', str(projection)])
        projected = json.loads(projection.read_text())
        if not isinstance(projected, dict):
            raise ValueError('Forecast projection must be a JSON object')
        asset = root/'frontend_assets/race_weekend.json'
        if asset.is_file():
            previous_asset = json.loads(asset.read_text())
            if preserve_newer_standings(previous_asset, projected):
                projection.write_text(
                    json.dumps(projected, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                    encoding='utf-8',
                )
        asset.parent.mkdir(parents=True, exist_ok=True)
        projection.replace(asset)
    except Exception:
        if not matches:
            if previous_raw is None:
                path.unlink(missing_ok=True)
            else:
                temporary = path.with_suffix(path.suffix+'.tmp')
                temporary.write_bytes(previous_raw)
                temporary.replace(path)
        raise


def preserve_newer_standings(previous, projected):
    """Keep the published standings if the forecast runner has an older capture."""
    previous_table = previous.get('dados_2026', {}).get('campeonato_pilotos', {})
    if previous_table.get('disponivel') is not True:
        return False
    new_data = projected['dados_2026']
    new_table = new_data['campeonato_pilotos']
    if (new_table.get('disponivel') is True
            and new_table['rodada_referencia'] >= previous_table['rodada_referencia']):
        return False
    new_data['campeonato_pilotos'] = previous_table
    # The published projection retains hashes even when raw inputs are offline.
    old_sources = previous['proveniencia']['fontes_sha256']
    new_sources = projected['proveniencia']['fontes_sha256']
    projected['proveniencia']['fontes_sha256'] = {**old_sources, **new_sources}
    return True


def retain(root, base, prepared):
    root, base = root.resolve(), base.resolve()
    inventory = {}
    for directory in prepared['directories']:
        for path in sorted(relative_file(root, directory).rglob('*')):
            if path.is_symlink():
                raise ValueError('Symlink in forecast evidence')
            if path.is_file():
                name = str(path.relative_to(root))
                target = base/'files'/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                inventory[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    prepared['files'] = inventory
    save_checkpoint(base/'prepared.json', prepared)


def restore(root, base, prepared):
    root, base = root.resolve(), base.resolve()
    for name, digest in prepared['files'].items():
        path = relative_file(base/'files', name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Retained forecast evidence changed')
        target = relative_file(root, name)
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('Existing immutable forecast evidence differs')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open('xb') as output:
                output.write(raw)


def verify_cards(root, directory, year):
    """Report optional artwork coverage without withholding a valid forecast.

    The scientific population remains mandatory. A missing illustration must
    never borrow another driver's face or prevent publication of probabilities.
    """
    from pitwall.dashboard.tarot_catalog import (load_catalog, artwork_for,
                                               read_artwork, TarotCatalogError)
    with (directory/'probabilidades.csv').open() as source:
        rows = list(csv.DictReader(source))
    if (len(rows) != 22 or len({r['piloto_id'] for r in rows}) != 22
            or any(not r['piloto_id'] or not r['equipe_id_entrada'] for r in rows)):
        raise ValueError('Prospective emission requires the complete 2026 population')
    result = dict(required_for_forecast=False, drivers_checked=len(rows),
                  verified_driver_pairs=0, missing=[])
    try:
        catalog = load_catalog(root)
    except TarotCatalogError:
        catalog = None
        result['catalog_status'] = 'unavailable'
    for row in rows:
        identity = dict(driver_id=row['piloto_id'], team_id=row['equipe_id_entrada'])
        entries = [artwork_for(catalog, identity, pose, year) if catalog else None
                   for pose in (0, 1, 2)]
        variants = [read_artwork(root, e) if e else None for e in entries]
        missing = [pose for pose, content in enumerate(variants) if content is None]
        if not missing and len({hashlib.sha256(v).hexdigest() for v in variants}) != 3:
            missing = [0, 1, 2]
        if missing:
            result['missing'].append(dict(identity, poses=missing))
        else:
            result['verified_driver_pairs'] += 1
    result['status'] = 'partial' if result['missing'] else 'complete'
    return result


def review_forecast_roster(root, config, snapshot, bundle=None):
    """Validate explicit announcements against Q; never manufacture driver IDs.

    Literal name variants are assertions on canonical records, not an ID join.
    The provider's original driverId is retained. A reviewed replacement also
    prevents an old 22-driver population from silently passing the count gate.
    """
    identity = list(cloud.identity(config))
    reviews = [r for r in policy(root).get('roster_reviews', []) if r['identity'] == identity]
    if not reviews:
        return dict(status='no_event_review', identity=identity)
    if len(reviews) != 1:
        raise ValueError('Ambiguous event roster review')
    review = reviews[0]
    source = review['source']
    if hashlib.sha256(relative_file(root, source['file']).read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('Roster announcement source changed')
    if bundle is not None:
        from operacao2026.openf1_qualificacao import carregar, MAPEAMENTO_2026
        expected = next(s for s in config['sessions'] if s['session_name'] == 'Qualifying')
        records = carregar(bundle, sessao_esperada=expected, prefixo='openf1-q',
                           mapeamento=MAPEAMENTO_2026)['registros']
    else:
        _, pages = fontes.ler_snapshot(root/'data/operacao_2026/snapshots', snapshot,
            endpoints={'classificacao'}, rodadas={str(config['rodada'])})
        records = []
        for _, payload in pages.get('classificacao', []):
            for race in payload['MRData']['RaceTable']['Races']:
                received = (race.get('season'), race.get('round'),
                            race.get('Circuit', {}).get('circuitId'), race.get('date'))
                if received != (str(config['temporada']), str(config['rodada']),
                                config['circuito_id'], config['data']):
                    raise ValueError('Roster qualifying belongs to another event')
                records.extend(race.get('QualifyingResults', []))
    ids = [r['Driver']['driverId'] for r in records]
    if len(ids) != 22 or len(set(ids)) != 22 or not all(ids):
        raise ValueError('Roster review requires 22 distinct canonical driver IDs')
    if set(ids).intersection(review['absent_driver_ids']):
        raise ValueError('Qualifying roster still contains the replaced driver')
    admitted = []
    for expected in review['required_entries']:
        matches = [r for r in records
            if [r['Driver'].get('givenName'), r['Driver'].get('familyName')] in expected['literal_names']
            and r['Constructor']['constructorId'] == expected['team_id']]
        if len(matches) != 1:
            raise ValueError('Announced driver/team is absent or ambiguous in qualifying')
        admitted.append(dict(driver_id=matches[0]['Driver']['driverId'],
                             team_id=expected['team_id']))
    return dict(status='verified', identity=identity, source=source,
                admitted_entries=admitted, id_origin='unchanged_qualifying_record')


def prepare(root, event_path, state, now=None, run=command):
    root, event_path = Path(root).resolve(), Path(event_path).resolve()
    now = now or utc_now()
    config = weekend.load_event(event_path)
    rule = policy(root)
    identity = list(cloud.identity(config))
    if identity not in rule['events']:
        return dict(status='event_not_admitted')
    from registro_emissoes import carregar
    if tuple(identity) in carregar(root):
        return dict(status='already_registered')
    if now >= instant(config['largada_utc'])-timedelta(minutes=rule['publication_margin_minutes']):
        return dict(status='publication_window_closed')
    if cloud.identity(state) != cloud.identity(config):
        raise ValueError('Forecast state belongs to another event')
    q = next(s for s in config['sessions'] if s['session_name'] == 'Qualifying')
    entry = next((s for s in state['sessoes'] if s['session_key'] == q['session_key']), {})
    if (entry.get('estado') not in ('dados_recebidos','parcial') or not entry.get('encerramento_observado_utc')
            or now <= instant(q['date_end'])+timedelta(minutes=30)):
        return dict(status='waiting_for_observed_qualifying')
    end, evidence_url = finish_evidence(root, entry, q, now)
    base = root/cloud.STATE/'forecasts'/('{}-{}'.format(config['temporada'], config['circuito_id']))
    base.mkdir(parents=True, exist_ok=True)
    if (base/'prepared.json').exists():
        prepared = json.loads((base/'prepared.json').read_text())
        if prepared['identity'] != identity or prepared['race_start_utc'] != config['largada_utc']:
            raise ValueError('Retained forecast has a different event')
        publication_guard(root, prepared, now)
        restore(root, base, prepared)
        bundle = prepared.get('qualifying_bundle')
        prepared['roster_review'] = review_forecast_roster(root, config,
            prepared['declaration']['snapshot'], root/bundle if bundle else None)
        prepared['artwork_coverage'] = verify_cards(root,
            root/prepared['declaration']['diretorio'], config['temporada'])
        register_and_project(root, prepared, run)
        return prepared
    receipt = base/'attempts.json'
    attempts = json.loads(receipt.read_text()) if receipt.exists() else []
    if attempts and now < instant(attempts[-1]['utc'])+timedelta(hours=rule['retry_hours']):
        return dict(status='blocked_retry_deferred' if attempts[-1].get('status') == 'blocked' else 'retry_deferred', attempts=len(attempts))
    if len(attempts) >= rule['max_attempts']:
        raise RuntimeError('Automatic forecast attempts exhausted; source review required')
    attempt = dict(utc=now.isoformat(), status='started')
    attempts.append(attempt)
    save_checkpoint(receipt, attempts)
    stamp = now.strftime('%Y%m%dT%H%M%S%fZ')
    snapshot = 'auto-{}-{}'.format(config['circuito_id'], stamp)
    emission = 'auto-prospectivo-{}-{}'.format(config['circuito_id'], stamp)
    try:
        source = source_control(root, event_path)
        fontes.coletar_snapshot(root/'data/operacao_2026/snapshots', snapshot_id=snapshot,
                                circuitos=(config['circuito_id'],), agora=now)
        common = ['--snapshot', snapshot, '--temporada', str(config['temporada']),
                  '--rodada', str(config['rodada']), '--circuito', config['circuito_id']]
        readiness = json.loads(run(root, ['operar_2026.py', 'estado', *common]))
        if readiness.get('registros_classificacao') not in (0,22):
            raise ValueError('Canonical qualifying population is incomplete')
        alternative = []
        bundle = None
        directories = ['data/operacao_2026/snapshots/'+snapshot]
        if readiness['estado'] != 'pronto':
            bundle = weekend.qualification_bundle(event_path, state, root)
            if not bundle:
                raise ValueError('Neither canonical nor admitted OpenF1 Q is available')
            alternative = ['--openf1-diretorio', str(bundle), '--openf1-evento', str(event_path)]
            directories.append(str(bundle.relative_to(root)))
        roster = review_forecast_roster(root, config, snapshot, bundle)
        cutoff = utc_now().isoformat()
        run(root, ['operar_2026.py', 'emitir', *common, '--id', emission,
                   '--sessao-encerrada-em', end, '--fonte-encerramento', evidence_url,
                   '--corte', cutoff, *alternative])
        directory = 'reports/operacao_2026/emissoes/'+emission
        prepared = dict(status='prepared', identity=identity, race_start_utc=config['largada_utc'],
                        automation_source=source,
                        roster_review=roster,
                        qualifying_bundle=str(bundle.relative_to(root)) if bundle else None,
                        declaration=dict(temporada=config['temporada'], rodada=config['rodada'],
                            circuito_id=config['circuito_id'], snapshot=snapshot, diretorio=directory, modo='PROSPECTIVO'),
                        directories=directories+[directory])
        # Retain the immutable emission before any later presentation/release failure.
        retain(root, base, prepared)
        prepared['artwork_coverage'] = verify_cards(root, root/directory, config['temporada'])
        save_checkpoint(base/'prepared.json', prepared)
        publication_guard(root, prepared)
        register_and_project(root, prepared, run)
        attempt['status'] = 'prepared'
        save_checkpoint(receipt, attempts)
        return prepared
    except Exception as error:
        attempt.update(status='blocked', error_type=type(error).__name__)
        save_checkpoint(receipt, attempts)
        # Preserve completed snapshots and diagnostics; no endless immediate retry.
        detail = str(error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            detail += '\n' + error.stderr
        (base/(stamp+'-error.txt')).write_text(detail+'\n')
        # Retain partial/final raw material even when the scientific gate rejects
        # the attempt. These directories are never admitted by this receipt.
        for name in ('data/operacao_2026/snapshots/'+snapshot,
                     'reports/operacao_2026/emissoes/'+emission):
            path = root/name
            if path.exists():
                target = base/'failed'/stamp/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(path, target, symlinks=True)
        raise


def check_health(result):
    status = result.get('forecast',{}).get('status')
    if status in ('blocked','blocked_retry_deferred','publication_window_closed'):
        raise RuntimeError('Previsão automática requer revisão / Automatic forecast needs review: '+status)
    return dict(status=status or 'not_in_forecast_window')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('check',))
    parser.add_argument('--result',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(check_health(json.loads(args.result.read_text()))))
