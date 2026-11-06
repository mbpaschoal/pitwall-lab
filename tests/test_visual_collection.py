"""Offline image-capture integrity; existing catalogued bytes are preserved."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ferramentas_catalogo_visual as visual


class VisualCaptureTests(unittest.TestCase):
    def test_divergent_download_preserves_existing_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'image.png'
            path.write_bytes(b'previous image')
            with patch.object(visual, 'urlopen', return_value=BytesIO(b'new image')):
                with self.assertRaises(FileExistsError):
                    visual._baixar('https://example.test/image', path)
            self.assertEqual(path.read_bytes(), b'previous image')

    def test_identical_download_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'image.png'
            for _ in range(2):
                with patch.object(visual, 'urlopen', return_value=BytesIO(b'fixed image')):
                    self.assertEqual(visual._baixar('https://example.test/image', path),
                                     hashlib.sha256(b'fixed image').hexdigest())
            self.assertEqual(path.read_bytes(), b'fixed image')

    def test_symlink_destination_is_rejected_before_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'original.png'
            target.write_bytes(b'original image')
            path = Path(tmp) / 'link.png'
            path.symlink_to(target)
            with patch.object(visual, 'urlopen', return_value=BytesIO(b'new image')) as request:
                with self.assertRaises(ValueError):
                    visual._baixar('https://example.test/image', path)
                request.assert_not_called()
            self.assertEqual(target.read_bytes(), b'original image')

    def test_corrupted_catalogued_image_is_not_silently_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'dashboard_assets/circuit'
            folder.mkdir(parents=True)
            entries = {}
            for name in ('foto', 'mapa'):
                path = folder / (name + '.png')
                path.write_bytes(b'corrupted image' if name == 'foto' else b'fixed image')
                entries[name] = dict(caminho=path.relative_to(root).as_posix(),
                                     sha256=hashlib.sha256(b'fixed image').hexdigest())
            catalog = folder / 'catalogo_visual.json'
            catalog.write_text(json.dumps(dict(versao=1, circuitos=dict(fixture=entries))))
            before = catalog.read_bytes()
            with patch.object(visual, 'CANDIDATOS', {'fixture': ('photo', 'map')}), \
                 patch.object(visual, '_api') as api:
                with self.assertRaisesRegex(ValueError, 'hash'):
                    visual.gerar(root, pausa=0)
                api.assert_not_called()
            self.assertEqual(catalog.read_bytes(), before)
            self.assertEqual((folder / 'foto.png').read_bytes(), b'corrupted image')


if __name__ == '__main__':
    unittest.main()
