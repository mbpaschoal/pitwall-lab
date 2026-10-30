"""Behavioural checks for fan comparisons and standalone sharing."""
import unittest
from xml.etree import ElementTree
from tests.test_driver_conditions import dataset, result
from pitwall.research.driver_duel import duel
from pitwall.dashboard.share_cards import card_svg


class FanExplorationTests(unittest.TestCase):
    def test_duel_compares_only_shared_starts(self):
        a = dataset([result('a', 1), result('b', 2), result('a', 1, '2024:2'),
                     result('b', 3, '2024:2', started=False), result('b', 1, '2024:3')])
        out = duel(a, 'a', 'b')
        self.assertEqual(out['common_starts'], 1)
        self.assertEqual(out['left']['wins'], 1)
        self.assertEqual(out['right']['wins'], 0)
        self.assertEqual(out['left_ahead'], 1)

    def test_dsq_still_an_opportunity_but_not_a_position_match(self):
        a = dataset([result('a', 1, disqualified=True), result('b', 2)])
        out = duel(a, 'a', 'b')
        self.assertEqual(out['common_starts'], 1)
        self.assertEqual(out['comparable_results'], 0)
        self.assertEqual(out['left']['wins'], 0)

    def test_card_escapes_markup_and_keeps_scope(self):
        svg = card_svg('<script>bad</script>', '2026 · 8 races', ['3 / 8'], 'OpenF1', True)
        root = ElementTree.fromstring(svg)
        self.assertFalse(root.findall('.//{http://www.w3.org/2000/svg}script'))
        self.assertIn('2026 · 8 races', ''.join(root.itertext()))

    def test_declared_available_wind_cannot_be_null(self):
        from tests.test_driver_conditions import rehash
        from pitwall.data.driver_conditions import validate, DriverConditionsError
        asset = dataset([result('a', 1)])
        asset['gps']['2024:1']['available_fields'] = ['wind_direction']
        asset['gps']['2024:1']['wind_direction'] = None
        rehash(asset)
        with self.assertRaisesRegex(DriverConditionsError, 'Advertised field'):
            validate(asset)
        asset['gps']['2024:1']['wind_direction'] = 0
        rehash(asset)
        validate(asset)

    def test_self_duel_rejected(self):
        with self.assertRaises(ValueError):
            duel(dataset([result('a', 1)]), 'a', 'a')
