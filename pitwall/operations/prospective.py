"""Idempotent hosted P1 publication, with immutable scientific companions.

Only admitted events are considered. No collection, training or v1 mutation.
All writes are new public release assets; existing assets are never replaced.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pitwall.paths import PROJECT_ROOT

REPO = 'mbpaschoal/pitwall-lab'
BASE = 'https://api.github.com/repos/' + REPO
FROZEN = Path('reports/prospectivo_p1_20261105')
MANIFEST_SHA = 'a312465eddabf47e15a6e0df114323d60c3aceaa9e49fe0c2342e6dd4bed1a03'
PAIR_NAME = 'paired-probabilities.json'


def now():
    return datetime.now(timezone.utc)


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(timezone.utc)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


class GitHub:
    """One bounded request per operation; only Actions supplies a write token."""
    def request(self, method, url, data=None, *, missing=False, binary=False):
        allowed = (BASE+'/', 'https://uploads.github.com/repos/'+REPO+'/')
        if not url.startswith(allowed):
            raise ValueError('Unexpected GitHub endpoint')
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Pitwall-Lab-P1',
                   'X-GitHub-Api-Version': '2022-11-28'}
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer '+token
        if method != 'GET':
            if not token:
                raise ValueError('Actions token required for publication')
            headers['Content-Type'] = 'application/octet-stream' if binary else 'application/json'
        body = data if binary else json_bytes(data) if data is not None else None
        try:
            with urlopen(Request(url, data=body, headers=headers, method=method), timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if missing and method == 'GET' and error.code == 404:
                return None
            # Never include a request/header/token in diagnostics.
            raise RuntimeError('GitHub API HTTP '+str(error.code)) from None

    def release(self, tag):
        return self.request('GET', BASE+'/releases/tags/'+tag, missing=True)

    def create(self, tag, commit):
        return self.request('POST', BASE+'/releases', {
            'tag_name': tag, 'target_commitish': commit, 'name': 'Pitwall P1 · '+tag[3:],
            'body': 'Protocolo P1 / P1 protocol: 6206fd4c82012e60a0bcad3ebe935efc6406ffeb. '
                    'Probabilidades congeladas e recibos separados / Frozen probabilities and separate receipts. '
                    'Nenhum treino ou promoção automática / No training or automatic promotion.',
            'draft': False, 'prerelease': False, 'make_latest': 'false'})

    def assets(self, release):
        rows = []
        for page in range(1, 11):
            batch = self.request('GET', BASE+'/releases/'+str(release['id'])+'/assets?per_page=100&page='+str(page))
            rows.extend(batch)
            if len(batch) < 100:
                return rows
        raise ValueError('Release asset pagination exceeded its bound')

    def upload(self, release, name, raw):
        url = 'https://uploads.github.com/repos/'+REPO+'/releases/'+str(release['id'])+'/assets?'+urlencode({'name': name})
        return self.request('POST', url, raw, binary=True)

    def download(self, asset):
        url = asset['browser_download_url']
        if not url.startswith('https://github.com/'+REPO+'/releases/download/'):
            raise ValueError('Unexpected public asset URL')
        with urlopen(Request(url, headers={'User-Agent': 'Pitwall-Lab-P1'}), timeout=30) as response:
            raw = response.read(1024*1024+1)
        if len(raw) > 1024*1024 or asset.get('state') != 'uploaded' or asset.get('size') != len(raw) or asset.get('digest') != 'sha256:'+digest(raw):
            raise ValueError('Public asset bytes/metadata differ')
        return raw


def frozen(root):
    folder = root/FROZEN
    if digest((folder/'public-protocol-manifest.json').read_bytes()) != MANIFEST_SHA:
        raise ValueError('Registered P1 manifest changed')
    for name, expected in json.loads((folder/'public-protocol-manifest.json').read_text())['files'].items():
        if digest((folder/name).read_bytes()) != expected:
            raise ValueError('Registered P1 file changed: '+name)
    return runpy.run_path(str(folder/'pair_predictions.py'))


def unique_asset(assets, name):
    matches = [a for a in assets if a['name'] == name]
    if len(matches) > 1 or (matches and matches[0].get('state') != 'uploaded'):
        raise ValueError('Ambiguous or incomplete immutable asset: '+name)
    return matches[0] if matches else None


def bind_pair(root, pair_file, entry, helpers):
    """Recompute frozen Q from native inputs, including recovery after cutoff."""
    pair = json.loads(pair_file.read_text())
    originals = {'modelo':'models/modelo_v1/modelo.joblib',
                 'metadados':'models/modelo_v1/metadados.json','esquema':'data/preparado/colunas.json'}
    if any(digest((root/name).read_bytes()) != helpers['V1_HASHES'][key] for key,name in originals.items()):
        raise ValueError('Original v1 artifacts changed')
    directory = root/entry['diretorio']
    manifest = json.loads((directory/'manifesto.json').read_text())
    for name, expected in manifest['hashes_saidas'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or digest((directory/name).read_bytes()) != expected:
            raise ValueError('Native emission evidence changed')
    with (directory/'probabilidades.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    expected = helpers['assemble_pairs'](json.loads((directory/'entradas.json').read_text()), rows,
                                         manifest['evento'], helpers['frozen_q']())
    for field, name in [('v1_manifest_sha256','manifesto.json'), ('v1_inputs_sha256','entradas.json'),
                        ('v1_probabilities_sha256','probabilidades.csv')]:
        if pair.get(field) != digest((directory/name).read_bytes()):
            raise ValueError('Pair/native evidence binding differs')
    if (pair.get('source_emission_id') != Path(entry['diretorio']).name or pair.get('pairs') != expected
            or pair.get('event') != manifest['evento'] or pair.get('cutoff_utc') != manifest['corte_utc']
            or utc(pair['public_receipt_required_before_utc']) != utc(manifest['corte_temporal']['corrida_programada_em_utc'])-timedelta(minutes=60)):
        raise ValueError('Public pair differs from the native registered emission')
    return pair


def persist_asset(api, release, assets, name, raw):
    previous = unique_asset(assets, name)
    if previous:
        if api.download(previous) != raw:
            raise ValueError('Refusing to replace immutable public asset: '+name)
        return previous
    result = api.upload(release, name, raw)
    if result.get('digest') != 'sha256:'+digest(raw) or result.get('size') != len(raw) or result.get('state') != 'uploaded':
        raise ValueError('Upload did not preserve the prepared bytes')
    assets.append(result)
    return result


def host_spec(root, pair):
    """Bind displayed native forecasts to all paired rows, without editing UI."""
    from pitwall.data.race_weekend import carregar_asset, nome_exibicao_piloto
    asset = carregar_asset(root)
    event = pair['event']
    event_identity=(int(event['temporada']),int(event['rodada']),event['circuito_id'])
    races = [r for r in asset['dados_2026']['corridas'] if
             (r['temporada'],r['rodada'],r['circuito_id']) == event_identity]
    if len(races) != 1 or races[0].get('emissao_sha256') != pair['v1_manifest_sha256'] or races[0]['estado_previsao'] != 'previsao_registrada':
        raise ValueError('Projected forecast is not the paired native emission')
    rows = [r for r in asset['dados_2026']['previsoes'] if (r['temporada'],r['rodada']) == event_identity[:2]]
    indexed = {r['piloto_id']:r for r in rows}
    if len(rows) != len(pair['pairs']) or set(indexed) != {r['piloto_id'] for r in pair['pairs']}:
        raise ValueError('Projected forecast roster differs')
    expected = []
    for p in pair['pairs']:
        r = indexed[p['piloto_id']]
        if r['probabilidade_modelo'] != p['probabilidade_v1'] or r['equipe_id'] != p['equipe_id_entrada']:
            raise ValueError('Projected probabilities or teams differ')
        expected.append(dict(id=p['piloto_id'],name=nome_exibicao_piloto(p['piloto_id'],r['piloto']),probability=p['probabilidade_v1']))
    return dict(identity=list(event_identity),
                rows=expected,favorites=[r['piloto_id'] for r in sorted(rows,key=lambda r:r['ranking_modelo'])[:3]],
                source_asset_sha256=digest((root/'frontend_assets/race_weekend.json').read_bytes()))


def validate_host(receipt, pair_sha, identity, start):
    cases = receipt.get('cases',[])
    expected = {(e,w,l) for e in ('chromium','webkit') for w in (390,1440) for l in ('pt','en')}
    if (receipt.get('schema')!='pitwall-p1-served-forecast-v1' or receipt.get('base')!='https://pitwall-lab.streamlit.app'
            or receipt.get('status') != 'passed' or receipt.get('pair_sha256') != pair_sha
            or receipt.get('identity') != identity or len(cases) != 8
            or {(c['engine'],c['width'],c['lang']) for c in cases} != expected
            or any(c.get('status') != 'passed' or c.get('rows_checked') != 22
                   or not utc(c['observed_at_utc']) <= now() < start for c in cases)
            or not utc(receipt['completed_at_utc']) <= now() < start):
        raise ValueError('Public forecast host acceptance is incomplete or late')


def prior_host(receipt, pair_sha, identity, start):
    """The later audit uses saved observation times, without pretending it ran now."""
    cases=receipt.get('cases',[])
    expected={(e,w,l) for e in ('chromium','webkit') for w in (390,1440) for l in ('pt','en')}
    if (receipt.get('schema')!='pitwall-p1-served-forecast-v1' or receipt.get('base')!='https://pitwall-lab.streamlit.app'
            or receipt.get('status')!='passed' or receipt.get('pair_sha256')!=pair_sha or receipt.get('identity')!=identity
            or len(cases)!=8 or {(c['engine'],c['width'],c['lang']) for c in cases}!=expected
            or any(c.get('status')!='passed' or c.get('rows_checked')!=22
                   or not utc(c['observed_at_utc']) <= utc(receipt['completed_at_utc']) < start for c in cases)
            or utc(receipt['completed_at_utc']) > now()):
        raise ValueError('Stored public host acceptance is invalid')


def score_rows(pairs, targets):
    """Pure descriptive GP scores; unknown targets remain outside denominators."""
    known=[(p,targets[p['piloto_id']]) for p in pairs if targets.get(p['piloto_id']) in (0,1)]
    scores={}
    for model in ('v1','q'):
        values=[(p['probabilidade_'+model],y) for p,y in known]
        if not values:
            scores[model]=dict(brier=None,log_loss=None)
            continue
        clipped=[(min(1-1e-15,max(1e-15,p)),y) for p,y in values]
        scores[model]=dict(brier=sum((p-y)**2 for p,y in values)/len(values),
                          log_loss=-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in clipped)/len(values))
    return dict(known_targets=len(known),unknown_targets=len(pairs)-len(known),scores=scores,
                model_selection_performed=False,formal_20_GP_conclusion='not evaluated by a single-GP receipt')


def post_race(root,pair,pair_sha,output,api,release,assets,event):
    if now() <= utc(event['largada_utc']):
        return dict(status='waiting_for_race')
    from pitwall.data.race_weekend import carregar_asset,alvo_podio_posterior
    asset=carregar_asset(root);identity=[event[k] for k in ('temporada','rodada','circuito_id')]
    race=next(r for r in asset['dados_2026']['corridas'] if [r[k] for k in ('temporada','rodada','circuito_id')]==identity)
    if race.get('resultado_posterior_validado') is not True or race.get('estado_resultado')!='observado_local':
        return dict(status='waiting_for_validated_targets')
    if (race.get('resultado_circuito_id')!=event['circuito_id'] or race.get('resultado_data_fonte')!=event['data']
            or not utc(event['largada_utc']) < utc(race['resultado_obtido_em_utc']) <= now()
            or not re.fullmatch('[a-f0-9]{64}',race.get('fonte_resultado_sha256',''))):
        raise ValueError('Posterior result identity/source/clock differs')
    host_spec(root,pair)  # Exact original probabilities and population must still match.
    rows=[r for r in asset['dados_2026']['previsoes'] if [r['temporada'],r['rodada']]==identity[:2]]
    targets={r['piloto_id']:alvo_podio_posterior(r,True) for r in rows}
    observed={'identity':identity,'targets':targets,'source_sha256':race['fonte_resultado_sha256'],
              'obtained_at_utc':race['resultado_obtido_em_utc']}
    evidence=json_bytes(observed)
    record=dict(schema='pitwall-p1-post-race-descriptive-v1',pair_sha256=pair_sha,
                posterior=observed,**score_rows(pair['pairs'],targets))
    name='post-race-'+digest(evidence)+'.json'
    raw=json_bytes(record)
    (output/name).write_bytes(raw)
    persist_asset(api,release,assets,name,raw)
    return dict(status='descriptive_scores_recorded',asset=name,known_targets=record['known_targets'])


def finish_host(root, spec_file, receipt_file, api=None):
    api=api or GitHub();spec=json.loads(Path(spec_file).read_text());receipt=json.loads(Path(receipt_file).read_text())
    root=Path(root)
    from operacao2026.post_qualifying import policy
    from registro_emissoes import carregar
    if spec['identity'] not in policy(root)['events']:
        raise ValueError('Host event is not admitted')
    events=[json.loads(p.read_text()) for p in (root/'operacao2026/eventos').glob('*.json')]
    events=[e for e in events if isinstance(e,dict) and e.get('schema')=='pitwall-weekend-event-v1'
            and [e[k] for k in ('temporada','rodada','circuito_id')]==spec['identity']]
    if len(events)!=1 or events[0]['largada_utc']!=spec['race_start_utc']:
        raise ValueError('Host calendar differs from admitted configuration')
    start=utc(events[0]['largada_utc'])
    validate_host(receipt,spec['pair_sha256'],spec['identity'],start)
    tag='p1-'+'-'.join(map(str,spec['identity']));release=api.release(tag)
    if not release or release['id']!=spec['release_id'] or release.get('draft') is not False:
        raise ValueError('Public P1 release differs')
    assets=api.assets(release);pair=unique_asset(assets,PAIR_NAME)
    if not pair or pair['id']!=spec['pair_asset_id']:
        raise ValueError('Public pair changed during browser acceptance')
    raw=api.download(pair)
    if digest(raw)!=spec['pair_sha256']:
        raise ValueError('Public pair changed during browser acceptance')
    local=Path(spec_file).parent/PAIR_NAME
    if local.read_bytes()!=raw:
        raise ValueError('Local and public pair differ')
    bound=bind_pair(root,local,carregar(root)[tuple(spec['identity'])],frozen(root))
    expected=host_spec(root,bound)
    if any(spec[k]!=expected[k] for k in expected):
        raise ValueError('Host expectations differ from native projected probabilities')
    if receipt.get('source_asset_sha256')!=spec['source_asset_sha256'] or receipt.get('version')!=spec['version']:
        raise ValueError('Host evidence comes from another package')
    saved=persist_asset(api,release,assets,'host-acceptance.json',Path(receipt_file).read_bytes())
    if not utc(saved['created_at']) <= utc(saved['updated_at']) < start:
        raise ValueError('Host evidence was not publicly preserved before the race')
    result=dict(status='pair_and_host_verified',admissible=True,pair_sha256=spec['pair_sha256'])
    (Path(spec_file).parent/'finish-host-result.json').write_bytes(json_bytes(result))
    return result


def run_event(root, event, entry, output, api=None):
    api = api or GitHub()
    clock = now(); start = utc(event['largada_utc']); deadline = start-timedelta(minutes=60)
    identity = [event[k] for k in ('temporada','rodada','circuito_id')]
    tag = 'p1-'+'-'.join(map(str,identity))
    release = api.release(tag)
    assets = api.assets(release) if release else []
    previous = unique_asset(assets, PAIR_NAME)
    if previous is None and clock >= deadline:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        release=release or api.create(tag,commit)
        persist_asset(api,release,assets,'coverage-missing-pair.json',json_bytes(dict(
            identity=identity,status='missing_pair_deadline_closed',admissible=False,
            deadline_exclusive_utc=deadline.isoformat(),forecast_backfilled=False)))
        return dict(status='missing_pair_deadline_closed',identity=identity,admissible=False)
    if entry is None:
        if previous:
            raise ValueError('Public pair has no matching native registered emission')
        return dict(status='waiting_for_native_forecast',identity=identity,admissible=False)
    if entry['modo'] != 'PROSPECTIVO':
        raise ValueError('Retrospective rehearsal cannot enter P1')
    helpers = frozen(root)
    pair_file = output/PAIR_NAME
    if previous:
        pair_file.write_bytes(api.download(previous))
    else:
        attempts = [a for a in assets if re.fullmatch(r'attempt-[1-4]\.json',a['name'])]
        if len(attempts) >= 4:
            raise RuntimeError('P1 attempts exhausted; review required')
        if attempts and clock < max(utc(a['created_at']) for a in attempts)+timedelta(hours=2):
            return dict(status='retry_deferred',identity=identity,admissible=False)
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        release = release or api.create(tag,commit)
        if release.get('draft') is not False or utc(release['published_at']) >= deadline:
            raise ValueError('Release is not publicly available before deadline')
        marker = dict(identity=identity,attempt=len(attempts)+1,started_at_utc=clock.isoformat())
        persist_asset(api,release,assets,'attempt-'+str(len(attempts)+1)+'.json',json_bytes(marker))
        destination = output/'prepared'
        helpers['prepare'](root,Path(entry['diretorio']).name,destination)
        pair_file.write_bytes((destination/PAIR_NAME).read_bytes())
        pair=bind_pair(root,pair_file,entry,helpers)
        if utc(pair['public_receipt_required_before_utc'])!=deadline:
            raise ValueError('Race schedule changed; explicit source review required')
        if now() >= deadline:
            raise ValueError('Publication margin closed before upload')
        previous = persist_asset(api,release,assets,PAIR_NAME,pair_file.read_bytes())
    pair = bind_pair(root,pair_file,entry,helpers)
    if utc(pair['public_receipt_required_before_utc'])!=deadline:
        raise ValueError('Race schedule changed; explicit source review required')
    if release.get('draft') is not False or not utc(release['published_at']) <= utc(previous['created_at']) < deadline:
        raise ValueError('Release publication does not prove public pre-deadline bytes')
    # The original keyless verifier performs its own real metadata GET.
    receipt_file = output/'public-receipt.json'
    subprocess.run([sys.executable,'-B',str(root/FROZEN/'verify_published_pair.py'),
                    '--pair-file',str(pair_file),'--asset-id',str(previous['id']),
                    '--destination',str(receipt_file)],cwd=root,check=True,capture_output=True,text=True)
    receipt = json.loads(receipt_file.read_text())['receipt']
    # Receipts are append-only per verification; the original pair never changes.
    receipt_name = 'receipt-'+digest(pair_file.read_bytes())[:16]+'.json'
    if not unique_asset(assets,receipt_name):
        persist_asset(api,release,assets,receipt_name,receipt_file.read_bytes())
    accepted=unique_asset(assets,'host-acceptance.json')
    if accepted:
        host=json.loads(api.download(accepted))
        prior_host(host,receipt['pair_sha256'],identity,start)
        if not utc(accepted['created_at']) <= utc(accepted['updated_at']) < start:
            raise ValueError('Host evidence was published too late')
        posterior=post_race(root,pair,receipt['pair_sha256'],output,api,release,assets,event)
        return dict(status='pair_and_host_verified',identity=identity,admissible=True,
                    pair_sha256=receipt['pair_sha256'],posterior=posterior)
    if now() >= start:
        persist_asset(api,release,assets,'coverage-missing-host.json',json_bytes(dict(
            identity=identity,status='missing_host_before_race',admissible=False,
            pair_sha256=receipt['pair_sha256'],race_start_utc=start.isoformat())))
        return dict(status='missing_host_before_race',identity=identity,admissible=False)
    attempts=[a for a in assets if re.fullmatch(r'host-attempt-[1-4]\.json',a['name'])]
    if len(attempts)>=4:
        raise RuntimeError('P1 host attempts exhausted; review required')
    if attempts and now()<max(utc(a['created_at']) for a in attempts)+timedelta(hours=2):
        return dict(status='host_retry_deferred',identity=identity,admissible=False)
    persist_asset(api,release,assets,'host-attempt-'+str(len(attempts)+1)+'.json',
                  json_bytes(dict(started_at_utc=now().isoformat(),pair_sha256=receipt['pair_sha256'])))
    spec = host_spec(root,pair)
    spec.update(pair_sha256=digest(pair_file.read_bytes()),race_start_utc=event['largada_utc'],
                version=(root/'VERSION').read_text().strip(),pair_asset_id=previous['id'],release_id=release['id'])
    (output/'host-input.json').write_bytes(json_bytes(spec))
    return dict(status='public_pair_verified',identity=identity,publication_verified=True,
                host_acceptance_pending=True,admissible=False,release_tag=tag,pair_sha256=receipt['pair_sha256'])


def run(root, output):
    from operacao2026.post_qualifying import policy
    from registro_emissoes import carregar
    root, output = Path(root).resolve(), Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    registry = carregar(root)
    results = []
    admitted = policy(root)['events']
    for path in sorted((root/'operacao2026/eventos').glob('*.json')):
        event = json.loads(path.read_text())
        if not isinstance(event,dict) or event.get('schema') != 'pitwall-weekend-event-v1':
            continue
        identity = [event[k] for k in ('temporada','rodada','circuito_id')]
        if identity not in admitted:
            continue
        q = next(s for s in event['sessions'] if s['session_name']=='Qualifying')
        folder=output/('-'.join(map(str,identity)));folder.mkdir()
        if now() <= utc(q['date_start']):
            result=dict(status='waiting_for_observed_qualifying',identity=identity,admissible=False)
        else:
            try:
                result=run_event(root,event,registry.get(tuple(identity)),folder)
            except Exception as error:
                result=dict(status='blocked',identity=identity,admissible=False,
                            error_type=type(error).__name__,error=str(error))
        (folder/'status.json').write_bytes(json_bytes(result));results.append(result)
    (output/'status.json').write_bytes(json_bytes({'events':results,'checked_at_utc':now().isoformat()}))
    if any(r['status'] in ('blocked','missing_pair_deadline_closed','missing_host_before_race','retry_deferred','host_retry_deferred') for r in results):
        raise RuntimeError('P1 needs attention; coverage/retry state retained without backfilling')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=PROJECT_ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--finish-host',type=Path)
    parser.add_argument('--host-receipt',type=Path)
    args=parser.parse_args()
    if args.finish_host:
        print(json.dumps(finish_host(args.root,args.finish_host,args.host_receipt)))
    else:
        print(json.dumps(run(args.root,args.output)))


if __name__=='__main__':
    main()
