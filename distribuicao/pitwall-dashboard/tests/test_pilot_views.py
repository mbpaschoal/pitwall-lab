"""Exercise navigation and language changes with the shipped, offline dataset."""
from pathlib import Path
import json
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class PilotViewTests(unittest.TestCase):
    def test_overview_profile_and_language_preserve_the_selection(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        app.radio(key="tela").set_value("Pilotos").run()
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
        at.radio(key="tela").set_value("Pilotos").run()
        at.multiselect(key="pilot_years").set_value([2025]).run()
        at.radio(key="tela").set_value("Corridas").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.radio(key="tela").value, "Corridas")
        self.assertEqual(at.selectbox(key="temporada").value, 2024)
        self.assertEqual(at.selectbox(key="gp").value, "2024:12")
        at.radio(key="tela").set_value("Pilotos").run()
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

    def test_component_state_cannot_replace_the_canonical_shared_scope(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(tela="Pilotos", visao="perfil", piloto="norris",
                               anos="2026", metrica="podium_rate", minimo="3", lang="en")
        at.run()
        # A browser component can rerun before native widgets apply set_value.
        at.session_state["browser_favorite"] = "max_verstappen"
        at.session_state["pilot_years"] = [2024, 2025, 2026]
        at.session_state["pilot_metric"] = "win_rate"
        at.session_state["pilot_minimum"] = 5
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.multiselect(key="pilot_years").value, [2026])
        self.assertEqual(at.selectbox(key="pilot_metric").value, "podium_rate")
        self.assertEqual(at.selectbox(key="pilot_minimum").value, 3)
        self.assertEqual(at.selectbox(key="pilot_driver").value, "norris")

    def test_intentional_empty_period_survives_reruns_and_remains_editable(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(tela="Pilotos", visao="perfil", piloto="bortoleto", anos="2024")
        at.run()
        self.assertEqual(len(at.get("plotly_chart")), 0)
        at.multiselect(key="pilot_years").set_value([]).run()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.multiselect(key="pilot_years").value, [])
        self.assertEqual(at.session_state["_pilot_filters"]["pilot_years"], [])
        at.multiselect(key="pilot_years").set_value([2025]).run()
        self.assertFalse(at.exception)
        self.assertGreater(len(at.get("plotly_chart")), 0)

    def test_empty_conditions_do_not_create_an_unobserved_chart(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        at.query_params.update(tela="Pilotos", visao="perfil", piloto="norris", anos="2026")
        at.run()
        charts = len(at.get("plotly_chart"))
        at.multiselect(key="profile_conditions").set_value([]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any(x.value == "Selecione pelo menos uma condição." for x in at.info))
        self.assertEqual(len(at.get("plotly_chart")), charts - 1)
        self.assertEqual(at.metric[0].value, "17")


if __name__ == "__main__":
    unittest.main()
