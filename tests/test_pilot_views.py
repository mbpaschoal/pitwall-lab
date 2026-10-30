"""Exercise navigation and language changes with the shipped, offline dataset."""
from pathlib import Path
import json
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class PilotViewTests(unittest.TestCase):
    def test_overview_profile_and_language_preserve_the_selection(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.sidebar.radio[0].set_value("Pilotos").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("pilot-cards" in x.value and "Norris" in x.value for x in app.markdown))
        app.multiselect(key="pilot_years").set_value([2025, 2026]).run()
        app.radio(key="pilot_view").set_value("Perfil individual").run()
        app.selectbox(key="pilot_driver").set_value("max_verstappen").run()
        next(x for x in app.button if x.label == "🇬🇧").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pilot_years"], [2025, 2026])
        self.assertEqual(app.session_state["pilot_driver"], "max_verstappen")
        self.assertEqual(app.metric[0].label, "Starts")
        self.assertEqual(app.metric[0].value, "42")
        columns = json.loads(app.dataframe[0].proto.columns)
        self.assertEqual(columns["Race"]["type_config"]["type"], "link")

    def test_deep_link_opens_the_named_driver(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        app.query_params.update(tela="Pilotos", piloto="max_verstappen", visao="perfil", lang="en")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pilot_driver"], "max_verstappen")
        self.assertEqual(app.session_state["pilot_view"], "Perfil individual")
        self.assertEqual(app.metric[0].value, "66")

    def test_page_changes_preserve_race_and_driver_filters(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(temporada="2024", gp="12")
        at.run()
        at.sidebar.radio[0].set_value("Pilotos").run()
        at.multiselect(key="pilot_years").set_value([2025]).run()
        at.sidebar.radio[0].set_value("Corridas").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.sidebar.radio[0].value, "Corridas")
        self.assertEqual(at.selectbox(key="temporada").value, 2024)
        self.assertEqual(at.selectbox(key="gp").value, "2024:12")
        at.sidebar.radio[0].set_value("Pilotos").run()
        self.assertEqual(at.multiselect(key="pilot_years").value, [2025])

    def test_shared_duel_opens_in_english_with_both_drivers(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(tela="Pilotos", visao="duelo", piloto="max_verstappen", rival="norris", anos="2026", lang="en")
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["pilot_years"], [2026])
        self.assertEqual(at.session_state["pilot_driver"], "max_verstappen")
        self.assertEqual(at.session_state["duel_right"], "norris")
        self.assertIn("Finished ahead of rival", [x.label for x in at.metric])

    def test_driver_without_starts_in_period_is_not_replaced(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(tela="Pilotos", visao="perfil", piloto="bortoleto", anos="2024", lang="en")
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox(key="pilot_driver").value, "bortoleto")
        self.assertEqual(at.metric[0].value, "0")
        self.assertTrue(any("Gabriel Bortoleto" in x.value for x in at.markdown))


if __name__ == "__main__":
    unittest.main()
