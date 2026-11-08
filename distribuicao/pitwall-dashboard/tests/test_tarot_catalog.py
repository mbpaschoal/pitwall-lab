"""Tarot assets never choose favorites or borrow a driver's later team."""
import copy
import csv
import hashlib
import itertools
import json
import struct
from pathlib import Path
import tempfile
import unittest

from pitwall.dashboard.tarot import cards_html
from pitwall.dashboard.tarot_catalog import (
    CATALOG_PATH, POSE_KEYS, TarotCatalogError, artwork_for, coverage,
    load_catalog, read_artwork, select_cards, team_id,
)
from pitwall.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]
LAST_BASELINE_EVENT = (2026, 19)
ORIGINALS = {
    "verstappen.png": "893f1206e878a4bd30751df4f7d83a0a779a6d6d5445e5dd6e0e77b602d8a3a9",
    "hamilton.png": "509138de884b2ce4bb64c1f2ef898fb6661f456467b9f2af64821a32a67e894d",
    "russell.png": "eb5db2342b4be6014f9d1ec58308ffd105baf2a84253e9d42439dfeedf3c7933",
}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = dict(schema_version=2, cards=[], overrides=[], team_cards=[])
        self.rows = [dict(driver_id=d, name=d.title(), team="Mercedes", probability=p)
                     for d, p in (("hamilton", .6), ("russell", .6), ("antonelli", .4))]
        for row in self.rows:
            for pose, key in enumerate(POSE_KEYS):
                path = "dashboard_assets/tarot/variants/{}/pose-{}.png".format(row["driver_id"], pose)
                # Deliberately tiny synthetic payloads exercise identity and integrity.
                content = b"\x89PNG\r\n\x1a\n" + path.encode()
                target = self.root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                self.catalog["cards"].append(dict(driver_id=row["driver_id"], pose_id=pose,
                    pose_key=key, team_neutral=True, status="ready", path=path,
                    sha256=hashlib.sha256(content).hexdigest()))
            self.add_team_cards(row["driver_id"], "mercedes", [2024, 2025, 2026])
        self.save()

    def add_team_cards(self, driver, team, years):
        for pose, key in enumerate(POSE_KEYS):
            path = "dashboard_assets/tarot/teams/{}/{}/pose-{}.png".format(team, driver, pose)
            content = b"\x89PNG\r\n\x1a\n" + path.encode()
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            self.catalog["team_cards"].append(dict(driver_id=driver, team_id=team,
                years=list(years), pose_id=pose, pose_key=key, team_neutral=False,
                status="ready", path=path, sha256=hashlib.sha256(content).hexdigest()))

    def save(self):
        (self.root / CATALOG_PATH).write_text(json.dumps(self.catalog))

    def test_every_gp_has_distinct_poses_without_changing_rows_or_probabilities(self):
        before = copy.deepcopy(self.rows)
        pose_compositions = set()
        for year in (2024, 2025, 2026):
            for round_ in range(1, 25):
                result = select_cards(self.rows, self.root, year, round_)
                self.assertEqual([item["row"] for item in result], before)
                self.assertEqual({item["pose_id"] for item in result}, {0, 1, 2})
                self.assertTrue(all(item["content"] for item in result))
                pose_compositions.add(tuple(item["pose_id"] for item in result))
                repeated = select_cards(self.rows, self.root, year, round_)
                self.assertEqual(result, repeated)
        self.assertEqual(self.rows, before)
        self.assertGreater(len(pose_compositions), 1)

    def test_reordering_a_trio_keeps_each_driver_pose(self):
        def assigned(rows):
            return {item["row"]["driver_id"]: item["pose_id"]
                    for item in select_cards(rows, self.root, 2026, 19)}
        expected = assigned(self.rows)
        for permutation in itertools.permutations(self.rows):
            self.assertEqual(assigned(list(permutation)), expected)

    def test_ties_retain_every_favorite_with_balanced_pose_cycles(self):
        rows = self.rows + [dict(driver_id="tie_{}".format(n), name="Tied favorite",
                                team="McLaren", probability=.4) for n in range(4)]
        result = select_cards(rows, self.root, 2026, 19)
        self.assertEqual([item["row"] for item in result], rows)
        for start in (0, 3):
            self.assertEqual({item["pose_id"] for item in result[start:start + 3]}, {0, 1, 2})

    def test_team_art_matches_gp_team_and_year_without_neutral_fallback(self):
        self.add_team_cards("hamilton", "ferrari", [2025, 2026])
        self.save()
        load_catalog(self.root)
        mercedes = self.rows[0]
        ferrari = dict(mercedes, team="Ferrari")
        self.assertEqual(artwork_for(self.catalog, mercedes, 0, 2024)["team_id"], "mercedes")
        self.assertEqual(artwork_for(self.catalog, ferrari, 0, 2025)["team_id"], "ferrari")
        self.assertIsNone(artwork_for(self.catalog, ferrari, 0, 2024))
        contradictory = dict(mercedes, team_id="ferrari")
        self.assertIsNone(team_id(contradictory))
        self.assertIsNone(artwork_for(self.catalog, contradictory, 0, 2025))

    def test_missing_context_and_invalid_pose_never_select_an_illustration(self):
        for year in (None, True, "2026", 2023):
            self.assertIsNone(artwork_for(self.catalog, self.rows[0], 0, year))
        for pose in (True, 0.0, -1, 3, "0"):
            self.assertIsNone(artwork_for(self.catalog, self.rows[0], pose, 2026))
        for team in ("", "Unknown", "McLaren"):
            row = dict(self.rows[0], team=team)
            self.assertIsNone(artwork_for(self.catalog, row, 0, 2026))
        for explicit in ([], {}, True, "invented"):
            row = dict(self.rows[0], team_id=explicit)
            self.assertIsNone(team_id(row))
            self.assertIsNone(artwork_for(self.catalog, row, 0, 2026))
        self.assertEqual(team_id(dict(self.rows[0], team_id="")), "mercedes")

    def test_legacy_catalog_preserves_archive_but_does_not_render_it_as_team_art(self):
        self.catalog["schema_version"] = 1
        self.catalog.pop("team_cards")
        self.save()
        catalog = load_catalog(self.root)
        self.assertTrue(coverage(self.root, catalog)["neutral_archive"]["complete"])
        self.assertFalse(coverage(self.root, catalog)["complete"])
        self.assertTrue(all(item["content"] is None
                            for item in select_cards(self.rows, self.root, 2026, 19, catalog)))

    def test_planned_team_illustrations_are_not_counted_or_rendered_as_ready(self):
        for entry in self.catalog["team_cards"]:
            entry["status"] = "planned"
            entry["sha256"] = None
        self.save()
        catalog = load_catalog(self.root)
        audit = coverage(self.root, catalog)
        self.assertEqual(audit["ready"], 0)
        self.assertEqual(len(audit["missing"]), 9)
        self.assertTrue(audit["neutral_archive"]["complete"])
        self.assertTrue(all(item["content"] is None
                            for item in select_cards(self.rows, self.root, 2026, 19, catalog)))

    def test_corrupt_or_missing_png_is_explicit_not_a_generic_driver_image(self):
        for entry in self.catalog["team_cards"]:
            if entry["driver_id"] == "hamilton":
                (self.root / entry["path"]).write_bytes(b"corrupt")
        self.save()
        set_language("pt")
        html = cards_html(self.rows, self.root, 2024, 1)
        self.assertEqual(html.count("<img "), 2)
        self.assertIn("Ilustração indisponível", html)
        self.assertNotIn("<svg", html)
        self.assertNotIn("%", html)
        self.assertEqual(coverage(self.root)["ready"], 6)
        self.assertFalse(coverage(self.root)["complete"])
        self.assertTrue(coverage(self.root)["neutral_archive"]["complete"])

    def test_invalid_values_are_not_rendered_or_promoted(self):
        invalid = [dict(self.rows[0], probability=value) for value in
                   (None, False, float("nan"), float("inf"), -1, 1.01)]
        self.assertNotIn("<article", cards_html(invalid, self.root, 2026, 19))

    def test_catalog_rejects_paths_and_metadata_that_swap_drivers(self):
        for invalid_path in ("/tmp/escape.png", "dashboard_assets/tarot/../escape.png",
                             "dashboard_assets/tarot/variants/russell/pose-0.png"):
            with self.subTest(path=invalid_path):
                original = self.catalog["cards"][0]["path"]
                self.catalog["cards"][0]["path"] = invalid_path
                self.save()
                with self.assertRaises(TarotCatalogError):
                    load_catalog(self.root)
                self.catalog["cards"][0]["path"] = original

    def test_catalog_rejects_symlink_escape_and_duplicate_pose(self):
        entry = self.catalog["cards"][0]
        path = self.root / entry["path"]
        path.unlink()
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside")
        path.symlink_to(outside)
        with self.assertRaises(TarotCatalogError):
            load_catalog(self.root)
        path.unlink()
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.catalog["cards"].append(dict(entry))
        self.save()
        with self.assertRaises(TarotCatalogError):
            load_catalog(self.root)

    def test_team_catalog_rejects_invalid_year_team_path_hash_pose_and_duplicates(self):
        changes = (
            {"years": []}, {"years": [True]}, {"years": [2026.0]},
            {"years": [0]}, {"years": [2026, 2026]}, {"years": [2025]},
            {"team_id": "invented"}, {"team_id": []}, {"team_id": "ferrari"},
            {"pose_id": True}, {"pose_id": 3}, {"pose_key": "invented"},
            {"sha256": "not-a-hash"}, {"team_neutral": True},
            {"path": "dashboard_assets/tarot/teams/mercedes/russell/pose-0.png"},
            {"path": "dashboard_assets/tarot/teams/mercedes/hamilton/../../escape.png"},
        )
        original = copy.deepcopy(self.catalog)
        for change in changes:
            with self.subTest(change=change):
                self.catalog = copy.deepcopy(original)
                self.catalog["team_cards"][0].update(change)
                self.save()
                with self.assertRaises(TarotCatalogError):
                    load_catalog(self.root)
        self.catalog = copy.deepcopy(original)
        self.catalog["team_cards"].append(dict(self.catalog["team_cards"][0]))
        self.save()
        with self.assertRaises(TarotCatalogError):
            load_catalog(self.root)

    def test_invalid_approved_composition_cannot_change_pose_assignment(self):
        original = dict(year=2026, round=19,
                        driver_poses={"hamilton": 0, "russell": 2, "antonelli": 1})
        changes = ({"year": True}, {"year": 0}, {"round": False}, {"round": 0},
                   {"driver_poses": {"hamilton": False, "russell": 2, "antonelli": 1}},
                   {"driver_poses": {"invented": 0, "russell": 2, "antonelli": 1}},
                   {"driver_poses": {"hamilton": 0, "russell": 0, "antonelli": 1}})
        for change in changes:
            with self.subTest(change=change):
                self.catalog["approved_compositions"] = [dict(original, **change)]
                self.save()
                with self.assertRaises(TarotCatalogError):
                    load_catalog(self.root)

    def test_approved_original_has_priority_and_only_matching_team_art_can_replace_corrupt_bytes(self):
        path = "dashboard_assets/tarot/russell.png"
        data = (ROOT / path).read_bytes()
        (self.root / path).write_bytes(data)
        self.catalog["overrides"].append(dict(driver_id="russell", team_id="mercedes",
            years=[2024, 2025, 2026], pose_id=2, pose_key=POSE_KEYS[2],
            path=path, sha256=ORIGINALS["russell.png"], team_neutral=False, status="ready"))
        self.catalog["approved_compositions"] = [dict(year=2026, round=19,
            driver_poses={"hamilton": 0, "russell": 2, "antonelli": 1})]
        self.save()
        catalog = load_catalog(self.root)
        result = select_cards(self.rows, self.root, 2026, 19, catalog)
        russell = next(item for item in result if item["row"]["driver_id"] == "russell")
        self.assertEqual(russell["content"], data)
        self.assertEqual(russell["entry"]["path"], path)
        (self.root / path).write_bytes(b"corrupt")
        result = select_cards(self.rows, self.root, 2026, 19, catalog)
        russell = next(item for item in result if item["row"]["driver_id"] == "russell")
        self.assertEqual(russell["pose_id"], 2)
        self.assertEqual(russell["entry"]["path"],
            "dashboard_assets/tarot/teams/mercedes/russell/pose-2.png")
        self.assertFalse(russell["entry"]["team_neutral"])

    def test_catalog_audit_detects_copied_pose_artwork(self):
        first, second = self.catalog["team_cards"][:2]
        (self.root / second["path"]).write_bytes((self.root / first["path"]).read_bytes())
        second["sha256"] = first["sha256"]
        self.save()
        audit = coverage(self.root)
        self.assertEqual(audit["ready"], 9)
        self.assertFalse(audit["complete"])
        self.assertEqual(len(audit["duplicate_artworks"]), 1)

    def test_delivered_catalog_has_29_archived_drivers_and_126_verified_team_artworks(self):
        actual = load_catalog(ROOT)
        ids = {entry["driver_id"] for entry in actual["cards"]}
        self.assertEqual(len(ids), 29)
        self.assertEqual(len(actual["cards"]), 87)
        race_weekend = json.loads((ROOT / "frontend_assets/race_weekend.json").read_text())
        baseline_identities = []
        for key, identity in race_weekend["identidades"].items():
            year, round_, driver = key.split(":", 2)
            if (int(year), int(round_)) <= LAST_BASELINE_EVENT:
                baseline_identities.append((int(year), driver, identity))
        self.assertEqual(ids, {driver for _, driver, _ in baseline_identities})
        for driver in ids:
            self.assertEqual({entry["pose_id"] for entry in actual["cards"]
                              if entry["driver_id"] == driver}, {0, 1, 2})
        self.assertEqual(len(actual["team_cards"]), 126)
        for entry in actual["cards"] + actual["overrides"] + actual["team_cards"]:
            self.assertEqual(entry["status"], "ready", entry["path"])
            content = read_artwork(ROOT, entry)
            self.assertIsNotNone(content, entry["path"])
            self.assertEqual(struct.unpack(">II", content[16:24]), (1024, 1536), entry["path"])
        audit = coverage(ROOT, actual)
        self.assertEqual(audit["required"], 126)
        self.assertEqual(audit["ready"], 126)
        self.assertEqual(audit["missing"], [])
        self.assertEqual(audit["duplicate_artworks"], [])
        self.assertTrue(audit["complete"])
        self.assertEqual(audit["neutral_archive"]["ready"], 87)
        self.assertEqual(audit["approved_originals"]["ready"], 3)
        known_pairs = {}
        for year, driver, identity in baseline_identities:
            team = team_id(dict(team=identity["equipe"]))
            if team:
                known_pairs.setdefault((driver, team), set()).add(year)
        actual_pairs = {(entry["driver_id"], entry["team_id"]) for entry in actual["team_cards"]}
        self.assertEqual(actual_pairs, set(known_pairs))
        for entry in actual["team_cards"]:
            self.assertEqual(set(entry["years"]), known_pairs[entry["driver_id"], entry["team_id"]])

    def test_norris_has_three_mclaren_illustrations_for_each_supported_year(self):
        actual = load_catalog(ROOT)
        row = dict(driver_id="norris", name="Lando Norris", team="McLaren", probability=.5)
        for year in (2024, 2025, 2026):
            for pose in (0, 1, 2):
                with self.subTest(year=year, pose=pose):
                    entry = artwork_for(actual, row, pose, year)
                    self.assertIsNotNone(entry)
                    self.assertFalse(entry["team_neutral"])
                    self.assertEqual(entry["team_id"], "mclaren")
                    self.assertIn("/teams/mclaren/norris/", entry["path"])
                    self.assertIsNotNone(read_artwork(ROOT, entry))

    def test_mexico_keeps_the_three_approved_originals_after_all_87_variants_arrive(self):
        catalog = load_catalog(ROOT)
        asset = json.loads((ROOT / "frontend_assets/race_weekend.json").read_text())
        favorites = sorted((row for row in asset["dados_2026"]["previsoes"]
                            if row["rodada"] == 19 and row.get("ranking_modelo") in (1, 2, 3)),
                           key=lambda row: row["ranking_modelo"])
        rows = []
        for favorite in favorites:
            identity = asset["identidades"]["2026:19:" + favorite["piloto_id"]]
            rows.append(dict(driver_id=favorite["piloto_id"], name=identity["piloto"],
                             team=identity["equipe"], probability=favorite["probabilidade_modelo"]))
        expected = {"max_verstappen": (0, "verstappen.png"),
                    "hamilton": (1, "hamilton.png"), "russell": (2, "russell.png")}
        self.assertEqual({row["driver_id"] for row in rows}, set(expected))
        self.assertTrue(coverage(ROOT, catalog)["complete"])
        for order in itertools.permutations(rows):
            with self.subTest(order=[row["driver_id"] for row in order]):
                selected = select_cards(list(order), ROOT, 2026, 19, catalog)
                self.assertEqual([card["row"] for card in selected], list(order))
                for card in selected:
                    pose, filename = expected[card["row"]["driver_id"]]
                    self.assertEqual(card["pose_id"], pose)
                    self.assertEqual(card["entry"]["path"], "dashboard_assets/tarot/" + filename)
                    self.assertFalse(card["entry"]["team_neutral"])
                    self.assertEqual(hashlib.sha256(card["content"]).hexdigest(), ORIGINALS[filename])

    def test_gp_favorite_groups_have_three_poses_and_correct_historical_teams(self):
        asset = json.loads((ROOT / "frontend_assets/race_weekend.json").read_text())
        catalog = load_catalog(ROOT)
        groups = {}
        sources = ((2024, "reports/modelo_v1/previsoes_validacao.csv"),
                   (2025, "reports/avaliacao_final_v1/previsoes_pre_corrida.csv"))
        for year, path in sources:
            with (ROOT / path).open() as source:
                for row in csv.DictReader(source):
                    if row["favorito_modelo"] == "1":
                        groups.setdefault((year, int(row["rodada"])), []).append(row)
        for row in asset["dados_2026"]["previsoes"]:
            if row.get("ranking_modelo") in (1, 2, 3):
                groups.setdefault((2026, row["rodada"]), []).append(row)
        self.assertEqual(sum(event <= LAST_BASELINE_EVENT for event in groups), 67)
        saw_hamilton_mercedes = False
        for (year, round_), favorites in sorted(groups.items()):
            with self.subTest(year=year, round=round_):
                rows = []
                for favorite in sorted(favorites, key=lambda row: int(row["ranking_modelo"])):
                    driver = favorite["piloto_id"]
                    identity = asset["identidades"]["{}:{}:{}".format(year, round_, driver)]
                    rows.append(dict(driver_id=driver, name=identity["piloto"],
                                     team=identity["equipe"],
                                     probability=float(favorite["probabilidade_modelo"])))
                selected = select_cards(rows, ROOT, year, round_, catalog)
                self.assertEqual([card["row"] for card in selected], rows)
                self.assertEqual({card["pose_id"] for card in selected[:3]}, {0, 1, 2})
                for card in selected:
                    if ((year, round_) > LAST_BASELINE_EVENT
                            and artwork_for(catalog, card["row"], card["pose_id"], year) is None):
                        # A new driver or team can enter an emission before its artwork exists.
                        self.assertIsNone(card["entry"])
                        self.assertIsNone(card["content"])
                        continue
                    self.assertIsNotNone(card["content"])
                    self.assertEqual(card["entry"]["driver_id"], card["row"]["driver_id"])
                    if not card["entry"]["team_neutral"]:
                        self.assertEqual(card["entry"]["team_id"], team_id(card["row"]))
                        self.assertIn(year, card["entry"]["years"])
                    if year == 2024 and card["row"]["driver_id"] == "hamilton":
                        saw_hamilton_mercedes = True
                        self.assertEqual(team_id(card["row"]), "mercedes")
                        self.assertFalse(card["entry"]["team_neutral"])
                        self.assertIn("/teams/mercedes/hamilton/", card["entry"]["path"])
        self.assertTrue(saw_hamilton_mercedes)

    def test_approved_original_artworks_are_preserved_byte_for_byte(self):
        for filename, expected in ORIGINALS.items():
            self.assertEqual(hashlib.sha256((ROOT / "dashboard_assets/tarot" / filename).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
