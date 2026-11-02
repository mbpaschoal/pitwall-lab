"""Publish validated data atomically, or retry from the latest main checkout.

Generated versions/packages are never rebased. A retry gets current source and
reprojects preserved captures through the ordinary collection/validation flow.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

from pitwall.paths import PROJECT_ROOT
from pitwall.publishing.releases import notes

MAX_RECOVERIES = 2
PUBLIC_PATHS = (
    'VERSION', 'CHANGELOG.md', 'CHANGELOG.en.md',
    'publicacao/templates/requirements.txt',
    'frontend_assets/operacao_fim_semana.json', 'distribuicao/pitwall-dashboard',
)


def command(root, args):
    return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.PIPE).strip()


def remote_head(root, run=command):
    run(root, ['git', 'fetch', '--no-tags', 'origin', 'main'])
    return run(root, ['git', 'rev-parse', 'FETCH_HEAD'])


def save_result(path, result, publication):
    result['publicacao'] = publication
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return publication


def retry(root, path, result, attempt, run_id, source, latest, run):
    publication = dict(estado='retry_scheduled', published=False,
                       source_commit=source, latest_commit=latest,
                       recovery_attempt=attempt, run_id=run_id)
    if attempt >= MAX_RECOVERIES:
        publication['estado'] = 'conflict_retry_limit'
        save_result(path, result, publication)
        raise RuntimeError('Concurrent updates exhausted recovery attempts; captures remain preserved.')
    try:
        run(root, ['gh', 'workflow', 'run', 'coletar-dados.yml',
                   '--ref', 'main', '--field', 'recovery_attempt=' + str(attempt + 1),
                   '--field', 'parent_run=' + run_id])
    except subprocess.CalledProcessError:
        publication['estado'] = 'retry_dispatch_failed'
        save_result(path, result, publication)
        raise
    publication['next_attempt'] = attempt + 1
    return save_result(path, result, publication)


def publish(root, result_path, zip_path, captures_path, *, attempt=0, run_id='', run=command):
    root, result_path = Path(root), Path(result_path)
    if type(attempt) is not int or not 0 <= attempt <= MAX_RECOVERIES:
        raise ValueError('Invalid recovery attempt')
    if not re.fullmatch(r'[0-9]*', run_id):
        raise ValueError('Invalid parent run id')
    result = json.loads(result_path.read_text())
    if result.get('changed') is not True:
        raise ValueError('No substantive data change to publish')
    if run(root, ['git', 'diff', '--cached', '--name-only']):
        raise ValueError('Unexpected staged files before data publication')
    source = run(root, ['git', 'rev-parse', 'HEAD'])
    latest = remote_head(root, run)
    if source != latest:
        return retry(root, result_path, result, attempt, run_id, source, latest, run)
    version = (root / 'VERSION').read_text().strip()
    previous = run(root, ['git', 'show', source + ':VERSION'])
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid product version')
    major, minor, patch = map(int, previous.split('.'))
    if version != '{}.{}.{}'.format(major, minor, patch + 1):
        raise ValueError('Data version must increment the latest source version')
    zip_path, captures_path = Path(zip_path).resolve(), Path(captures_path).resolve()
    if not zip_path.is_file() or not captures_path.is_file():
        raise ValueError('Validated ZIP or original capture archive missing')
    body = result_path.with_name('release-notes.md')
    body.write_text('## Português\n\n' + notes('pt', root) + '\n\n## English\n\n' + notes('en', root))
    run(root, ['git', 'config', 'user.name', 'Pitwall Lab automation'])
    run(root, ['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    run(root, ['git', 'add', '--', *PUBLIC_PATHS])
    run(root, ['git', 'commit', '-m', 'data: atualização automática / automatic update v' + version])
    tag = 'v' + version
    run(root, ['git', 'tag', '-a', tag, '-m', 'Pitwall Lab ' + version + ' — automatic data update / atualização automática'])
    try:
        run(root, ['git', 'push', '--atomic', 'origin', 'HEAD:main', 'refs/tags/' + tag])
    except subprocess.CalledProcessError:
        latest = remote_head(root, run)
        if latest == source:
            # Authentication, transport and tag failures must not masquerade as
            # a branch race or launch a loop of identical unsuccessful jobs.
            raise
        return retry(root, result_path, result, attempt, run_id, source, latest, run)
    run(root, ['gh', 'release', 'create', tag, str(zip_path), str(captures_path),
               '--verify-tag', '--title', 'Pitwall Lab ' + version, '--notes-file', str(body)])
    return save_result(result_path, result, dict(estado='published', published=True,
                       version=version, commit=run(root, ['git', 'rev-parse', 'HEAD']),
                       recovery_attempt=attempt, run_id=run_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--recovery-attempt', type=int, default=0)
    parser.add_argument('--run-id', default='')
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    publication = publish(PROJECT_ROOT, args.result, args.zip, args.captures,
                          attempt=args.recovery_attempt, run_id=args.run_id)
    if args.github_output:
        with args.github_output.open('a') as output:
            output.write('published=' + str(publication['published']).lower() + '\n')
    print(json.dumps(publication, ensure_ascii=False))


if __name__ == '__main__':
    main()
