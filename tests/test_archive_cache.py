"""Archive reuse must preserve validation, live content identity and isolation."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pitwall.dashboard import archive_cache
from pitwall.data import archive


class TestArchiveCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / archive.ASSET
        self.base.parent.mkdir()
        self.base.write_bytes(b'{"revision":1}')
        archive_cache._load_cached.clear()
        self.addCleanup(archive_cache._load_cached.clear)

    def test_unchanged_content_reuses_validation_and_returns_isolated_copies(self):
        with patch.object(archive, 'carregar', return_value={'gps': {'2026:19': {}}}) as loader:
            first = archive_cache.carregar(self.root)
            first['gps'].clear()
            second = archive_cache.carregar(self.root)
        self.assertEqual(loader.call_count, 1)
        self.assertIn('2026:19', second['gps'])

    def test_same_size_and_timestamp_content_change_invalidates_cache(self):
        stat = self.base.stat()
        with patch.object(archive, 'carregar', side_effect=lambda root: {'raw': self.base.read_bytes()}) as loader:
            first = archive_cache.carregar(self.root)
            self.base.write_bytes(b'{"revision":2}')
            os.utime(self.base, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            second = archive_cache.carregar(self.root)
        self.assertEqual(loader.call_count, 2)
        self.assertNotEqual(first, second)

    def test_each_complement_creation_change_and_removal_invalidates_cache(self):
        for relative, _, _ in archive_cache._INPUTS[1:]:
            with self.subTest(input=relative):
                archive_cache._load_cached.clear()
                path = self.root / relative
                with patch.object(archive, 'carregar', return_value={}) as loader:
                    archive_cache.carregar(self.root)
                    path.write_bytes(b'{"revision":1}')
                    archive_cache.carregar(self.root)
                    stat = path.stat()
                    path.write_bytes(b'{"revision":2}')
                    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                    archive_cache.carregar(self.root)
                    path.unlink()
                    archive_cache.carregar(self.root)
                self.assertEqual(loader.call_count, 3)  # Original absent-content key is reusable.

    def test_warm_cache_rejects_symlink_before_returning_any_projection(self):
        with patch.object(archive, 'carregar', return_value={}) as loader:
            archive_cache.carregar(self.root)
            saved = self.root / 'saved.json'
            self.base.rename(saved)
            self.base.symlink_to(saved)
            with self.assertRaisesRegex(archive.AcervoDashboardErro, 'symlink'):
                archive_cache.carregar(self.root)
        self.assertEqual(loader.call_count, 1)

    def test_warm_cache_rejects_removed_or_oversized_required_input(self):
        with patch.object(archive, 'carregar', return_value={}) as loader:
            archive_cache.carregar(self.root)
            self.base.unlink()
            with self.assertRaises(archive.AcervoDashboardErro):
                archive_cache.carregar(self.root)
            with self.base.open('wb') as stream:
                stream.truncate(archive.MAX_BYTES + 1)
            with self.assertRaises(archive.AcervoDashboardErro):
                archive_cache.carregar(self.root)
        self.assertEqual(loader.call_count, 1)

    def test_changing_inputs_during_load_is_rejected_and_not_cached(self):
        def changed(root):
            self.base.write_bytes(b'{"revision":2}')
            return {'stale': True}
        with patch.object(archive, 'carregar', side_effect=changed):
            with self.assertRaisesRegex(archive.AcervoDashboardErro, 'mudaram'):
                archive_cache.carregar(self.root)
        with patch.object(archive, 'carregar', return_value={'current': True}) as loader:
            self.assertEqual(archive_cache.carregar(self.root), {'current': True})
            archive_cache.carregar(self.root)
        self.assertEqual(loader.call_count, 1)

    def test_real_archive_projection_is_identical_to_canonical_loader(self):
        root = Path(__file__).resolve().parents[1]
        expected = archive.carregar(root)
        first = archive_cache.carregar(root)
        self.assertEqual(first, expected)
        first['gps'].clear()
        self.assertEqual(archive_cache.carregar(root), expected)
