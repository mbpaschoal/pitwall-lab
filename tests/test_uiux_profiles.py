"""Accessible profile numbers, scoped favourites, and localised date labels."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from streamlit.testing.v1 import AppTest

from pitwall.dashboard import pilot_views
from pitwall.i18n import set_language


ROOT = Path(__file__).resolve().parents[1]


class DuelDifferenceTests(unittest.TestCase):
    def tearDown(self):
        set_language("pt")

    def test_rate_difference_is_percentage_points_and_never_the_finish_score(self):
        result = dict(common_starts=10, left={"win_rate": .3}, right={"win_rate": .1},
                      left_ahead=1, right_ahead=9)
        original = deepcopy(result)
        for lang, amount in [("pt", "20,0 pontos percentuais"), ("en", "20.0 percentage points")]:
            set_language(lang)
            html = pilot_views._duel_difference_html(result, "Driver A", "Driver B", "win_rate", 5)
            self.assertIn('data-state="left"', html)
            self.assertIn(amount, html)
            self.assertIn("Driver A", html)
        self.assertEqual(result, original)

    def test_zero_is_a_tie_and_insufficient_sample_does_not_publish_a_difference(self):
        result = dict(common_starts=3, left={"wins": 0}, right={"wins": 0})
        set_language("en")
        hidden = pilot_views._duel_difference_html(result, "A", "B", "wins", 5)
        self.assertIn('data-state="insufficient"', hidden)
        self.assertIn("Sample below the selected minimum.", hidden)
        self.assertNotIn("Tied", hidden)
        shown = pilot_views._duel_difference_html(result, "A", "B", "wins", 3)
        self.assertIn('data-state="tied"', shown)
        self.assertIn("Tied on this metric.", shown)

    def test_count_difference_is_integer_and_missing_value_is_not_zero(self):
        result = dict(common_starts=10, left={"podiums": 2}, right={"podiums": 5})
        set_language("en")
        html = pilot_views._duel_difference_html(result, "<Driver A>", "<Driver B>", "podiums", 5)
        self.assertIn('data-state="right"', html)
        self.assertIn("&lt;Driver B&gt; has 3 more on this metric.", html)
        self.assertNotIn("percentage", html)
        result["right"]["podiums"] = None
        self.assertIn('data-state="insufficient"', pilot_views._duel_difference_html(
            result, "A", "B", "podiums", 5))


class AccessibleProfileValuesTests(unittest.TestCase):
    def setUp(self):
        set_language("pt")

    def tearDown(self):
        set_language("pt")

    def test_all_series_keep_denominators_and_distinguish_zero_from_small_sample(self):
        comparisons = [
            {"condition": "rain", "driver": {"starts": 8, "win_rate": .375},
             "reference": {"starts": 24, "win_rate": .125}},
            {"condition": "track_hot", "driver": {"starts": 2, "win_rate": 1},
             "reference": {"starts": 9, "win_rate": 0}},
        ]
        before = deepcopy(comparisons)
        series = [("driver", "Norris <driver>", "#102b50"),
                  ("reference", "Demais pilotos (taxa conjunta)", "#7fa4ca")]
        table = ElementTree.fromstring(pilot_views._condition_values_html(
            comparisons, series, "win_rate", 5))
        rows = [["".join(cell.itertext()) for cell in row]
                for row in table.findall("./tbody/tr")]
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], ["Chuva", "Norris <driver>", "37,5%", "8"])
        self.assertEqual(rows[1][-2:], ["12,5%", "24"])
        self.assertEqual(rows[2][-2:], ["—", "2"])
        self.assertEqual(rows[3][-2:], ["0,0%", "9"])
        self.assertTrue(all(row[0].get("scope") == "row" for row in table.findall("./tbody/tr")))
        self.assertTrue(all(cell.get("scope") == "col" for cell in table.findall("./thead/tr/th")))
        self.assertEqual(comparisons, before)

    def test_english_count_table_keeps_exact_counts_and_omits_unplotted_reference(self):
        set_language("en")
        html = pilot_views._condition_values_html(
            [{"condition": "rain", "driver": {"starts": 8, "wins": 3}}],
            [("driver", "Lando Norris", "#102b50")], "wins", 5)
        table = ElementTree.fromstring(html)
        self.assertEqual(table.findtext("caption"), "Values and sample sizes by condition")
        self.assertEqual(["".join(c.itertext()) for c in table.findall("./thead/tr/th")],
                         ["Condition", "Group", "Wins", "Starts (N)"])
        self.assertEqual(["".join(c.itertext()) for c in table.findall("./tbody/tr/*")],
                         ["Rain", "Lando Norris", "3", "8"])

    def test_published_profile_table_agrees_with_each_plotted_series(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
        app.query_params.update(tela="Pilotos", visao="perfil", piloto="norris",
                                anos="2024,2025,2026", minimo="5", lang="pt")
        app.run()
        self.assertFalse(app.exception)
        html = next(x.value for x in app.markdown if 'class="pilot-condition-values"' in x.value)
        rows = [["".join(c.itertext()) for c in row]
                for row in ElementTree.fromstring(html).findall("./tbody/tr")]
        chart = json.loads(app.get("plotly_chart")[0].proto.spec)
        expected = {}
        for trace in chart["data"]:
            for condition, value, n in zip(trace["y"], trace["x"], trace["customdata"]):
                expected[(condition, trace["name"])] = (value, n)
        self.assertEqual(len(rows), len(expected))
        for condition, group, value, n in rows:
            score, denominator = expected[(condition, group)]
            self.assertEqual(int(n), denominator)
            if score is None:
                self.assertEqual(value, "—")
            else:
                self.assertAlmostEqual(float(value.rstrip("%").replace(",", ".")),
                                       score * 100, delta=.051)


class ProfileInteractionTests(unittest.TestCase):
    def test_forecast_origin_survives_favourite_filters_and_a_fresh_shared_link(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
        origin = dict(temporada="2026", gp="18", origem_tela="Previsões",
                      origem_temporada="2026", origem_gp="18")
        app.query_params.update(tela="Pilotos", visao="perfil", piloto="norris", anos="2026",
                                metrica="podium_rate", minimo="3", lang="pt", **origin)
        app.run()
        app.multiselect(key="pilot_years").set_value([2025]).run()
        app.session_state["browser_favorite"] = "hamilton"
        app.run()
        next(b for b in app.button if b.label == "Ver meu favorito").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.multiselect(key="pilot_years").value, [2025])
        for key, value in origin.items():
            self.assertEqual(app.query_params.get(key),value)
        fresh = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
        fresh.query_params.update(**app.query_params)
        fresh.run()
        self.assertFalse(fresh.exception)
        self.assertEqual(fresh.selectbox(key="pilot_driver").value, "hamilton")
        self.assertEqual(fresh.multiselect(key="pilot_years").value, [2025])
        self.assertEqual(fresh.selectbox(key="temporada").value, 2026)
        self.assertEqual(fresh.selectbox(key="gp").value, "2026:18")
        self.assertTrue(any("Voltar às chances" in item.value for item in fresh.markdown))

    def test_origin_requires_matching_supported_context(self):
        valid = dict(temporada="2026", gp="18", origem_tela="Previsões",
                     origem_temporada="2026", origem_gp="18")
        self.assertEqual(pilot_views._forecast_origin_params(valid), valid)
        for change in ({"origem_tela": "Corridas"}, {"temporada": "2025"},
                       {"gp": "19"}, {"gp": "0", "origem_gp": "0"},
                       {"gp": "25", "origem_gp": "25"},
                       {"gp": "018", "origem_gp": "018"},
                       {"temporada": "2023", "origem_temporada": "2023"}):
            self.assertEqual(pilot_views._forecast_origin_params(dict(valid, **change)), {})

    def test_opening_saved_favourite_retains_shared_criteria(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
        app.query_params.update(tela="Pilotos", visao="perfil", piloto="norris", anos="2026",
                                metrica="podium_rate", minimo="3", lang="pt")
        app.run()
        app.session_state["browser_favorite"] = "hamilton"
        app.run()
        self.assertEqual(app.selectbox(key="pilot_driver").value, "norris")
        next(b for b in app.button if b.label == "Ver meu favorito").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="pilot_driver").value, "hamilton")
        self.assertEqual(app.multiselect(key="pilot_years").value, [2026])
        self.assertEqual(app.selectbox(key="pilot_metric").value, "podium_rate")
        self.assertEqual(app.selectbox(key="pilot_minimum").value, 3)
        self.assertEqual(app.query_params.get("piloto"),"hamilton")

    def test_duel_explanation_distinguishes_shared_starts_from_teammates(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40)
        app.query_params.update(tela="Pilotos", visao="duelo", piloto="norris",
                                rival="max_verstappen", anos="2024,2025,2026", lang="pt")
        app.run()
        self.assertFalse(app.exception)
        text = "\n".join(x.value for x in app.markdown)
        self.assertIn("No Duelo, os dois pilotos podem pertencer a equipes diferentes.", text)
        self.assertIn("Na comparação com o companheiro", text)
        self.assertNotIn("O confronto exige dois pilotos da mesma equipe", text)


class ProfileDateLabelsTests(unittest.TestCase):
    def tearDown(self):
        set_language("pt")

    def test_date_labels_do_not_depend_on_browser_locale_or_change_date(self):
        for selected, expected in (("pt", "9 ago 2026"), ("en", "9 Aug 2026")):
            set_language(selected)
            self.assertEqual(pilot_views._appearance_date_label("2026-08-09T23:00:00Z"), expected)
        self.assertEqual(pilot_views._appearance_date_label("not-a-date"), "not-a-date")

    def test_timeline_keeps_original_dates_positions_and_missing_values(self):
        asset = {"gps": {
            "2026:1": {"temporada": 2026, "rodada": 1, "name": "A", "date_utc": "2026-08-09T23:00:00Z"},
            "2026:2": {"temporada": 2026, "rodada": 2, "name": "B", "date_utc": "2026-09-06T18:00:00Z"},
            "2026:3": {"temporada": 2026, "rodada": 3, "name": "C", "date_utc": "2026-10-25T19:00:00Z"},
        }}
        rows = [
            {"race_id": "2026:1", "position": 2, "started": True, "disqualified": False},
            {"race_id": "2026:2", "position": 3, "started": True, "disqualified": True},
            {"race_id": "2026:3", "position": None, "started": False, "disqualified": False},
        ]
        before = deepcopy((asset, rows))
        set_language("pt")
        with patch.object(pilot_views, "_figure") as draw, patch.object(pilot_views, "st"):
            pilot_views._form(asset, rows)
        figure = draw.call_args[0][0]
        dates = [asset["gps"][row["race_id"]]["date_utc"] for row in rows]
        self.assertEqual(list(figure.data[0].x), dates)
        self.assertEqual(list(figure.data[0].y), [2, None, None])
        self.assertEqual(list(figure.layout.xaxis.tickvals), dates)
        self.assertEqual(list(figure.layout.xaxis.ticktext), ["9 ago 2026", "6 set 2026", "25 out 2026"])
        self.assertIn("9 ago 2026", figure.data[0].text[0])
        self.assertEqual((asset, rows), before)


if __name__ == "__main__":
    unittest.main()
