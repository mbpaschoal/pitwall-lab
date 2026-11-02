"""Real Git races must preserve main, tags and captures, then retry fresh."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from operacao2026 import publication


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.remote = self.base / 'remote.git'
        self.seed = self.base / 'seed'
        self.git(self.base, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.git(self.base, 'clone', str(self.remote), str(self.seed))
        self.configure(self.seed)
        self.write(self.seed, 'VERSION', '1.2.3\n')
        self.write(self.seed, 'model-sentinel.txt', 'frozen scientific bytes\n')
        self.git(self.seed, 'add', '.')
        self.git(self.seed, 'commit', '-m', 'initial')
        self.git(self.seed, 'push', 'origin', 'main')
        self.worker = self.clone('worker')
        self.result = self.base / 'result.json'
        self.result.write_text(json.dumps(dict(changed=True, reason='new_data')))
        self.zip = self.base / 'pitwall-dashboard.zip'; self.zip.write_bytes(b'validated zip fixture')
        self.captures = self.base / 'captures.tar.gz'; self.captures.write_bytes(b'original captured bytes')
        self.gh = []
        self.generate(self.worker)

    def git(self, root, *args):
        return publication.command(root, ['git', *args])

    def configure(self, root):
        self.git(root, 'config', 'user.name', 'test')
        self.git(root, 'config', 'user.email', 'test@example.invalid')

    def clone(self, name):
        path = self.base / name
        self.git(self.base, 'clone', str(self.remote), str(path))
        self.configure(path)
        return path

    def write(self, root, name, value):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)

    def generate(self, root):
        major, minor, patch = map(int, (root / 'VERSION').read_text().strip().split('.'))
        version = '{}.{}.{}'.format(major, minor, patch + 1)
        self.write(root, 'VERSION', version + '\n')
        for name in ('CHANGELOG.md', 'CHANGELOG.en.md'):
            self.write(root, name, '## {} — 2026-11-02\n\n'.format(version) + 'Verified automatic data change. ' * 6)
        for name in publication.PUBLIC_PATHS[3:]:
            self.write(root, name + '/asset.json' if name.endswith('pitwall-dashboard') else name, 'new data\n')

    def advance(self, name='concurrent'):
        other = self.clone(name)
        self.write(other, 'review.md', 'New independent work must survive.\n')
        self.git(other, 'add', 'review.md')
        self.git(other, 'commit', '-m', 'concurrent update')
        self.git(other, 'push', 'origin', 'main')
        return self.git(other, 'rev-parse', 'HEAD')

    def execute(self, root, args):
        if args[0] == 'gh':
            self.gh.append(args)
            return ''
        return publication.command(root, args)

    def publish(self, **kwargs):
        return publication.publish(self.worker, self.result, self.zip, self.captures,
                                   run_id='123', run=self.execute, **kwargs)

    def test_current_source_publishes_main_and_tag_atomically(self):
        result = self.publish()
        self.assertTrue(result['published'])
        self.assertEqual(result['version'], '1.2.4')
        self.assertEqual(self.git(self.seed, 'ls-remote', 'origin', 'refs/heads/main').split()[0], result['commit'])
        self.assertTrue(self.git(self.seed, 'ls-remote', 'origin', 'refs/tags/v1.2.4'))
        self.assertEqual((self.worker / 'model-sentinel.txt').read_text(), 'frozen scientific bytes\n')
        self.assertEqual(self.gh[-1][:3], ['gh', 'release', 'create'])

    def test_advanced_main_starts_fresh_retry_without_committing_stale_generated_files(self):
        source = self.git(self.worker, 'rev-parse', 'HEAD')
        latest = self.advance()
        result = self.publish()
        self.assertFalse(result['published'])
        self.assertEqual(result['latest_commit'], latest)
        self.assertEqual(self.git(self.worker, 'rev-parse', 'HEAD'), source)
        self.assertFalse(self.git(self.seed, 'ls-remote', 'origin', 'refs/tags/v1.2.4'))
        self.assertIn('recovery_attempt=1', self.gh[-1])
        self.assertEqual(self.captures.read_bytes(), b'original captured bytes')
        # A fresh checkout preserves the independent work and uses the ordinary
        # producer's current version rather than rebasing the old package.
        self.worker = self.clone('fresh-retry')
        self.generate(self.worker)
        result = self.publish(attempt=1)
        self.assertTrue(result['published'])
        self.assertEqual((self.worker / 'review.md').read_text(), 'New independent work must survive.\n')

    def test_push_time_race_is_detected_after_atomic_rejection(self):
        normal = self.execute
        def racing(root, args):
            if args[:3] == ['git', 'push', '--atomic']:
                self.advance('racing-writer')
            return normal(root, args)
        result = publication.publish(self.worker, self.result, self.zip, self.captures,
                                     run_id='123', run=racing)
        self.assertEqual(result['estado'], 'retry_scheduled')
        self.assertFalse(self.git(self.seed, 'ls-remote', 'origin', 'refs/tags/v1.2.4'))
        self.assertEqual(self.captures.read_bytes(), b'original captured bytes')

    def test_retry_uses_version_from_the_new_main_and_keeps_existing_tags(self):
        other = self.clone('new-release')
        self.write(other, 'VERSION', '1.2.7\n')
        self.git(other, 'add', 'VERSION'); self.git(other, 'commit', '-m', 'independent release')
        self.git(other, 'tag', 'v1.2.7')
        self.git(other, 'push', '--atomic', 'origin', 'main', 'refs/tags/v1.2.7')
        self.assertFalse(self.publish()['published'])
        self.worker = self.clone('retry-after-release'); self.generate(self.worker)
        self.assertEqual(self.publish(attempt=1)['version'], '1.2.8')
        self.assertTrue(self.git(self.seed, 'ls-remote', 'origin', 'refs/tags/v1.2.7'))
        self.assertTrue(self.git(self.seed, 'ls-remote', 'origin', 'refs/tags/v1.2.8'))

    def test_foreign_staged_files_are_not_accidentally_published(self):
        self.write(self.worker, 'unrelated.txt', 'unrelated work stays local')
        self.git(self.worker, 'add', 'unrelated.txt')
        with self.assertRaisesRegex(ValueError, 'Unexpected staged'):
            self.publish()
        self.assertFalse(self.gh)
        self.assertIn('unrelated.txt', self.git(self.worker, 'diff', '--cached', '--name-only'))

    def test_permission_failure_is_not_treated_as_a_commit_conflict(self):
        normal = self.execute
        def denied(root, args):
            if args[:3] == ['git', 'push', '--atomic']:
                raise subprocess.CalledProcessError(128, args, stderr='permission denied')
            return normal(root, args)
        with self.assertRaises(subprocess.CalledProcessError):
            publication.publish(self.worker, self.result, self.zip, self.captures,
                                run_id='123', run=denied)
        self.assertFalse(self.gh)

    def test_repeated_conflicts_are_bounded_and_keep_the_capture(self):
        self.advance()
        with self.assertRaisesRegex(RuntimeError, 'exhausted'):
            self.publish(attempt=publication.MAX_RECOVERIES)
        self.assertEqual(json.loads(self.result.read_text())['publicacao']['estado'], 'conflict_retry_limit')
        self.assertFalse(self.gh)
        self.assertEqual(self.captures.read_bytes(), b'original captured bytes')

    def test_dispatch_failure_and_invalid_inputs_remain_visible(self):
        self.advance()
        normal = self.execute
        def denied(root, args):
            if args[0] == 'gh': raise subprocess.CalledProcessError(1, args)
            return normal(root, args)
        with self.assertRaises(subprocess.CalledProcessError):
            publication.publish(self.worker, self.result, self.zip, self.captures, run=denied)
        self.assertEqual(json.loads(self.result.read_text())['publicacao']['estado'], 'retry_dispatch_failed')
        for attempt in (-1, 3, True):
            with self.assertRaises(ValueError): self.publish(attempt=attempt)


if __name__ == '__main__':
    unittest.main()
