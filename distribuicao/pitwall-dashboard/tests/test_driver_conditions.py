from copy import deepcopy
import unittest

from pitwall.data.driver_conditions import DriverConditionsError, SCHEMA, content_hash, validate
from pitwall.research.driver_conditions import BY_KEY, leaders, ranking, summarize, teammate_comparison


def result(driver, position, race="2024:1", **kwargs):
    return {"race_id": race, "driver_id": driver, "driver_name": driver, "team_id": "team",
            "started": True, "disqualified": False, "retired": False, "position": position, "grid": 1, **kwargs}


def dataset(rows):
    gps = {}
    for row in rows:
        year, round_ = map(int, row["race_id"].split(":"))
        gps[row["race_id"]] = {"temporada": year, "rodada": round_, "session_name": "Race",
            "rain_condition": "recorded", "direction": "horario", "track_temperature": 0,
            "air_temperature": 20, "humidity": 80, "pressure": 1000, "wind_speed": 3,
            "altitude_m": 100, "corners": 14}
    asset = {"schema": SCHEMA, "gps": gps, "resultados": rows, "qualidade": {
        "gate_pilotos": True, "pendencias_obrigatorias_sem_tratamento": 0, "corridas": len(gps),
        "resultados": len(rows), "largadas": sum(x["started"] for x in rows)}}
    asset["conteudo_sha256"] = content_hash(asset)
    return asset


def rehash(asset):
    asset["conteudo_sha256"] = content_hash({k: v for k, v in asset.items() if k != "conteudo_sha256"})


class DriverConditionsTests(unittest.TestCase):
    def test_dns_excluded_but_zero_lap_retirement_and_dsq_are_opportunities(self):
        rows = [result("a", 1), result("b", 2, started=False), result("c", 3, retired=True),
                result("d", 1, disqualified=True)]
        stats = summarize(rows)
        self.assertEqual(stats["starts"], 3)
        self.assertEqual(stats["wins"], 1)
        self.assertAlmostEqual(stats["win_rate"], 1 / 3)
        self.assertEqual(stats["dns"], 1)

    def test_more_wins_and_higher_rate_can_have_different_leaders(self):
        rows = [result("a", 1, "2024:" + str(i)) for i in range(1, 3)]
        rows += [result("a", 2, "2024:" + str(i)) for i in range(3, 5)]
        rows += [result("b", 1)]
        asset = dataset(rows)
        self.assertEqual(leaders(ranking(asset, "rain", "wins", 1))[0]["driver_id"], "a")
        self.assertEqual(leaders(ranking(asset, "rain", "win_rate", 1))[0]["driver_id"], "b")
        self.assertEqual(leaders(ranking(asset, "rain", "win_rate", 3))[0]["driver_id"], "a")

    def test_ties_are_retained_and_all_zero_does_not_create_a_winner(self):
        asset = dataset([result("a", 1), result("b", 1)])
        self.assertEqual(len(leaders(ranking(asset, "rain", minimum_starts=1))), 2)
        asset = dataset([result("a", 4), result("b", 5)])
        self.assertEqual(leaders(ranking(asset, "rain", minimum_starts=1)), [])

    def test_empty_sample_is_unknown_rate_not_zero(self):
        stats = summarize([result("a", 20, started=False)])
        self.assertIsNone(stats["win_rate"])
        self.assertIsNone(stats["win_interval"])

    def test_temperature_boundaries_and_zero_are_explicit(self):
        self.assertTrue(BY_KEY["track_cold"].includes({"track_temperature": 0}))
        self.assertFalse(BY_KEY["track_cold"].includes({"track_temperature": None}))
        self.assertTrue(BY_KEY["track_hot"].includes({"track_temperature": 40}))
        self.assertFalse(BY_KEY["track_mild"].includes({"track_temperature": 40}))

    def test_figure_eight_does_not_enter_binary_direction_groups(self):
        self.assertTrue(BY_KEY["figure_eight"].includes({"direction": "misto_oito"}))
        self.assertFalse(BY_KEY["cw"].includes({"direction": "misto_oito"}))
        self.assertFalse(BY_KEY["ccw"].includes({"direction": "misto_oito"}))

    def test_teammate_requires_same_race_team_and_valid_starts(self):
        asset = dataset([result("a", 1), result("b", 2),
            result("a", 3, "2024:2"), result("b", 1, "2024:2", team_id="other"),
            result("a", 1, "2024:3"), result("b", 2, "2024:3", started=False)])
        value = teammate_comparison(asset, "a")
        self.assertEqual(value["comparable"], 1)
        self.assertEqual(value["ahead"], 1)

    def test_scientific_inputs_not_mutated_by_comparisons(self):
        asset = dataset([result("a", 1), result("b", 2)])
        before = deepcopy(asset)
        ranking(asset, "rain", minimum_starts=1)
        teammate_comparison(asset, "a")
        self.assertEqual(asset, before)

    def test_semantic_validation_still_applies_after_rehash(self):
        mutations = [lambda a: a["gps"]["2024:1"].update(session_name="Sprint"),
                     lambda a: a["resultados"][0].update(started="False"),
                     lambda a: a["resultados"].append(dict(a["resultados"][0]))]
        for mutate in mutations:
            asset = dataset([result("a", 1)])
            mutate(asset); rehash(asset)
            with self.assertRaises(DriverConditionsError):
                validate(asset)

    def test_hash_detects_edited_condition(self):
        asset = dataset([result("a", 1)])
        asset["gps"]["2024:1"]["track_temperature"] = 50
        with self.assertRaises(DriverConditionsError):
            validate(asset)


if __name__ == "__main__":
    unittest.main()
