"""Published snapshot invariants: actual race scope and reversible projection."""
import json
from pathlib import Path
import unittest

from pitwall.data.driver_archive_projection import circuit_panels, supplement
from pitwall.data.driver_conditions import load
from pitwall.research.driver_conditions import select_rows, summarize

ROOT = Path(__file__).resolve().parents[1]


class DriverProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drivers = load(ROOT)

    def test_published_scope_uses_actual_races_and_starts(self):
        stats = summarize(select_rows(self.drivers))
        self.assertEqual((stats["starts"], stats["dns"], stats["wins"], stats["podiums"]), (1340, 14, 66, 198))
        self.assertEqual(sum(g["rain_condition"] == "recorded" for g in self.drivers["gps"].values()), 8)
        self.assertTrue(all(g["session_name"] == "Race" for g in self.drivers["gps"].values()))

    def test_archive_projection_is_idempotent_and_preserves_source_flags(self):
        original = json.loads((ROOT / "frontend_assets/acervo_dashboard.json").read_text())
        projected, counts = supplement(original, self.drivers)
        self.assertEqual(projected, original)
        self.assertEqual(counts["corridas_clima_efetivo"], 66)
        self.assertTrue(any(e.get("qualidade_fonte_original") for gp in projected["gps"].values() for e in gp["estrategias"]))

    def test_edition_lengths_and_figure_eight_survive_projection(self):
        original = json.loads((ROOT / "frontend_assets/paineis_editoriais.json").read_text())
        projected = circuit_panels(original, self.drivers, "2026-10-29")
        self.assertEqual(projected, original)
        circuits = projected["circuitos"]
        self.assertEqual(circuits["red_bull_ring"]["por_temporada"]["2024"]["comprimento_km"], 4.318)
        self.assertEqual(circuits["red_bull_ring"]["por_temporada"]["2025"]["comprimento_km"], 4.326)
        self.assertEqual(circuits["suzuka"]["por_temporada"]["2024"]["sentido"], "Misto (traçado em oito)")


if __name__ == "__main__":
    unittest.main()
