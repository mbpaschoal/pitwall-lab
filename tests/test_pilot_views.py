"""Exercise navigation and language changes with the shipped, offline dataset."""
from pathlib import Path
import json
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class PilotNavigationStateTests(unittest.TestCase):
    def restore(self, query, state):
        from pitwall.dashboard.pilot_views import _restore_navigation_state
        _restore_navigation_state(query, state, {"norris": "Norris", "max_verstappen": "Verstappen"})

    def test_deep_link_restores_valid_filters_and_driver_pair(self):
        state = {}
        self.restore(dict(piloto="norris", rival="max_verstappen", visao="duelo",
                          anos="2026,2025,2026", metrica="podium_rate", minimo="3",
                          condicao="rain", faixas="rain,unknown", duelo_condicao="rain"), state)
        self.assertEqual(state["pilot_years"], [2026, 2025])
        self.assertEqual(state["pilot_driver"], "norris")
        self.assertEqual(state["duel_right"], "max_verstappen")
        self.assertEqual(state["pilot_view"], "Duelo")
        self.assertEqual(state["pilot_metric"], "podium_rate")
        self.assertEqual(state["pilot_minimum"], 3)
        self.assertEqual(state["profile_conditions"], ["rain"])

    def test_invalid_link_values_preserve_existing_choices(self):
        for years in ("2027", "2026,bad", "2026,2027"):
            with self.subTest(years=years):
                state = dict(pilot_years=[2025], pilot_driver="norris",
                             pilot_metric="wins", pilot_minimum=10, pilot_view="Duelo")
                self.restore(dict(anos=years, piloto="unknown", metrica="unknown",
                                  minimo="-1", visao="unknown"), state)
                self.assertEqual(state["pilot_years"], [2025])
                self.assertEqual(state["pilot_driver"], "norris")
                self.assertEqual(state["pilot_metric"], "wins")
                self.assertEqual(state["pilot_minimum"], 10)
                self.assertEqual(state["pilot_view"], "Duelo")

    def test_empty_selections_are_preserved_without_aliasing_saved_lists(self):
        state = {}
        self.restore(dict(anos="", faixas=""), state)
        self.assertEqual(state["pilot_years"], [])
        self.assertEqual(state["profile_conditions"], [])
        state["pilot_years"].append(2026)
        self.assertEqual(state["_pilot_filters"]["pilot_years"], [])

    def test_unchanged_url_keeps_widget_selection_and_saved_comparison_scope(self):
        query = dict(piloto="norris", anos="2026", metrica="podium_rate", minimo="3")
        state = {}
        self.restore(query, state)
        state.update(pilot_driver="max_verstappen", pilot_years=[2024], pilot_metric="wins")
        self.restore(query, state)
        self.assertEqual(state["pilot_driver"], "max_verstappen")
        self.assertEqual(state["pilot_years"], [2026])
        self.assertEqual(state["pilot_metric"], "podium_rate")
        self.restore(dict(query, piloto="norris", anos="2025"), state)
        self.assertEqual(state["pilot_driver"], "norris")
        self.assertEqual(state["pilot_years"], [2025])


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
        self.assertGreaterEqual(int(app.metric[0].value), 43)
        columns = json.loads(app.dataframe[0].proto.columns)
        self.assertEqual(columns["Race"]["type_config"]["type"], "link")

    def test_mexico_debut_and_dynamic_cutoff_are_available_in_both_languages(self):
        for lang,prefix in [('pt','Dados até'),('en','Data through')]:
            at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
            at.query_params.update(tela='Pilotos',visao='perfil',piloto='ryo_hirakawa',anos='2026',lang=lang)
            at.run()
            self.assertFalse(at.exception)
            self.assertEqual(at.selectbox(key='pilot_driver').value,'ryo_hirakawa')
            self.assertGreaterEqual(int(at.metric[0].value),1)
            self.assertTrue(any(prefix in x.value for x in at.caption))

    def test_deep_link_opens_the_named_driver(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        app.query_params.update(tela="Pilotos", piloto="max_verstappen", visao="perfil", lang="en")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pilot_driver"], "max_verstappen")
        self.assertEqual(app.session_state["pilot_view"], "Perfil individual")
        self.assertGreaterEqual(int(app.metric[0].value), 67)

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
        self.assertGreaterEqual(int(at.metric[0].value), 18)


if __name__ == "__main__":
    unittest.main()
