"""Release policy must reject an unversioned product change and incomplete notes."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from pitwall.publishing.releases import check, notes, version

ROOT = Path(__file__).resolve().parents[1]


class TestReleases(unittest.TestCase):
    def test_real_version_has_both_languages_and_separate_model_identity(self):
        result = check(ROOT)
        self.assertEqual(result["languages"], ["pt", "en"])
        self.assertGreater(len(notes("en", ROOT)), 100)
        self.assertNotEqual(notes("en", ROOT), notes("pt", ROOT))
        self.assertNotEqual(version(ROOT), "v1")

    def test_invalid_version_and_missing_translation_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "VERSION").write_text("v1\n")
            with self.assertRaises(ValueError):
                version(root)
            (root / "VERSION").write_text("0.1.0\n")
            with self.assertRaises(ValueError):
                check(root)

    def test_product_diff_requires_increment_and_both_changelogs(self):
        from pitwall.publishing.releases import DOCUMENT_PAIRS

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for pair in DOCUMENT_PAIRS:
                for name in pair:
                    dest = root / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, dest)
            (root / "VERSION").write_text("0.1.0\n")
            # Fixture versions are independent of the real project's growing history.
            for name in ("CHANGELOG.md", "CHANGELOG.en.md"):
                (root/name).write_text("# Fixture\n\n## 0.1.0 — 2026-10-29\n\n" + "Explicit fixture release notes with behaviour, validation and limitations. "*3)

            (root / "pitwall").mkdir()
            (root / "pitwall/example.py").write_text("a=1\n")

            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True, text=True
                ).stdout

            git("init", "-q")
            git("add", "VERSION", "pitwall/example.py")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            )
            (root / "pitwall/example.py").write_text("a=2\n")
            with self.assertRaisesRegex(ValueError, "new version"):
                check(root, base="HEAD")
            (root / "VERSION").write_text("0.1.1\n")
            with self.assertRaisesRegex(ValueError, "missing"):
                check(root, base="HEAD")
            for name in ["CHANGELOG.md", "CHANGELOG.en.md"]:
                p = root / name
                p.write_text(p.read_text().replace("## 0.1.0", "## 0.1.1"))
            self.assertEqual(check(root, base="HEAD")["version"], "0.1.1")
