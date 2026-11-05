"""Read-only, keyless n8n supervisor. Never runs collection or prediction."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pitwall.operations import prospective as p1
from pitwall.paths import PROJECT_ROOT

IDENTITY = [2026, 20, 'interlagos']
TAG = 'p1-2026-20-interlagos'
RAW = 'https://raw.githubusercontent.com/' + p1.REPO + '/main/'
DEFAULT_STATE = Path.home()/'Library/Application Support/Pitwall Lab/n8n/supervisor'
DEFAULT_ARCHIVE = Path('/Users/MBPaschoal/Dropbox/Projetos pessoais/F1/reports/supervisao_n8n')
MAX_BYTES = 4 * 1024 * 1024
OFFICIAL = [
    'https://www.formula1.com/en/racing/2026/brazil',
    'https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_race_classification.pdf',
]


def utc_now():
    return datetime.now(timezone.utc)


def raw_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)


def immutable(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as output:
            output.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError('Immutable archive collision')
    if sha(path.read_bytes()) != sha(raw):
        raise ValueError('Archive verification failed')


def allowed(url):
    parsed = urlparse(url)
    return (parsed.scheme == 'https' and not parsed.username and not parsed.password
            and (url.startswith(p1.BASE+'/') or url.startswith(RAW)
                 or url.startswith('https://github.com/'+p1.REPO+'/releases/download/'+TAG+'/')
                 or url in OFFICIAL))


def get(url, missing=False):
    if not allowed(url):
        raise ValueError('URL outside the read-only allowlist')
    request = Request(url, headers={'User-Agent': 'Pitwall-Lab-keyless-supervisor',
                                   'Accept': 'application/vnd.github+json' if url.startswith(p1.BASE) else '*/*'})
    try:
        with urlopen(request, timeout=30) as response:
            if urlparse(response.url).hostname not in {
                'api.github.com', 'raw.githubusercontent.com', 'github.com',
                'release-assets.githubusercontent.com', 'objects.githubusercontent.com',
                'www.formula1.com', 'www.fia.com', 'fia.com',
            }:
                raise ValueError('Unexpected response origin')
            raw = response.read(MAX_BYTES+1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Response exceeds the supervisor limit')
            return raw
    except HTTPError as error:
        if missing and error.code == 404:
            return None
        raise RuntimeError('Public source HTTP '+str(error.code)) from None


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden = 0; self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1
        if not self.hidden and tag == 'a':
            self.parts.extend(v for k, v in attrs if k == 'href' and v and '/system/files/' in v)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.hidden = max(0, self.hidden-1)

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def semantic(raw):
    if raw.startswith(b'%PDF'):
        return sha(raw)
    page = PageText(); page.feed(raw.decode('utf-8', errors='replace'))
    return sha(' '.join(' '.join(page.parts).split()).encode())


def pair_checks(root, path, asset, event):
    p1.frozen(root)  # Hash-check the unchanged registered validators first.
    folder = root/p1.FROZEN
    sys.path.insert(0, str(folder))
    try:
        validate = runpy.run_path(str(folder/'verify_published_pair.py'))['validate']
        receipt = validate(path, asset)
    finally:
        sys.path.pop(0)
    pair = json.loads(path.read_bytes())
    if ([int(pair['event']['temporada']),int(pair['event']['rodada']),pair['event']['circuito_id']] != IDENTITY
            or p1.utc(pair['public_receipt_required_before_utc']) != p1.utc(event['largada_utc'])-timedelta(hours=1)):
        raise ValueError('Pair event/calendar differs from admitted operation')
    return pair, receipt


def posterior_checks(record, pair, pair_sha, event, asset):
    if (record.get('schema') != 'pitwall-p1-post-race-descriptive-v1'
            or record.get('pair_sha256') != pair_sha
            or record['posterior'].get('identity') != IDENTITY):
        raise ValueError('Posterior receipt identity differs')
    posterior = record['posterior']; finish = p1.utc(posterior['observed_race_finish_utc'])
    if not p1.utc(event['largada_utc']) < finish <= p1.utc(asset['created_at']) <= utc_now():
        raise ValueError('Posterior chronology differs')
    drivers = {row['piloto_id'] for row in pair['pairs']}
    if set(posterior['targets']) != drivers or any(v not in (None, 0, 1) or isinstance(v, bool) for v in posterior['targets'].values()):
        raise ValueError('Posterior population or targets differ')
    if not posterior.get('sources') or any(not re.fullmatch('[0-9a-f]{64}', s.get('sha256',''))
            or not finish <= p1.utc(s['obtido_em_utc']) <= p1.utc(asset['created_at']) for s in posterior['sources']):
        raise ValueError('Posterior source chronology differs')
    expected = p1.score_rows(pair['pairs'], posterior['targets'])
    for key in ('known_targets', 'unknown_targets', 'model_selection_performed', 'formal_20_GP_conclusion'):
        if record.get(key) != expected[key]:
            raise ValueError('Posterior coverage/conclusion differs')
    for model in ('v1','q'):
        for metric in ('brier','log_loss'):
            actual, wanted = record['scores'][model][metric], expected['scores'][model][metric]
            if actual is None and wanted is None:
                continue
            if not isinstance(actual, (float,int)) or not math.isfinite(actual) or wanted is None or abs(actual-wanted)>1e-12:
                raise ValueError('Posterior score differs from fixed probabilities')
    return record


def summary(snapshot, language):
    english = language == 'en'
    lines = ['# Pitwall Lab — '+('operational supervision' if english else 'supervisão operacional'), '',
             'Created by: MBPaschoal', 'Status: generated; descriptive only', 'Type: operational report', '',
             ('Checked UTC: ' if english else 'Conferido UTC: ')+snapshot['checked_at_utc'],
             ('Event: ' if english else 'Evento: ')+'/'.join(map(str, IDENTITY)),
             'P1: '+snapshot['p1']['status'], '',
             ('Workflow success does not prove forecast publication or host acceptance.' if english else
              'Sucesso do workflow não comprova publicação da previsão nem aceite do host.'), '']
    for row in snapshot.get('post_race', []):
        lines += ['## '+row['asset'], '',
                  ('Known/unknown targets: ' if english else 'Alvos conhecidos/desconhecidos: ')+
                  str(row['known_targets'])+'/'+str(row['unknown_targets']),
                  'v1: '+json.dumps(row['scores']['v1']), 'Q: '+json.dumps(row['scores']['q']),
                  ('Single-GP description; no model selection or promotion.' if english else
                   'Descrição de um GP; sem seleção ou promoção de modelo.'), '']
    lines += ['## '+('Review queue' if english else 'Fila de revisão'), '']
    for item in snapshot['queue']:
        lines += ['- '+item['kind']+': '+item['detail']+' ['+item['status']+']']
    return '\n'.join(lines)+'\n'


class Supervisor:
    def __init__(self, root=PROJECT_ROOT, state=DEFAULT_STATE, archive=DEFAULT_ARCHIVE, fetch=get):
        self.root, self.state, self.archive = Path(root), Path(state), Path(archive)
        self.fetch = fetch

    def blob(self, raw):
        path = self.archive/'objects'/sha(raw)
        immutable(path, raw)
        return path

    def capture(self, url, sources, missing=False):
        raw = self.fetch(url, missing=missing)
        sources.append(dict(url=url, obtained_at_utc=utc_now().isoformat(),
                            status=404 if raw is None else 200,
                            sha256=None if raw is None else sha(raw), size=0 if raw is None else len(raw)))
        if raw is not None:
            self.blob(raw)
        return raw

    def asset(self, asset, sources):
        expected = asset.get('digest', '').removeprefix('sha256:')
        if not re.fullmatch('[0-9a-f]{64}', expected) or asset.get('state') != 'uploaded' or not 0 < asset['size'] <= MAX_BYTES:
            raise ValueError('Incomplete asset metadata')
        cached = self.archive/'objects'/expected
        raw = cached.read_bytes() if cached.exists() else self.capture(asset['browser_download_url'], sources)
        if sha(raw) != expected or len(raw) != asset['size']:
            raise ValueError('Public asset digest/size differs')
        self.blob(raw)
        return raw

    def run(self, force=False, notify=False):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.state/'run.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            previous = json.loads((self.state/'latest.json').read_text()) if (self.state/'latest.json').exists() else {}
            if not force and previous and utc_now()-p1.utc(previous['checked_at_utc']) < timedelta(minutes=20):
                return dict(status='cooldown', changed=False, events=[])
            snapshot = self.observe(previous)
            old = previous.get('signals', {})
            changes = [dict(key=k, previous=old.get(k), current=v) for k,v in snapshot['signals'].items() if old.get(k)!=v]
            changes += [dict(key=k,previous=v,current='resolved') for k,v in old.items()
                        if k.startswith('problem:') and k not in snapshot['signals']]
            actionable = [c for c in changes if c['key'].startswith('problem:') or c['key']=='post_race' and snapshot['post_race']
                          or c['key']=='p1' and c['current'] not in ('pre_q_no_public_pair','awaiting_public_pair')
                          or c['key'].startswith('workflow:') and (c['current']=='failure' or c['previous']=='failure')]
            snapshot['events'] = actionable
            snapshot['changed'] = bool(actionable)
            raw = raw_json(snapshot); content = sha(raw)
            immutable(self.archive/'runs'/(content+'.json'), raw)
            for language in ('pt','en'):
                report = summary(snapshot, language).encode()
                immutable(self.archive/'summaries'/content/(language+'.md'), report)
            # Commit all immutable evidence before the mutable local cursor.
            atomic(self.state/'latest.json', raw)
            atomic(self.archive/'latest.json', raw)
            atomic(self.archive/'queue.json', raw_json(snapshot['queue']))
            for language in ('pt','en'):
                atomic(self.archive/('latest.'+language+'.md'), summary(snapshot, language).encode())
            if notify and actionable and sys.platform == 'darwin':
                # Fixed text only: no scraped text, paths or URLs in AppleScript.
                subprocess.run(['/usr/bin/osascript', '-e', 'display notification "Há uma mudança operacional para revisar. Consulte reports/supervisao_n8n/latest.pt.md." with title "Pitwall Lab"'], timeout=10, check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return snapshot

    def observe(self, previous):
        snapshot = dict(schema='pitwall-readonly-supervision-v1', checked_at_utc=utc_now().isoformat(),
                        identity=IDENTITY, signals={}, workflows={}, sources=[], documents=previous.get('documents',{}).copy(),
                        p1={'status':'indeterminate'}, post_race=[], queue=[], scientific_execution=False)
        sources = snapshot['sources']; problems = []
        def problem(kind, detail):
            problems.append(dict(kind=kind, detail=detail, status='open', id=sha((kind+':'+detail).encode())))
        # A later no-change collection cannot resolve an orphaned data release.
        pending=set(previous.get('pending_data_releases',[]))
        snapshot['data_release_metadata']={}
        try:
            current=self.capture(RAW+'VERSION',sources).decode().strip()
            if not re.fullmatch(r'\d+\.\d+\.\d+',current):
                raise ValueError('Main product version is invalid')
            versions=[current]+sorted(pending-{current})
            for version in versions[:5]:
                if not re.fullmatch(r'\d+\.\d+\.\d+',version):
                    raise ValueError('Stored product version is invalid')
                pending.add(version)
                try:
                    raw=self.capture(p1.BASE+'/releases/tags/v'+version,sources,missing=True)
                    release=json.loads(raw) if raw else None
                    asset=p1.unique_asset(release.get('assets',[]),'pitwall-dashboard.zip') if release else None
                    valid=(release and release.get('tag_name')=='v'+version and not release.get('draft')
                           and not release.get('prerelease') and asset and asset.get('size',0)>0
                           and re.fullmatch('sha256:[a-f0-9]{64}',asset.get('digest',''))
                           and p1.utc(asset['created_at'])<=p1.utc(asset['updated_at'])<=utc_now())
                    if valid:
                        pending.discard(version)
                        snapshot['data_release_metadata'][version]={'status':'uploaded_asset_metadata_present',
                            'digest':asset['digest'],'size':asset['size'],
                            'scope':'metadata only; ZIP bytes and served-host acceptance remain separate'}
                except Exception as error:
                    problem('data_publication_source',version+': '+str(error))
            if len(versions)>5:
                problem('data_publication_backlog','More than five versions need review; older pending versions retained')
        except Exception as error:
            problem('data_publication_source',str(error))
        snapshot['pending_data_releases']=sorted(pending)
        for version in sorted(pending):
            problem('data_publication',version+': release/ZIP publication not yet confirmed')
        gate_path=self.state.parent/'dependency-gate.json'
        if gate_path.exists():
            try:
                gate=json.loads(gate_path.read_text()); decision=gate['decision']
                snapshot['dependency_audit']={'checked_at_utc':gate['checked_at_utc'],
                    'counts':decision['counts'],'residual_high':decision['residual_high']}
                if not decision['accepted_for_restricted_local_profile']:
                    problem('dependency_security','Dependency policy requires intervention')
                for row in decision['residual_high']:
                    problem('dependency_security',row['package']+'@'+row['version']+': '+row['advisory']+' (open; local mitigation only)')
                if utc_now()-p1.utc(gate['checked_at_utc'])>timedelta(days=7):
                    problem('dependency_audit_due','Dependency audit is older than seven days; review without automatic upgrades')
            except Exception as error:
                problem('dependency_audit_source',str(error))
        for name in ('coletar-dados.yml','product.yml'):
            try:
                url=p1.BASE+'/actions/workflows/'+name+'/runs?branch=main&status=completed&per_page=1'
                data=json.loads(self.capture(url,sources)); rows=data['workflow_runs']
                if len(rows)!=1 or rows[0].get('head_branch')!='main' or rows[0].get('event')=='pull_request':
                    raise ValueError('No unambiguous trusted main run')
                row=rows[0]; conclusion=row['conclusion']
                snapshot['workflows'][name]={k:row.get(k) for k in ('id','conclusion','html_url','head_sha','updated_at')}
                snapshot['signals']['workflow:'+name]=conclusion
                if conclusion!='success': problem('workflow',name+': '+str(conclusion))
                if utc_now()-p1.utc(row['updated_at']) > timedelta(hours=3) and name=='coletar-dados.yml':
                    problem('stale_collection', 'No recent completed collection run; schedule may be delayed')
            except Exception as error:
                snapshot['signals']['workflow:'+name]='indeterminate'
                problem('source',name+': '+str(error))
        event=json.loads((self.root/'operacao2026/eventos/saopaulo2026.json').read_text())
        if ([event[k] for k in ('temporada','rodada','circuito_id')]!=IDENTITY
                or p1.utc(event['largada_utc'])!=p1.utc('2026-11-08T17:00:00Z')):
            raise ValueError('Supervisor event/calendar requires prior review')
        try:
            release_raw=self.capture(p1.BASE+'/releases/tags/'+TAG,sources,missing=True)
            if release_raw is None:
                q=next(s for s in event['sessions'] if s['session_name']=='Qualifying')
                status='pre_q_no_public_pair' if utc_now()<p1.utc(q['date_start']) else 'awaiting_public_pair'
                if utc_now()>=p1.utc(event['largada_utc'])-timedelta(hours=1):
                    status='missing_public_pair_deadline'; problem('coverage',status)
                snapshot['p1']={'status':status,'admissible':False,'detail':'Observed Q/host cannot be inferred from workflow success'}
            else:
                release=json.loads(release_raw)
                if release['tag_name']!=TAG or release['draft']:
                    raise ValueError('Unexpected P1 release')
                assets=[]
                for page in range(1,4):
                    batch=json.loads(self.capture(p1.BASE+'/releases/'+str(release['id'])+'/assets?per_page=100&page='+str(page),sources))
                    assets.extend(batch)
                    if len(batch)<100: break
                else: raise ValueError('Asset pagination limit exceeded')
                pair_asset=p1.unique_asset(assets,p1.PAIR_NAME)
                if pair_asset is None:
                    snapshot['p1']={'status':'pair_not_public','admissible':False}
                    if utc_now()>=p1.utc(event['largada_utc'])-timedelta(hours=1): problem('coverage','missing_public_pair_deadline')
                else:
                    pair_raw=self.asset(pair_asset,sources); path=self.blob(pair_raw)
                    pair,receipt=pair_checks(self.root,path,pair_asset,event)
                    snapshot['p1']={'status':'public_pair_verified','public_receipt':receipt,'admissible':False}
                    host=p1.unique_asset(assets,'host-acceptance.json')
                    if host:
                        host_raw=self.asset(host,sources); host_record=json.loads(host_raw)
                        p1.prior_host(host_record,sha(pair_raw),IDENTITY,p1.utc(event['largada_utc']))
                        if not p1.utc(host_record['completed_at_utc'])<=p1.utc(host['created_at'])<=p1.utc(host['updated_at'])<p1.utc(event['largada_utc']):
                            raise ValueError('Host evidence was published late')
                        snapshot['p1'].update(status='public_pair_and_host_verified',admissible=True,host_sha256=sha(host_raw))
                    elif utc_now()>=p1.utc(event['largada_utc']): problem('coverage','missing_host_before_race')
                    for asset in assets:
                        if re.fullmatch('post-race-[0-9a-f]{64}\\.json',asset['name']):
                            record=json.loads(self.asset(asset,sources))
                            posterior_checks(record,pair,sha(pair_raw),event,asset)
                            if asset['name']!='post-race-'+sha(p1.json_bytes(record['posterior']))+'.json':
                                raise ValueError('Posterior evidence name differs')
                            snapshot['post_race'].append(dict(asset=asset['name'],known_targets=record['known_targets'],unknown_targets=record['unknown_targets'],scores=record['scores']))
                    for asset in assets:
                        if asset['name'].startswith(('missing-','blocked-')):
                            problem('operation_asset',asset['name'])
        except Exception as error:
            snapshot['p1']={'status':'indeterminate','admissible':False}
            problem('P1_validation',str(error))
        snapshot['signals']['p1']=snapshot['p1']['status']
        snapshot['signals']['post_race']=sha(raw_json(snapshot['post_race']))
        # One descriptive snapshot; never starts or retries any collector.
        try:
            data=json.loads(self.capture(RAW+'frontend_assets/pilotos_condicoes_operacao.json',sources))
            for key,value in data.get('pending',{}).items():
                problem('data_review',str(key)+': '+json.dumps(value,ensure_ascii=False,sort_keys=True))
        except Exception as error: problem('descriptive_source',str(error))
        for url in OFFICIAL:
            prior=previous.get('documents',{}).get(url,{})
            if prior and utc_now()-p1.utc(prior['checked_at_utc'])<timedelta(hours=24): continue
            try:
                raw=self.capture(url,sources); current=semantic(raw)
                snapshot['documents'][url]=dict(sha256=sha(raw),semantic_sha256=current,checked_at_utc=utc_now().isoformat())
                if prior and prior['semantic_sha256']!=current:
                    problem('official_document_changed',url+' '+current)
            except Exception as error: problem('official_source',url+': '+str(error))
        # Document changes remain queued for human review across later runs.
        old_reviews=[r for r in previous.get('queue',[]) if r['kind']=='official_document_changed']
        snapshot['queue']=list({r['id']:r for r in old_reviews+problems}.values())
        for row in snapshot['queue']:
            snapshot['signals']['problem:'+row['id']]=row['status']
        return snapshot


def serve(supervisor, port=5681):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if (self.path!='/run' or self.headers.get('X-Pitwall-Supervisor')!='v1'
                    or self.headers.get('Host') not in ('127.0.0.1:'+str(port),'localhost:'+str(port))
                    or self.headers.get('Origin') or self.headers.get('Content-Length','0') not in ('0','2')):
                self.send_error(403); return
            try:
                result=supervisor.run(notify=True); code=200
            except Exception as error:
                result={'status':'supervisor_failed','error_type':type(error).__name__}; code=500
            raw=raw_json(result); self.send_response(code)
            self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    HTTPServer(('127.0.0.1',port),Handler).serve_forever()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('run','serve'))
    parser.add_argument('--state',type=Path,default=DEFAULT_STATE)
    parser.add_argument('--archive',type=Path,default=DEFAULT_ARCHIVE)
    parser.add_argument('--root',type=Path,default=PROJECT_ROOT)
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args(); supervisor=Supervisor(args.root,args.state,args.archive)
    if args.command=='serve': serve(supervisor)
    else:
        result=supervisor.run(force=args.force)
        print(json.dumps(dict(status=result.get('p1',{}).get('status',result.get('status')),changed=result['changed'],events=len(result['events']))))


if __name__=='__main__': main()
