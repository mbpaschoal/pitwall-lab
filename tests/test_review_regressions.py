"""Regressions for the approved critical review."""
import unittest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from tests.test_driver_conditions import dataset, result
from pitwall.research.driver_conditions import profile


class ReviewRegressions(unittest.TestCase):
    def test_reference_only_contains_driver_start_opportunities(self):
        asset = dataset([result('a', 1), result('b', 2), result('b', 1, '2024:2')])
        comparison = profile(asset, 'a')['conditions'][0]
        self.assertEqual(comparison['reference']['starts'], 1)
        self.assertEqual(comparison['reference']['wins'], 0)

    def test_profile_link_restores_all_filters(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30)
        app.query_params.update(tela='Pilotos', piloto='max_verstappen', visao='perfil', anos='2026', metrica='wins', minimo='10')
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['pilot_years'], [2026])
        self.assertEqual(app.session_state['pilot_metric'], 'wins')
        self.assertEqual(app.session_state['pilot_minimum'], 10)
