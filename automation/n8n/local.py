"""Local n8n Community launcher. Data stays outside Dropbox; no cloud account."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path.home()/'Library/Application Support/Pitwall Lab/n8n'
NODE = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
PYTHON = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
N8N = BASE/'runtime/node_modules/n8n/bin/n8n'
WORKFLOW_ID = 'PitwallFreeSupervisor01'


def environment():
    # Start with a small environment; never inherit GitHub/Dropbox/LLM tokens.
    env = {k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','TMPDIR','LANG','LC_ALL')}
    env.update(PATH=str(NODE.parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
               N8N_USER_FOLDER=str(BASE/'data'), N8N_LISTEN_ADDRESS='127.0.0.1',
               N8N_HOST='localhost', N8N_PORT='5678', N8N_PROTOCOL='http',
               N8N_DIAGNOSTICS_ENABLED='false', N8N_VERSION_NOTIFICATIONS_ENABLED='false',
               N8N_TEMPLATES_ENABLED='false', N8N_COMMUNITY_PACKAGES_ENABLED='false',
               N8N_PERSONALIZATION_ENABLED='false', N8N_BLOCK_ENV_ACCESS_IN_NODE='true',
               NODES_INCLUDE=json.dumps(['n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest']),
               N8N_PAYLOAD_SIZE_MAX='1',
               N8N_RUNNERS_ENABLED='false', N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS='true',
               GENERIC_TIMEZONE='America/Sao_Paulo', TZ='America/Sao_Paulo',
               EXECUTIONS_DATA_MAX_AGE='168', EXECUTIONS_DATA_PRUNE='true',
               EXECUTIONS_DATA_PRUNE_MAX_COUNT='1000')
    return env


def cli(*args):
    env=environment()
    if args and args[0]=='execute':
        env['N8N_RUNNERS_BROKER_PORT']='5683'
        # CLI execution dumps internal resume tokens. Keep only a safe receipt.
        result=subprocess.run([str(NODE),str(N8N),*args],env=env,capture_output=True,text=True)
        import json
        passed=result.returncode==0 and '"status": "success"' in result.stdout
        print(json.dumps(dict(command='execute',returncode=result.returncode,success=passed)))
        if not passed:
            raise RuntimeError('n8n execution failed; inspect its local authenticated UI')
        return result
    return subprocess.run([str(NODE),str(N8N),*args],env=env,check=True)


def deploy():
    """Install only explicitly selected source bytes, not a recursive repo copy."""
    validate_audit_gate()
    source = BASE/'source'; source.mkdir(parents=True,exist_ok=True)
    files = ['pitwall/__init__.py','pitwall/paths.py','pitwall/operations/__init__.py',
             'pitwall/operations/prospective.py','pitwall/operations/supervision.py',
             'operacao2026/eventos/saopaulo2026.json', 'automation/n8n/local.py',
             'automation/n8n/supervisor.json','automation/n8n/audit_result.py',
             'automation/n8n/pnpm-lock.yaml','automation/n8n/pnpm-workspace.yaml',
             'automation/n8n/package.json','automation/n8n/UPSTREAM.md']
    folder = ROOT/'reports/prospectivo_p1_20261105'
    import json
    files += [str(Path('reports/prospectivo_p1_20261105')/name) for name in json.loads((folder/'public-protocol-manifest.json').read_text())['files']]
    files += ['reports/prospectivo_p1_20261105/public-protocol-manifest.json']
    for name in files:
        dest=source/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    BASE.chmod(0o700)
    (BASE/'logs').mkdir(exist_ok=True)
    (BASE/'data').mkdir(exist_ok=True,mode=0o700)
    database=BASE/'data/.n8n/database.sqlite'
    if database.exists():
        with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as connection:
            exists=connection.execute('SELECT id FROM workflow_entity WHERE id=?',(WORKFLOW_ID,)).fetchone()
        if exists:
            cli('unpublish:workflow','--id='+WORKFLOW_ID)
    cli('import:workflow','--input='+str(source/'automation/n8n/supervisor.json'))
    cli('publish:workflow','--id='+WORKFLOW_ID)


def install():
    runtime=BASE/'runtime'; runtime.mkdir(parents=True,exist_ok=True)
    BASE.chmod(0o700)
    for name in ('package.json','pnpm-workspace.yaml','pnpm-lock.yaml'):
        shutil.copyfile(ROOT/'automation/n8n'/name,runtime/name)
    pnpm=NODE.parents[1]/'../bin/fallback/pnpm'
    subprocess.run([str(pnpm.resolve()),'install','--frozen-lockfile','--store-dir',str(runtime/'store'),
                    '--config.managePackageManagerVersions=false'],cwd=runtime,env=environment(),check=True)
    audit=subprocess.run([str(pnpm.resolve()),'audit','--prod','--json'],cwd=runtime,env=environment(),capture_output=True,text=True)
    if audit.returncode not in (0,1):
        raise RuntimeError('Dependency audit unavailable')
    import runpy
    parsed=json.loads(audit.stdout[audit.stdout.index('{'):])
    evaluate=runpy.run_path(str(ROOT/'automation/n8n/audit_result.py'))['evaluate']
    decision=evaluate(parsed,environment())
    (BASE/'dependency-audit.json').write_text(json.dumps(parsed,indent=2)+'\n')
    gate=dict(decision=decision,lock_sha256=hashlib.sha256((runtime/'pnpm-lock.yaml').read_bytes()).hexdigest(),
              profile=audit_profile(),checked_at_utc=datetime.now(timezone.utc).isoformat())
    (BASE/'dependency-gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    if not decision['accepted_for_restricted_local_profile']:
        raise RuntimeError('Dependency findings block local deployment')


def audit_profile():
    env=environment()
    return {k:env[k] for k in ('N8N_LISTEN_ADDRESS','NODES_INCLUDE','N8N_PAYLOAD_SIZE_MAX','N8N_COMMUNITY_PACKAGES_ENABLED')}


def validate_audit_gate():
    gate=json.loads((BASE/'dependency-gate.json').read_text())
    expected=hashlib.sha256((ROOT/'automation/n8n/pnpm-lock.yaml').read_bytes()).hexdigest()
    if (gate['lock_sha256']!=expected or gate['profile']!=audit_profile()
            or gate['decision']['accepted_for_restricted_local_profile'] is not True):
        raise ValueError('Install and audit the exact lockfile/profile before deployment')


def agents():
    dest=Path.home()/'Library/LaunchAgents'; dest.mkdir(parents=True,exist_ok=True)
    for role in ('bridge','engine'):
        name='com.mbpaschoal.pitwall.n8n.'+role
        path=dest/(name+'.plist')
        data=dict(Label=name,ProgramArguments=[str(PYTHON),str(BASE/'source/automation/n8n/local.py'),role],
                  RunAtLoad=True,KeepAlive=True,ThrottleInterval=30,
                  WorkingDirectory=str(BASE/'source'),
                  StandardOutPath=str(BASE/'logs'/(role+'.log')),
                  StandardErrorPath=str(BASE/'logs'/(role+'.err.log')))
        if path.exists() and plistlib.loads(path.read_bytes())!=data:
            raise FileExistsError('Existing LaunchAgent differs; review before replacing')
        path.write_bytes(plistlib.dumps(data))
        result=subprocess.run(['/bin/launchctl','bootstrap','gui/'+str(os.getuid()),str(path)],capture_output=True)
        if result.returncode:
            subprocess.run(['/bin/launchctl','print','gui/'+str(os.getuid())+'/'+name],check=True,stdout=subprocess.DEVNULL)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('install','deploy','agents','stop','engine','bridge','execute','export'))
    args=parser.parse_args()
    if args.command=='install': install()
    elif args.command=='deploy': deploy()
    elif args.command=='agents': agents()
    elif args.command=='stop':
        for role in ('engine','bridge'):
            subprocess.run(['/bin/launchctl','bootout','gui/'+str(os.getuid())+'/com.mbpaschoal.pitwall.n8n.'+role],check=True)
    elif args.command=='engine': cli('start')
    elif args.command=='bridge':
        os.execve(str(PYTHON),[str(PYTHON),'-B','-m','pitwall.operations.supervision','serve','--root',str(ROOT)],environment())
    elif args.command=='execute': cli('execute','--id='+WORKFLOW_ID)
    else: cli('export:workflow','--id='+WORKFLOW_ID,'--output='+str(BASE/'workflow-export.json'))


if __name__=='__main__': main()
