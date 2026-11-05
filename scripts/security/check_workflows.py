"""Check the repository's trust boundaries before privileged workflows run."""
import argparse
from pathlib import Path
import re

import yaml


PRIVILEGED_JOBS = {
    ('coletar-dados.yml', 'collect'): {'contents': 'write', 'actions': 'write'},
    ('coletar-dados.yml', 'prospective'): {'contents': 'write'},
    ('product.yml', 'release'): {'contents': 'write'},
    ('maintenance.yml', 'latest'): {'contents': 'write'},
    ('maintenance.yml', 'health'): {
        'contents': 'read', 'actions': 'read', 'issues': 'write'},
}
ACTION = re.compile(r'^actions/(checkout|setup-python|setup-node|upload-artifact|cache(?:/restore|/save)?)@[0-9a-f]{40}$')


def validate_workflow(name, workflow):
    errors = []
    if workflow.get('permissions') != {'contents': 'read'}:
        errors.append('default token permissions must be contents: read')
    events = workflow.get('on', workflow.get(True, {}))
    if not isinstance(events, dict):
        errors.append('workflow events must be explicit')
        events = {}
    if 'pull_request_target' in events:
        errors.append('pull_request_target is forbidden')
    for job_id, job in workflow.get('jobs', {}).items():
        permissions = job.get('permissions', {'contents': 'read'})
        expected = PRIVILEGED_JOBS.get((name, job_id), {'contents': 'read'})
        if permissions != expected:
            errors.append(job_id + ': unexpected token permissions')
        privileged = any(value == 'write' for value in permissions.values())
        if privileged and 'pull_request' in events:
            if (name, job_id) != ('product.yml', 'release') or job.get('if') != "startsWith(github.ref, 'refs/tags/v')":
                errors.append(job_id + ': write token can reach pull request code')
        if name == 'coletar-dados.yml' and job_id in ('collect','prospective'):
            if job.get('if') != "github.repository == 'mbpaschoal/pitwall-lab' && github.ref == 'refs/heads/main'":
                errors.append('collection must be restricted to trusted main')
            if 'pull_request' in events or 'workflow_run' in events:
                errors.append('collection cannot be triggered by untrusted runs')
            if job_id == 'prospective' and job.get('needs') != 'collect':
                errors.append('prospective publication must follow serial collection')
        for step in job.get('steps', []):
            action = step.get('uses')
            if action and not ACTION.fullmatch(action):
                errors.append(job_id + ': action must use an approved repository and full commit SHA')
            if action and action.startswith('actions/checkout@'):
                options = step.get('with', {})
                if options.get('persist-credentials') is not False:
                    errors.append(job_id + ': checkout must not persist credentials')
                if 'workflow_run' in events and options.get('ref') != 'main':
                    errors.append(job_id + ': workflow_run must check out trusted main')
                if name == 'coletar-dados.yml' and job_id == 'prospective' and options.get('ref') != 'main':
                    errors.append('prospective publication must read the latest trusted main')
            if '${{ github.event.' in step.get('run', ''):
                errors.append(job_id + ': event data must not be interpolated into shell code')
    return errors


def check(root):
    failures = []
    for path in sorted((Path(root) / '.github/workflows').glob('*.yml')):
        workflow = yaml.safe_load(path.read_text())
        failures.extend(path.name + ': ' + message for message in validate_workflow(path.name, workflow))
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = check(args.root)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Workflow trust boundaries verified.')
