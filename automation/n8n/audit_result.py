"""Gate the n8n lockfile, preserving explicit local-only residual findings."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
NODES={'n8n-nodes-base.manualTrigger','n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest'}
RESIDUAL='GHSA-mrhx-c7xc-m3w5'


def runtime_profile():
    spec=importlib.util.spec_from_file_location('pitwall_n8n_profile',HERE/'local.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.environment()


def evaluate(report,environment):
    if 'error' in report or not isinstance(report.get('advisories'),dict) or 'vulnerabilities' not in report.get('metadata',{}):
        raise ValueError('A complete registry audit is required')
    if (environment.get('N8N_LISTEN_ADDRESS')!='127.0.0.1'
            or set(json.loads(environment.get('NODES_INCLUDE','[]')))!=NODES
            or environment.get('N8N_PAYLOAD_SIZE_MAX')!='1'
            or environment.get('N8N_COMMUNITY_PACKAGES_ENABLED')!='false'):
        raise ValueError('Residual decision requires the restricted local profile')
    residual=[];blocked=[]
    for advisory in report['advisories'].values():
        if advisory['severity'] not in ('high','critical'): continue
        identity=advisory['url'].rsplit('/',1)[-1]
        versions={f['version'] for f in advisory.get('findings',[])}
        if (advisory['severity']=='high' and identity==RESIDUAL
                and advisory['module_name']=='zod' and versions=={'3.25.76'}):
            residual.append(dict(advisory=identity,package='zod',version='3.25.76',status='open; local mitigation only'))
        else:
            blocked.append(dict(advisory=identity,package=advisory['module_name'],severity=advisory['severity']))
    # Metadata and advisory records must agree; missing records are not clean.
    counts=report['metadata']['vulnerabilities']
    if counts.get('critical',0) and not any(a['severity']=='critical' for a in blocked):
        raise ValueError('Critical advisory details are absent')
    if counts.get('high',0)>len(blocked)+len(residual):
        raise ValueError('High advisory details are incomplete')
    return dict(accepted_for_restricted_local_profile=not blocked,counts=counts,blocked=blocked,residual_high=residual,
                zero_vulnerabilities_claimed=False,public_server_profile_accepted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args(); raw=args.input.read_text()
    report=json.loads(raw[raw.index('{'):]); result=evaluate(report,runtime_profile())
    with args.output.open('x') as output: json.dump(result,output,indent=2); output.write('\n')
    print(json.dumps(result))
    if not result['accepted_for_restricted_local_profile']: raise SystemExit(1)


if __name__=='__main__': main()
