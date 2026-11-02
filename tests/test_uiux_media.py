"""Delivery variants keep source identity and enough detail for mobile/desktop DPR2."""
import hashlib
import json
from pathlib import Path
import unittest

from pitwall.dashboard.hero_assets import hero_asset
from pitwall.dashboard.media import responsive_attributes

ROOT = Path(__file__).resolve().parents[1]


class ResponsiveMediaTests(unittest.TestCase):
    def test_derivatives_match_documented_original_without_replacing_it(self):
        item = json.loads((ROOT / 'static/pitwall-media/catalog.json').read_text())['method']
        original = ROOT / item['source_path']
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), hero_asset('method')['sha256'])
        self.assertEqual(item['source_sha256'], hero_asset('method')['sha256'])
        widths = []
        for variant in item['variants']:
            contents = (ROOT / variant['path']).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), variant['sha256'])
            self.assertLess(len(contents), original.stat().st_size)
            self.assertAlmostEqual(variant['width'] / variant['height'], 3793 / 2134, delta=.002)
            widths.append(variant['width'])
        self.assertGreaterEqual(min(widths), 494 * 2)
        self.assertGreaterEqual(max(widths), 1742 * 2)

    def test_unknown_photo_cannot_inject_an_arbitrary_static_path(self):
        self.assertIsNone(responsive_attributes({'path': '../../private'}))
        with self.assertRaises(ValueError):
            responsive_attributes(dict(hero_asset('method'), sha256='changed'))
        attrs = responsive_attributes(hero_asset('method'))
        self.assertIn('srcset=', attrs)
        self.assertNotIn('data:', attrs)


if __name__ == '__main__':
    unittest.main()
