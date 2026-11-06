"""Malformed presentation files retain explicit unavailable states and search fallback."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pitwall.dashboard import search, weekend_views
from pitwall.data.race_weekend import carregar_asset, RaceWeekendDadosErro
from pitwall.data import editorial_panels, tyre_strategies


class PresentationReaderTests(unittest.TestCase):
    def test_absent_optional_standings_snapshot_has_no_fabricated_source_path(self):
        from preparar_dashboard_race_weekend import _campeonato_pilotos_2026
        with tempfile.TemporaryDirectory() as tmp:
            state, sources = _campeonato_pilotos_2026(Path(tmp))
            self.assertFalse(state['disponivel'])
            self.assertEqual(state['classificacao'], [])
            self.assertIn('indisponível', state['motivo'])
            self.assertEqual(sources, [])

    def test_exporter_rejects_nonobject_catalogue_before_building_package(self):
        from exportar_dashboard import _ler_catalogo_visual
        for value in ([], None, "invalid", 42):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "dashboard_assets/circuit/catalogo_visual.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value))
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    _ler_catalogo_visual(tmp)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse((Path(tmp) / "distribuicao").exists())

    def test_championship_retains_valid_snapshot_when_weekend_reader_fails(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "app.py"), default_timeout=45)
        app.query_params.update(tela="Campeonato", temporada="2026", gp="18", lang="pt")
        with patch.object(weekend_views, "load_status", side_effect=ValueError("invalid fixture")):
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("estado da coleta" in w.value for w in app.warning))
        markup = "\n".join(m.value for m in app.markdown)
        self.assertIn("pw-standings-provenance", markup)
        self.assertIn("Max Verstappen", markup)

    def test_performance_retains_valid_scores_when_weekend_reader_fails(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "app.py"), default_timeout=45)
        app.query_params.update(tela="Desempenho", temporada="2026", gp="19", lang="pt")
        with patch.object(weekend_views, "observed_rounds", side_effect=ValueError("invalid fixture")):
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("estado da coleta" in w.value for w in app.warning))
        self.assertIn("fan-results", "\n".join(m.value for m in app.markdown))

    def test_unknown_operational_status_is_not_an_awaited_race_claim(self):
        from pitwall.dashboard.fan_views import performance_cards
        rows = [dict(rodada=18, corrida="United States Grand Prix", modelo=2, classificacao=2)]
        races = [dict(rodada=18, corrida="United States Grand Prix", estado_previsao="previsao_registrada"),
                 dict(rodada=19, corrida="Mexico City Grand Prix", estado_previsao="previsao_registrada")]
        html = performance_cards(rows, races, 2026, operation_available=False)
        self.assertIn("Estado do resultado indisponível", html)
        self.assertNotIn("Corrida aguardada", html)


    def test_invalid_strategy_roots_return_unavailable(self):
        contexts = {(2025, 1): dict(circuito_id="fixture", data="2025-03-16")}
        for value in ([], None, "invalid", 42):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / tyre_strategies.ASSET
                path.parent.mkdir()
                path.write_text(json.dumps(value))
                with patch.object(tyre_strategies, "carregar_contextos", return_value=contexts):
                    result = tyre_strategies.carregar_estrategia(tmp, 2025, 1, "fixture")
                self.assertFalse(result["disponivel"])
                self.assertEqual(result["paradas"], [])
                self.assertIn("indisponíveis", result["motivo"])

    def test_invalid_standings_row_raises_domain_error(self):
        for row in (None, [], "invalid", 42):
            with self.subTest(row=row), self.assertRaises(editorial_panels.PaineisDadosErro):
                editorial_panels._validar_classificacao([row], "driver_standings", 1)

    def test_invalid_race_weekend_roots_raise_domain_error(self):
        for value in ([], None, "invalid", 42):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "frontend_assets/race_weekend.json"
                path.parent.mkdir()
                path.write_text(json.dumps(value))
                with self.assertRaises(RaceWeekendDadosErro):
                    carregar_asset(tmp)

    def test_search_keeps_driver_results_when_editorial_context_is_malformed(self):
        asset = dict(resultados=[dict(driver_id="fixture", driver_name="Fixture Driver",
                                     team_id="fixture_team", race_id="2025:1")],
                     gps={"2025:1": dict(temporada=2025, rodada=1)})
        for value in ([], None, {"eventos": None}, {"eventos": [None]},
                      {"eventos": [dict(corrida="Fixture")]}):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "frontend_assets/contexto_editorial.json"
                path.parent.mkdir()
                path.write_text(json.dumps(value))
                with patch.object(search, "load", return_value=asset):
                    results = search.search(tmp, "Fixture", year=2024, round_=1)
                driver = next(r for r in results if r["kind"] == "driver")
                self.assertEqual(driver["label"], "Fixture Driver")
                self.assertIn("temporada=2024", driver["href"])
                self.assertFalse(any(r["kind"] == "gp" for r in results))

    def test_weekend_readers_reject_malformed_event_archive(self):
        base = dict(schema="pitwall-weekend-public-v1", temporada=2026, rodada=19,
                    circuito_id="rodriguez", atualizado_em_utc="2026-11-01T23:00:00Z",
                    sessoes=[])
        for value in ([], dict(base, arquivo_eventos=[None]),
                      dict(base, arquivo_eventos={}), dict(base, arquivo_eventos=[{}])):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "frontend_assets/operacao_fim_semana.json"
                path.parent.mkdir()
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    weekend_views.load_status(tmp, 2026, 18, "americas")
                with self.assertRaises(ValueError):
                    weekend_views.observed_rounds(tmp, 2026)


if __name__ == "__main__":
    unittest.main()
