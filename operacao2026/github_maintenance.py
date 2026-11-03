"""Bounded GitHub maintenance: release ordering and quiet incident transitions.

Only GitHub Actions supplies credentials. No collection, model or forecast runs
here. The API callable is injectable so incident tests never create real issues.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = 'mbpaschoal/pitwall-lab'
INCIDENT_MARKER = '<!-- pitwall:automatic-collection-health:v1 -->'
WORKFLOW = 'coletar-dados.yml'


class GitHubAPI:
    def __init__(self, token=None):
        if os.environ.get('GITHUB_REPOSITORY', REPOSITORY) != REPOSITORY:
            raise ValueError('Maintenance is restricted to the Pitwall repository')
        self._token = token or os.environ.get('GITHUB_TOKEN')

    def __call__(self, method, path, body=None):
        if not path.startswith('/') or '://' in path or '..' in path:
            raise ValueError('Invalid repository API path')
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Pitwall-Lab-maintenance'}
        if self._token:
            headers['Authorization'] = 'Bearer ' + self._token
        if method != 'GET' and not self._token:
            raise ValueError('A workflow token is required for changes')
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers['Content-Type'] = 'application/json'
        request = Request('https://api.github.com/repos/' + REPOSITORY + path,
                          data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if method == 'GET' and path == '/releases/latest' and error.code == 404:
                return None
            # Do not print response bodies or request credentials.
            raise RuntimeError('GitHub API {} {} returned {}'.format(method, path, error.code)) from None


def all_pages(api, path, key=None):
    """Refuse a truncated inventory rather than selecting from an unknown tail."""
    out = []
    for page in range(1, 11):
        join = '&' if '?' in path else '?'
        data = api('GET', path + join + 'per_page=100&page=' + str(page))
        rows = data[key] if key else data
        if not isinstance(rows, list):
            raise ValueError('Invalid API inventory')
        out.extend(rows)
        if len(rows) < 100:
            return out
    raise ValueError('Maintenance inventory exceeded its pagination limit')


def semantic_version(value):
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value or '')
    return tuple(map(int, match.groups())) if match else None


def latest_candidate(releases, main_version):
    ceiling = semantic_version(main_version)
    if ceiling is None:
        raise ValueError('Invalid main VERSION')
    candidates = []
    for release in releases:
        tag = release.get('tag_name', '')
        version = semantic_version(tag)
        if not tag.startswith('v') or version is None or version > ceiling:
            continue
        if release.get('draft') or release.get('prerelease') or not release.get('published_at'):
            continue
        assets = [a for a in release.get('assets', []) if a.get('name') == 'pitwall-dashboard.zip']
        if (len(assets) != 1 or assets[0].get('state') != 'uploaded'
                or assets[0].get('size', 0) <= 0
                or not re.fullmatch(r'sha256:[a-f0-9]{64}', assets[0].get('digest', ''))):
            continue
        candidates.append((version, release))
    if not candidates:
        raise ValueError('No complete stable release is available')
    return max(candidates, key=lambda item: item[0])[1]


def repair_latest(api, apply=False):
    source = api('GET', '/contents/VERSION?ref=main')
    main = base64.b64decode(source['content'], validate=False).decode().strip()
    chosen = latest_candidate(all_pages(api, '/releases'), main)
    current = api('GET', '/releases/latest')
    current_tag = current.get('tag_name') if current else None
    if current and semantic_version(current_tag) and semantic_version(current_tag) > semantic_version(chosen['tag_name']):
        raise ValueError('Refusing to demote a newer highlighted release')
    changed = current_tag != chosen['tag_name']
    if changed and apply:
        api('PATCH', '/releases/' + str(chosen['id']), {'make_latest': 'true'})
        confirmed = api('GET', '/releases/latest')
        if not confirmed or confirmed['tag_name'] != chosen['tag_name']:
            raise ValueError('Release highlight verification failed')
    return dict(main_version=main, previous=current_tag, selected=chosen['tag_name'],
                changed=changed, applied=changed and apply)


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('UTC timestamp required')
    return parsed.astimezone(timezone.utc)


def collection_health(runs, now):
    relevant = [r for r in runs if r.get('head_branch') == 'main'
                and r.get('event') in ('schedule', 'workflow_dispatch', 'push')]
    done = sorted((r for r in relevant if r.get('status') == 'completed'
                   and r.get('conclusion') != 'skipped'), key=lambda r: r['run_number'], reverse=True)
    if not done:
        return dict(problem='no_completed_collection', run=None)
    last = done[0]
    if utc(last['updated_at']) > now + timedelta(minutes=5):
        raise ValueError('Future workflow receipt')
    if now - utc(last['updated_at']) > timedelta(hours=6):
        return dict(problem='collection_stale', run=last)
    if last['conclusion'] != 'success':
        return dict(problem='collection_failed', run=last)
    return dict(problem=None, run=last)


def incident_body(health):
    run = health['run']
    link = run['html_url'] if run else 'https://github.com/' + REPOSITORY + '/actions/workflows/' + WORKFLOW
    if not link.startswith('https://github.com/' + REPOSITORY + '/actions/'):
        raise ValueError('Foreign incident link')
    return (INCIDENT_MARKER + '\n\n'
            '## Português\n\nA coleta automática precisa de atenção: `' + health['problem'] + '`. '
            '[Conferir execução](' + link + '). Os dados públicos anteriores e as capturas permanecem preservados. '
            'Esta ocorrência não se repete a cada tentativa; será encerrada após uma execução saudável.\n\n'
            '## English\n\nAutomatic collection needs attention: `' + health['problem'] + '`. '
            '[Inspect run](' + link + '). Previous public data and original captures remain preserved. '
            'Repeated attempts do not create repeated notifications; a healthy execution resolves this incident.\n')


def monitor(api, now=None, apply=False):
    now = now or datetime.now(timezone.utc)
    # One page is enough to inspect the latest runs; reject incomplete freshness.
    runs = api('GET', '/actions/workflows/' + WORKFLOW + '/runs?branch=main&per_page=30')['workflow_runs']
    health = collection_health(runs, now)
    issues = all_pages(api, '/issues?state=open')
    open_incidents = [i for i in issues if not i.get('pull_request')
                      and (i.get('body') or '').startswith(INCIDENT_MARKER)
                      and i.get('user', {}).get('login') == 'github-actions[bot]']
    if len(open_incidents) > 1:
        raise ValueError('Duplicate collection incidents need review')
    issue = open_incidents[0] if open_incidents else None
    action = 'unchanged'
    if health['problem'] and not issue:
        action = 'open_incident'
        if apply:
            issue = api('POST', '/issues', {'title': 'Coleta automática precisa de atenção / Collection needs attention',
                                          'body': incident_body(health), 'assignees': ['mbpaschoal']})
    elif not health['problem'] and issue:
        action = 'resolve_incident'
        if apply:
            api('POST', '/issues/{}/comments'.format(issue['number']), {
                'body': 'Coleta recuperada / Collection recovered: ' + health['run']['html_url']})
            api('PATCH', '/issues/' + str(issue['number']), {'state': 'closed', 'state_reason': 'completed'})
    return dict(problem=health['problem'], action=action, applied=apply and action != 'unchanged',
                issue_number=issue['number'] if issue else None,
                last_run_id=health['run']['id'] if health['run'] else None,
                checked_utc=now.isoformat())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('latest', 'health', 'check-source'))
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--result', type=Path)
    args = parser.parse_args()
    if args.action == 'check-source':
        result = json.loads(args.result.read_text())
        if result.get('reason') == 'provider_access_restricted':
            raise SystemExit('Provider access restricted; previous public data retained. / Acesso restrito; dados anteriores preservados.')
        print(json.dumps({'reason': result.get('reason'), 'healthy_execution': True}))
        return
    result = repair_latest(GitHubAPI(), args.apply) if args.action == 'latest' else monitor(GitHubAPI(), apply=args.apply)
    if args.result:
        args.result.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
