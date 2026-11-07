"""Release contracts for real photographs and their unmodified source bytes."""

import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image

from pitwall.dashboard.hero_assets import HERO_IMAGES, hero_asset, portrait_asset, profile_asset


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

    def test_editorial_profiles_use_separate_high_resolution_originals(self):
        catalog = json.loads((ROOT / 'frontend_assets/profile_photos.json').read_text())
        self.assertTrue(catalog['photos'])
        for driver, photo in catalog['photos'].items():
            with self.subTest(driver=driver):
                self.assert_original(ROOT / photo['path'], photo, 1600, 1600)
                self.assertEqual(profile_asset(driver)['driver_id'], driver)
                self.assertNotEqual(photo['path'], portrait_asset(driver)['path'])
                self.assertEqual(len(photo['caption']), 2)
                self.assertTrue(all(photo['caption']))
                self.assertTrue(photo['author'])
                self.assertTrue(photo['source'].startswith('https://'))
                self.assertTrue(photo['license_url'].startswith('https://'))

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

    def test_all_29_portrait_identities_resolve_with_legacy_filename_metadata(self):
        from pitwall.dashboard.fan_views import hero
        portraits=[x for x in json.loads((ROOT/'dashboard_assets/fan/sources.json').read_text())
                   if x.get('file','').startswith('portraits/')]
        self.assertEqual(len(portraits),29)
        for item in portraits:
            pid=item.get('driver_id') or Path(item['file']).stem
            with self.subTest(driver=pid):
                spec=portrait_asset(pid,pid.replace('_',' ').title())
                self.assertEqual(spec['path'],'dashboard_assets/fan/'+item['file'])
                self.assertEqual(spec['driver_id'],pid)
                self.assertIn('fan-hero-image',hero(pid,person=dict(id=pid,name=pid)))
        self.assertEqual(portrait_asset('norris')['path'],'dashboard_assets/fan/portraits/norris.png')

    def test_real_jpeg_portrait_is_used_for_mexico_debutant(self):
        from pitwall.dashboard.fan_views import portrait
        spec=portrait_asset('ryo_hirakawa')
        self.assertEqual(spec['path'],'dashboard_assets/fan/portraits/ryo_hirakawa.jpg')
        self.assertIn('haasf1team.com',spec['source'])
        self.assertIn('Simon Galloway',spec['credit'])
        self.assertIn('data:image/jpeg;base64,',portrait('ryo_hirakawa','Ryo Hirakawa'))
        self.assertIsNone(portrait_asset('unregistered_driver'))
        self.assertIn('fan-avatar-fallback',portrait('unregistered_driver','Unknown Driver'))

    def test_legacy_aliases_and_detached_spec(self):
        for alias, canonical in [('rain', 'drivers'), ('helmet', 'method'), ('car', 'forecast')]:
            self.assertEqual(hero_asset(alias), hero_asset(canonical))
        detached = hero_asset('drivers')
        detached['path'] = 'changed'
        self.assertNotEqual(detached, HERO_IMAGES['drivers'])
        with self.assertRaises(KeyError):
            hero_asset('unknown-driver')
