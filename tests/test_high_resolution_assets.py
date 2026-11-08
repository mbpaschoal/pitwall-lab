"""Release contracts for real photographs and their unmodified source bytes."""

import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image

from pitwall.dashboard.hero_assets import HERO_IMAGES, hero_asset, portrait_asset, profile_asset, profile_crop_geometry


ROOT = Path(__file__).resolve().parents[1]


class TestHighResolutionAssets(unittest.TestCase):
    def assert_original(self, path, metadata, minimum_width, minimum_height):
        self.assertTrue(path.is_file(), str(path))
        with Image.open(path) as image:
            encoded = (metadata.get('encoded_width', metadata['width']),
                       metadata.get('encoded_height', metadata['height']))
            self.assertEqual(image.size, encoded)
            if 'exif_orientation' in metadata:
                orientation = image.getexif().get(274, 1)
                self.assertEqual(orientation, metadata['exif_orientation'])
                displayed = encoded[::-1] if orientation in (5, 6, 7, 8) else encoded
                self.assertEqual(displayed, (metadata['width'], metadata['height']))
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

    def test_registered_profiles_have_a_photo_or_the_explicit_doohan_deferral(self):
        catalog = json.loads((ROOT / 'frontend_assets/profile_photos.json').read_text())
        sources = json.loads((ROOT / 'dashboard_assets/fan/sources.json').read_text())
        registered = {item.get('driver_id') or Path(item['file']).stem for item in sources
                      if item.get('file', '').startswith('portraits/')}
        photos = set(catalog['photos'])
        deferred = catalog.get('deferred_profiles', {})
        self.assertFalse(photos.intersection(deferred))
        self.assertLessEqual(set(deferred), {'doohan'})
        self.assertEqual(photos.union(deferred), registered,
                         'Every driver needs a reviewed photo or an explicitly documented deferral')
        for driver, pending in deferred.items():
            with self.subTest(driver=driver):
                self.assertEqual(pending['driver_id'], driver)
                self.assertEqual(pending['status'], 'awaiting_suitable_original')
                self.assertEqual(pending['publication_decision'], 'retain_existing_portrait_temporarily')
                self.assertEqual(len(pending['reason']), 2)
                self.assertTrue(all(pending['reason']))
                self.assertEqual(pending['fallback_path'], portrait_asset(driver)['path'])
                self.assertEqual(pending['fallback_sha256'], hashlib.sha256(
                    (ROOT / pending['fallback_path']).read_bytes()).hexdigest())
                self.assertIsNone(profile_asset(driver))
                from pitwall.dashboard.fan_views import hero
                rendered = hero('Jack Doohan', person=dict(id=driver, name='Jack Doohan'))
                self.assertIn('data-driver-id="doohan"', rendered)
                self.assertNotIn('fan-hero-profile-editorial', rendered)

    def test_editorial_profiles_use_separate_high_resolution_originals(self):
        catalog = json.loads((ROOT / 'frontend_assets/profile_photos.json').read_text())
        self.assertTrue(catalog['photos'])
        for driver, photo in catalog['photos'].items():
            with self.subTest(driver=driver):
                self.assert_original(ROOT / photo['path'], photo, 1600, 1600)
                self.assertEqual(profile_asset(driver)['driver_id'], driver)
                crop = profile_crop_geometry(photo)
                if crop:
                    self.assertGreaterEqual(crop['native_width'], 1600)
                    self.assertGreaterEqual(crop['native_height'], 1600)
                podium = ROOT / portrait_asset(driver)['path']
                self.assertNotEqual(photo['path'], portrait_asset(driver)['path'])
                self.assertNotEqual(photo['sha256'], hashlib.sha256(podium.read_bytes()).hexdigest(),
                                    'The profile must not reuse the podium photograph')
                self.assertEqual(len(photo['caption']), 2)
                self.assertTrue(all(photo['caption']))
                self.assertTrue(photo['author'])
                self.assertTrue(photo['source'].startswith('https://'))
                self.assertTrue(photo['license_url'].startswith('https://'))

    def test_focal_profile_rejects_invalid_or_insufficient_source_pixels(self):
        base = dict(width=6000, height=4000,
                    focal_crop=dict(top=0, right=25, bottom=25, left=25))
        self.assertIsNone(profile_crop_geometry(dict(width=6000, height=4000)))
        for invalid in [dict(base, focal_crop=None),
                        dict(base, focal_crop=dict(top=0, right=50, bottom=0, left=50)),
                        dict(base, focal_crop=dict(top=0, right=0, bottom=75, left=0)),
                        dict(base, focal_crop=dict(top=float('nan'), right=0, bottom=0, left=0)),
                        dict(base, focal_crop=dict(top=False, right=0, bottom=0, left=0)),
                        dict(base, width=0)]:
            with self.subTest(spec=invalid), self.assertRaises(ValueError):
                profile_crop_geometry(invalid)

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
