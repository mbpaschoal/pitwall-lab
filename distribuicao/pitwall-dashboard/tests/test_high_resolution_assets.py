"""Release contracts for real photographs and their unmodified source bytes."""

import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image

from pitwall.dashboard.hero_assets import HERO_IMAGES, hero_asset


ROOT = Path(__file__).resolve().parents[1]


class TestHighResolutionAssets(unittest.TestCase):
    def assert_original(self, path, metadata, minimum_width, minimum_height):
        self.assertTrue(path.is_file(), str(path))
        with Image.open(path) as image:
            self.assertEqual(image.size, (metadata['width'], metadata['height']))
            self.assertGreaterEqual(image.width, minimum_width, str(path))
            self.assertGreaterEqual(image.height, minimum_height, str(path))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), metadata['sha256'])

    def test_circuit_photographs_cover_banner_at_twice_css_size(self):
        catalog = json.loads((ROOT / 'dashboard_assets/circuit/catalogo_visual.json').read_text())
        self.assertGreaterEqual(len(catalog['circuitos']), 26)
        for circuit, metadata in catalog['circuitos'].items():
            with self.subTest(circuit=circuit):
                photo = metadata['foto']
                self.assert_original(ROOT / photo['caminho'], photo, 2488, 660)
                self.assertTrue(photo['pagina'].startswith('https://'))
                self.assertTrue(photo['autor'])
                self.assertTrue(photo['licenca'])

    def test_driver_references_are_large_identified_originals(self):
        sources = json.loads((ROOT / 'dashboard_assets/fan/sources.json').read_text())
        portraits = [item for item in sources if item['file'].startswith('portraits/')]
        self.assertGreaterEqual(len(portraits), 29)
        self.assertEqual(len({item['sha256'] for item in portraits}), len(portraits))
        for portrait in portraits:
            with self.subTest(portrait=portrait['file']):
                self.assert_original(ROOT / 'dashboard_assets/fan' / portrait['file'], portrait, 512, 512)
                self.assertTrue(portrait['url'].startswith('https://'))
                self.assertTrue(portrait['retrieved'])
                self.assertEqual(portrait['kind'], 'photograph')

    def test_five_distinct_historical_heroes_have_sources_and_resolution(self):
        canonical = ['drivers', 'championship', 'forecast', 'performance', 'method']
        self.assertEqual(len({HERO_IMAGES[name]['sha256'] for name in canonical}), 5)
        for name in canonical:
            with self.subTest(hero=name):
                spec = HERO_IMAGES[name]
                self.assert_original(ROOT / spec['path'], spec, 2488, 660)
                self.assertEqual(spec['kind'], 'photograph')
                self.assertTrue(spec['historical'])
                self.assertFalse(spec['portrait'])
                for field in ['driver_id', 'name', 'source', 'credit', 'author', 'license', 'event', 'alt_pt', 'alt_en']:
                    self.assertTrue(spec[field], field)
        drivers = HERO_IMAGES['drivers']
        backdrop = drivers['backdrop']
        self.assert_original(ROOT / backdrop['path'], backdrop, 2488, 660)
        self.assertNotEqual(backdrop['sha256'], drivers['sha256'])
        self.assertNotEqual(backdrop['driver_id'], drivers['driver_id'])
        self.assertTrue(drivers['composition_pt'])
        self.assertTrue(drivers['composition_en'])

    def test_legacy_aliases_and_detached_spec(self):
        for alias, canonical in [('rain', 'drivers'), ('helmet', 'method'), ('car', 'forecast')]:
            self.assertEqual(hero_asset(alias), hero_asset(canonical))
        detached = hero_asset('drivers')
        detached['path'] = 'changed'
        self.assertNotEqual(detached, HERO_IMAGES['drivers'])
        with self.assertRaises(KeyError):
            hero_asset('unknown-driver')
