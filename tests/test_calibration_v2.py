"""Synthetic, independent oracles for the isolated temporal v2 experiment.

No test loads the historical data, the frozen v1 object, or an issued forecast.
Exact binomial counts identify calibration parameters; metamorphic changes to
future rows expose leakage that a snapshot of fitted coefficients would miss.
"""

import copy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression

from pitwall.research import calibration_v2 as experiment
from pitwall.research import run_calibration_v2 as runner


# This list is a test oracle copied from the frozen documented contract rather
# than imported from the implementation whose allowlist is under test.
FEATURES = (
    "posicao_classificacao", "posicao_classificacao_repetida",
    "classificacao_ausente", "posicao_classificacao_ausente",
    "media_posicao_final_5", "taxa_podios_5", "n_posicoes_5", "n_podios_5",
    "media_pontos_equipe_5", "n_corridas_equipe_5", "n_participacoes_equipe_5",
    "historico_piloto_insuficiente", "historico_equipe_insuficiente",
    "equipe_pre_corrida_ausente", "referencia_temporal_ausente",
)
REDUCED = (
    "posicao_classificacao", "posicao_classificacao_repetida",
    "media_posicao_final_5", "taxa_podios_5", "media_pontos_equipe_5",
    "n_posicoes_5",
)
METHODS = {
    "v1_temporal", "q_probability", "v2_uncalibrated",
    "v2_intercept_calibrated", "v2_sigmoid_calibrated",
}


def _rows(seasons=(2021, 2022)):
    """Twelve warm-up-year GPs and four test GPs; eight drivers per GP.

    Each GP has three positives with occasional upsets. Missing historical
    values and duplicate denominators are deliberate. Features do not depend
    on the targets generated below.
    """
    rng = np.random.RandomState(431)
    rows = []
    for year in seasons:
        for race in range(1, 13 if year == 2021 else 5):
            reference = datetime(year, 3, 1, 15, tzinfo=timezone.utc) + timedelta(days=14 * (race - 1))
            strengths = np.arange(8) + rng.normal(0, 0.35, 8)
            podium = set(np.argsort(strengths + rng.normal(0, 1.6, 8))[:3])
            for driver in range(8):
                n = min(5, race - 1)
                row = dict.fromkeys(FEATURES, 0.0)
                row.update({
                    "temporada": year, "rodada": race,
                    "piloto_id": "driver_{}".format(driver),
                    "limite_inferior_referencia_utc": reference.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data_corrida": (reference + timedelta(days=1)).date().isoformat(),
                    "posicao_classificacao": float(driver + 1),
                    "media_posicao_final_5": None if race == 1 else float(driver + 1) + rng.uniform(-0.4, 0.4),
                    "taxa_podios_5": None if race == 1 else float(rng.uniform(0.1, 0.9)),
                    "media_pontos_equipe_5": None if race == 1 else float(rng.uniform(0, 20)),
                    "n_posicoes_5": n, "n_podios_5": n,
                    "n_corridas_equipe_5": n, "n_participacoes_equipe_5": 2 * n,
                    "historico_piloto_insuficiente": int(n < 5),
                    "historico_equipe_insuficiente": int(n < 5),
                    "podio": int(driver in podium),
                })
                rows.append(row)
    return rows


def _raw(rows, features):
    return np.asarray([
        [np.nan if row[name] is None else row[name] for name in features]
        for row in rows
    ], dtype=float)


def _preprocess(raw):
    """Independent training median / population-variance oracle."""
    medians = np.array([
        np.median(column[np.isfinite(column)]) if np.isfinite(column).any() else 0.0
        for column in raw.T
    ])
    filled = np.where(np.isnan(raw), medians, raw)
    means = filled.mean(axis=0)
    scales = filled.std(axis=0, ddof=0)
    scales = np.where(scales == 0, 1.0, scales)
    return (filled - means) / scales, medians, means, scales


def _key(row):
    return (int(row["temporada"]), int(row["rodada"]), row["piloto_id"])


def _exact_calibration():
    rates = np.repeat([0.25, 0.5, 0.75], 4)
    outcomes = np.array([1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0])
    return rates, outcomes


def _predictions_for_year(result, year):
    return {
        (row["metodo"], _key(row)): (
            row["probabilidade"], row["ranking_modelo"], row["status"],
        )
        for row in result["predictions"] if int(row["temporada"]) == year
    }


def _fits_for_year(result, year):
    return [row for row in result["fit_records"] if int(row["outer_fold"]) == year]


def _calibrations_for_year(result, year):
    return [row for row in result["calibration_records"] if int(row["outer_fold"]) == year]


def _trained_parameters(result, year):
    # Prediction-partition hashes should change when its features change;
    # learned parameters and their training provenance must stay identical.
    return [
        {name: value for name, value in record.items() if name != "predict_partition"}
        for record in _fits_for_year(result, year)
    ]


def _partition_hash(partition, source):
    """Recompute the published partition digest from original fixture rows."""
    indexed = {_key(row): row for row in source}
    payload = []
    for key in sorted(tuple(key) for key in partition["keys"]):
        original = indexed[key]
        record = {name: original[name] for name in partition["hash_fields"]}
        for name in FEATURES:
            if name in record and record[name] is not None:
                record[name] = float(record[name])
        payload.append(record)
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _write_dataset(root, rows=None):
    """A tiny prepared source with deliberate post-race decoy columns."""
    if rows is None:
        rows = _rows((2021, 2022, 2023, 2024, 2025))
    prepared = Path(root) / "data/preparado"
    prepared.mkdir(parents=True)
    schema = {
        "chaves": ["temporada", "rodada", "piloto_id"],
        "entradas": list(FEATURES),
        "auditoria_proibida_como_entrada": ["posicao_final", "grid_resultado", "pontos", "status"],
    }
    (prepared / "colunas.json").write_text(json.dumps(schema), encoding="utf-8")
    fields = schema["chaves"] + list(FEATURES) + [
        "podio", "limite_inferior_referencia_utc", "data_corrida", "corrida",
        "posicao_final", "grid_resultado", "pontos", "status",
    ]
    for filename, years in (
        ("treino.csv", {2021, 2022, 2023}),
        ("validacao.csv", {2024}),
        ("teste_final_reservado.csv", {2025}),
    ):
        with (prepared / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                if row["temporada"] in years:
                    writer.writerow(dict(row, posicao_final="OUTCOME_DECOY", grid_resultado=999, pontos=999, status="POST_RACE"))
    return prepared


class PreparedSourceContractTest(unittest.TestCase):
    def test_loader_preserves_unknown_targets_and_discards_post_race_decoys(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = _rows((2021, 2022, 2023, 2024, 2025))
            rows[0]["podio"] = None
            _write_dataset(directory, rows)
            observed = experiment.load_dataset(directory)
            self.assertEqual(len(observed), len(rows))
            unknown = next(row for row in observed if _key(row) == _key(rows[0]))
            self.assertIsNone(unknown["podio"])
            self.assertFalse(unknown["alvo_conhecido"])
            self.assertTrue(unknown["elegivel_previsao"])
            for row in observed:
                self.assertTrue(set(FEATURES).issubset(row))
                self.assertTrue({"posicao_final", "grid_resultado", "pontos", "status"}.isdisjoint(row))

    def test_loader_rejects_schema_that_admits_an_outcome_as_feature(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = _write_dataset(directory)
            schema = json.loads((prepared / "colunas.json").read_text(encoding="utf-8"))
            schema["entradas"].append("posicao_final")
            (prepared / "colunas.json").write_text(json.dumps(schema), encoding="utf-8")
            with self.assertRaises(ValueError):
                experiment.load_dataset(directory)

    def test_loader_rejects_duplicate_keys_and_wrong_season_in_source_split(self):
        for alteration in ("duplicate", "2026"):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                prepared = _write_dataset(directory)
                source = prepared / "treino.csv"
                lines = source.read_text(encoding="utf-8").splitlines()
                if alteration == "duplicate":
                    lines.append(lines[1])
                else:
                    lines[1] = "2026," + lines[1].split(",", 1)[1]
                source.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    experiment.load_dataset(directory)

    def test_loader_rejects_missing_or_duplicate_csv_headers(self):
        for alteration in ("missing", "duplicate"):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                prepared = _write_dataset(directory)
                source = prepared / "treino.csv"
                lines = source.read_text(encoding="utf-8").splitlines()
                if alteration == "missing":
                    lines[0] = lines[0].replace("media_posicao_final_5,", "")
                else:
                    lines[0] += ",media_posicao_final_5"
                source.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    experiment.load_dataset(directory)

    def test_loader_rejects_prepared_source_symlink_outside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            prepared = _write_dataset(root)
            source = prepared / "treino.csv"
            outside = Path(directory) / "outside.csv"
            source.rename(outside)
            source.symlink_to(outside)
            with self.assertRaises(ValueError):
                experiment.load_dataset(root)


class TrainingDesignOracleTest(unittest.TestCase):
    def test_training_medians_means_and_scales_match_independent_oracle(self):
        train = [row for row in _rows() if row["temporada"] == 2021]
        _, medians, means, scales = _preprocess(_raw(train, REDUCED))
        actual = experiment.prepare_design(train, REDUCED, reduce=True)
        np.testing.assert_allclose(actual["medians"], medians, atol=1e-12)
        np.testing.assert_allclose(actual["means"], means, atol=1e-12)
        np.testing.assert_allclose(actual["scales"], scales, atol=1e-12)
        self.assertEqual(actual["train_partition"]["sha256"], _partition_hash(
            actual["train_partition"], train,
        ))

    def test_exact_constants_and_dependencies_are_removed_in_allowlist_order(self):
        train = _rows()[:32]
        for i, row in enumerate(train):
            row.update({
                "posicao_classificacao": float(i + 1),
                "posicao_classificacao_repetida": 0.0,
                "media_posicao_final_5": float(2 * (i + 1)),
                "taxa_podios_5": float(i % 2),
                "media_pontos_equipe_5": float(3 * (i % 2)),
                "n_posicoes_5": 5.0,
            })
        actual = experiment.prepare_design(train, REDUCED, reduce=True)
        self.assertEqual(actual["features_selected"], [
            "posicao_classificacao", "taxa_podios_5",
        ])
        self.assertEqual(actual["rank_with_intercept"], 3)
        X, _, _, _ = _preprocess(_raw(train, REDUCED))
        selected = X[:, actual["selected_indices"]]
        self.assertEqual(np.linalg.matrix_rank(np.column_stack([np.ones(len(X)), selected])), 3)
        for left in range(selected.shape[1]):
            for right in range(left + 1, selected.shape[1]):
                self.assertFalse(np.array_equal(selected[:, left], selected[:, right]))

    def test_selection_mask_ignores_targets_and_input_row_order(self):
        train = [row for row in _rows() if row["temporada"] == 2021]
        before = experiment.prepare_design(train, REDUCED, reduce=True)
        changed = copy.deepcopy(train[::-1])
        for row in changed:
            row["podio"] = 1 - row["podio"]
        after = experiment.prepare_design(changed, REDUCED, reduce=True)
        self.assertEqual(before["features_selected"], after["features_selected"])
        self.assertEqual(before["selected_indices"], after["selected_indices"])
        self.assertEqual(before["dropped_features"], after["dropped_features"])
        np.testing.assert_allclose(before["medians"], after["medians"], atol=1e-12)

    def test_wholly_missing_training_column_stays_zero_and_is_removed(self):
        train = _rows()[:64]
        for row in train:
            row["media_posicao_final_5"] = None
        actual = experiment.prepare_design(train, REDUCED, reduce=True)
        index = list(REDUCED).index("media_posicao_final_5")
        self.assertEqual(actual["medians"][index], 0.0)
        self.assertNotIn("media_posicao_final_5", actual["features_selected"])

    def test_reduced_l2_predictions_match_independent_sklearn_fit(self):
        rows = _rows()
        train = [row for row in rows if row["temporada"] == 2021]
        test = [row for row in rows if row["temporada"] == 2022]
        actual = experiment.fit_design(train, REDUCED, reduce=True)
        X, medians, means, scales = _preprocess(_raw(train, REDUCED))
        indices = actual["selected_indices"]
        y = np.asarray([row["podio"] for row in train])
        oracle = LogisticRegression(C=1.0, solver="lbfgs", tol=1e-11, max_iter=4000).fit(X[:, indices], y)
        transformed = (np.where(np.isnan(_raw(test, REDUCED)), medians, _raw(test, REDUCED)) - means) / scales
        expected = oracle.predict_proba(transformed[:, indices])[:, 1]
        np.testing.assert_allclose(experiment.predict_design(actual, test), expected, atol=5e-6)
        np.testing.assert_allclose(actual["coef"], oracle.coef_[0], atol=3e-5)
        self.assertEqual(actual["fit_status"], "ok")

    def test_predicting_missing_extreme_future_rows_does_not_refit_transformers(self):
        rows = _rows()
        train = [row for row in rows if row["temporada"] == 2021]
        test = [row for row in rows if row["temporada"] == 2022]
        fit = experiment.fit_design(train, REDUCED, reduce=True)
        before = copy.deepcopy(fit)
        expected = experiment.predict_design(fit, test[:1])
        changed = copy.deepcopy(test)
        for i, row in enumerate(changed[1:]):
            row["media_pontos_equipe_5"] = None if i % 2 else 1e12
            row["media_posicao_final_5"] = None if i % 2 else -1e12
        observed = experiment.predict_design(fit, changed)
        self.assertEqual(observed[:1], expected)
        self.assertEqual(fit, before)


class TemporalExperimentOracleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _rows((2021, 2022, 2023, 2024, 2025))
        cls.result = experiment.run_experiment(cls.rows)

    def test_fixed_methods_and_all_outer_years_use_all_eligible_prior_training(self):
        self.assertEqual({row["metodo"] for row in self.result["predictions"]}, METHODS)
        configuration = self.result["configuration"]
        self.assertEqual(configuration["features_v1"], list(FEATURES))
        self.assertEqual(configuration["features_v2"], list(REDUCED))
        self.assertEqual(configuration["C"], 1.0)
        self.assertEqual(configuration["inner_warmup_gp"], 8)
        self.assertEqual(configuration["inner_block_gp"], 4)
        for year in range(2022, 2026):
            expected = {_key(row) for row in self.rows if row["temporada"] < year}
            outer = [record for record in _fits_for_year(self.result, year) if record["purpose"].startswith("outer_")]
            self.assertEqual({record["purpose"] for record in outer}, {"outer_v1", "outer_q", "outer_v2"})
            for record in outer:
                with self.subTest(year=year, purpose=record["purpose"]):
                    expected_features = {
                        "outer_v1": list(FEATURES), "outer_q": ["posicao_classificacao"],
                        "outer_v2": list(REDUCED),
                    }[record["purpose"]]
                    self.assertEqual(record["features_requested"], expected_features)
                    self.assertEqual({tuple(key) for key in record["train_partition"]["keys"]}, expected)
                    self.assertEqual(record["train_partition"]["sha256"], _partition_hash(record["train_partition"], self.rows))
                    self.assertTrue(all(key[0] == year for key in record["predict_partition"]["keys"]))
                    self.assertNotIn("podio", record["predict_partition"]["hash_fields"])

    def test_v1_and_qualifying_probability_comparators_match_independent_fixed_recipe(self):
        train = [row for row in self.rows if row["temporada"] == 2021]
        test = [row for row in self.rows if row["temporada"] == 2022]
        for method, features in (("v1_temporal", FEATURES), ("q_probability", ["posicao_classificacao"])):
            with self.subTest(method=method):
                X, medians, means, scales = _preprocess(_raw(train, features))
                oracle = LogisticRegression(C=1.0, solver="lbfgs", tol=1e-11, max_iter=4000).fit(
                    X, [row["podio"] for row in train],
                )
                raw_test = _raw(test, features)
                transformed = (np.where(np.isnan(raw_test), medians, raw_test) - means) / scales
                expected = dict(zip(map(_key, test), oracle.predict_proba(transformed)[:, 1]))
                actual = {
                    _key(row): row["probabilidade"] for row in self.result["predictions"]
                    if row["temporada"] == 2022 and row["metodo"] == method
                }
                self.assertEqual(set(actual), set(expected))
                np.testing.assert_allclose([actual[key] for key in expected], list(expected.values()), atol=5e-6)

    def test_successful_calibration_preserves_reduced_rankings_within_each_gp(self):
        raw = {
            _key(row): row for row in self.result["predictions"]
            if row["metodo"] == "v2_uncalibrated"
        }
        comparisons = 0
        for row in self.result["predictions"]:
            if row["metodo"] not in {"v2_intercept_calibrated", "v2_sigmoid_calibrated"}:
                continue
            if row["probabilidade"] is not None:
                self.assertEqual(row["ranking_modelo"], raw[_key(row)]["ranking_modelo"])
                comparisons += 1
        self.assertGreater(comparisons, 0)

    def test_inner_oof_blocks_are_whole_gps_strictly_after_their_training(self):
        indexed = {_key(row): row for row in self.rows}
        for year in range(2022, 2026):
            records = [record for record in _fits_for_year(self.result, year) if record["purpose"] == "inner_v2"]
            scored_keys = []
            for record in records:
                train = record["train_partition"]
                scored = record["predict_partition"]
                self.assertTrue(set(map(tuple, train["gps"])).isdisjoint(map(tuple, scored["gps"])))
                self.assertLess(train["max_reference_utc"], scored["min_reference_utc"])
                self.assertGreaterEqual(train["n_gp"], 8)
                self.assertLessEqual(scored["n_gp"], 4)
                for gp in scored["gps"]:
                    expected = {_key(row) for row in self.rows if [row["temporada"], row["rodada"]] == gp}
                    actual = {tuple(key) for key in scored["keys"] if list(key[:2]) == gp}
                    self.assertEqual(actual, expected)
                self.assertEqual(train["sha256"], _partition_hash(train, self.rows))
                self.assertEqual(scored["sha256"], _partition_hash(scored, self.rows))
                self.assertTrue(all(indexed[tuple(key)]["temporada"] < year for key in scored["keys"]))
                scored_keys.extend(tuple(key) for key in scored["keys"])
            self.assertEqual(len(scored_keys), len(set(scored_keys)))
            prior_gps = sorted({(row["temporada"], row["rodada"]) for row in self.rows if row["temporada"] < year})
            expected_oof = {_key(row) for row in self.rows if (row["temporada"], row["rodada"]) in prior_gps[8:]}
            self.assertEqual(set(scored_keys), expected_oof)
            for calibration in _calibrations_for_year(self.result, year):
                self.assertEqual({_key(row) for row in calibration["oof_rows"]}, expected_oof)
                self.assertEqual(calibration["oof_partition"]["sha256"], _partition_hash(
                    calibration["oof_partition"], calibration["oof_rows"],
                ))

    def test_conflicting_calendar_round_order_and_utc_references_are_rejected(self):
        rows = _rows()
        for row in rows:
            if row["temporada"] == 2021:
                row["rodada"] = 13 - row["rodada"]
        with self.assertRaisesRegex(ValueError, "order|UTC|calendar"):
            experiment.run_experiment(rows)

    def test_mutating_outer_test_targets_never_changes_its_fits_or_probabilities(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            if row["temporada"] == 2022:
                row["podio"] = 1 - row["podio"]
        observed = experiment.run_experiment(changed)
        self.assertEqual(_predictions_for_year(observed, 2022), _predictions_for_year(self.result, 2022))
        self.assertEqual(_fits_for_year(observed, 2022), _fits_for_year(self.result, 2022))
        self.assertEqual(_calibrations_for_year(observed, 2022), _calibrations_for_year(self.result, 2022))

    def test_mutating_oof_block_targets_never_changes_that_blocks_predictions(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            if row["temporada"] == 2021 and row["rodada"] >= 9:
                row["podio"] = 1 - row["podio"]
        observed = experiment.run_experiment(changed)
        expected_oof = _calibrations_for_year(self.result, 2022)[0]["oof_rows"]
        actual_oof = _calibrations_for_year(observed, 2022)[0]["oof_rows"]
        self.assertEqual(
            {_key(row): row["probabilidade"] for row in actual_oof},
            {_key(row): row["probabilidade"] for row in expected_oof},
        )
        # The perturbation is effective: calibration labels do change.
        self.assertNotEqual([row["podio"] for row in actual_oof], [row["podio"] for row in expected_oof])

    def test_future_extremes_and_missingness_cannot_change_earlier_fit_or_calibrator(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            if row["temporada"] == 2025:
                row["media_posicao_final_5"] = None
                row["media_pontos_equipe_5"] = 1e10
                row["taxa_podios_5"] = 0.999
        observed = experiment.run_experiment(changed)
        for year in (2022, 2023, 2024):
            self.assertEqual(_predictions_for_year(observed, year), _predictions_for_year(self.result, year))
        self.assertEqual(_trained_parameters(observed, 2025), _trained_parameters(self.result, 2025))
        self.assertEqual(_calibrations_for_year(observed, 2025), _calibrations_for_year(self.result, 2025))

    def test_predictions_keep_unknown_target_and_do_not_require_outcome_to_predict(self):
        changed = copy.deepcopy(self.rows)
        missing_key = _key(next(row for row in changed if row["temporada"] == 2022))
        next(row for row in changed if _key(row) == missing_key)["podio"] = None
        observed = experiment.run_experiment(changed)
        self.assertEqual(_predictions_for_year(observed, 2022), _predictions_for_year(self.result, 2022))
        cases = [row for row in observed["predictions"] if _key(row) == missing_key]
        self.assertEqual(len(cases), len(METHODS))
        for row in cases:
            self.assertIsNone(row["podio"])
            self.assertFalse(row["alvo_conhecido"])
            self.assertTrue(row["elegivel_previsao"])

    def test_unknown_training_target_is_excluded_rather_than_converted_to_negative(self):
        changed = _rows()
        missing_key = _key(changed[8])
        changed[8]["podio"] = None
        observed = experiment.run_experiment(changed)
        removed = experiment.run_experiment([row for row in changed if _key(row) != missing_key])
        self.assertEqual(_predictions_for_year(observed, 2022), _predictions_for_year(removed, 2022))
        for record in _fits_for_year(observed, 2022):
            self.assertNotIn(list(missing_key), record["train_partition"]["keys"])

    def test_input_rows_are_preserved_and_result_is_strict_json(self):
        original = _rows()
        snapshot = copy.deepcopy(original)
        result = experiment.run_experiment(original)
        self.assertEqual(original, snapshot)
        json.dumps(result, allow_nan=False)

    def test_insufficient_oof_calibration_fails_explicitly_without_raw_probability_fallback(self):
        rows = [row for row in _rows() if row["temporada"] != 2021 or row["rodada"] <= 8]
        result = experiment.run_experiment(rows)
        records = _calibrations_for_year(result, 2022)
        self.assertEqual({record["kind"] for record in records}, {"intercept", "sigmoid"})
        for record in records:
            self.assertEqual(record["status"], "not_estimable")
            self.assertTrue(record.get("reason"))
        for row in result["predictions"]:
            if row["metodo"] in {"v2_intercept_calibrated", "v2_sigmoid_calibrated"}:
                self.assertIsNone(row["probabilidade"])
                self.assertNotEqual(row["status"], "ok")
            elif row["metodo"] == "v2_uncalibrated":
                self.assertIsNotNone(row["probabilidade"])

    def test_one_failed_inner_fit_disallows_calibrating_on_the_surviving_subset(self):
        rows = _rows()
        for source in list(rows):
            if source["temporada"] == 2021 and source["rodada"] >= 9:
                extra = copy.deepcopy(source)
                extra["rodada"] += 4
                reference = datetime.fromisoformat(extra["limite_inferior_referencia_utc"].replace("Z", "+00:00")) + timedelta(days=56)
                extra["limite_inferior_referencia_utc"] = reference.strftime("%Y-%m-%dT%H:%M:%SZ")
                extra["data_corrida"] = (reference + timedelta(days=1)).date().isoformat()
                rows.append(extra)
        real_fit = experiment.fit_design
        injected = []
        def fail_first_inner(train_rows, features, reduce=False):
            fit = real_fit(train_rows, features, reduce=reduce)
            if reduce and len({(row["temporada"], row["rodada"]) for row in train_rows}) == 8 and not injected:
                injected.append(True)
                fit.update(fit_status="failed", converged=False, failure_reason="deliberately failed inner fit")
            return fit
        with mock.patch.object(experiment, "fit_design", side_effect=fail_first_inner):
            result = experiment.run_experiment(rows)
        self.assertEqual(len(injected), 1)
        records = _calibrations_for_year(result, 2022)
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertEqual(record["status"], "not_estimable")
            self.assertFalse(record["oof_coverage_complete"])
            self.assertEqual(record["oof_expected_rows"], 64)
            self.assertEqual(record["oof_expected_known_rows"], 64)
            self.assertEqual(len(record["oof_rows"]), 32)
            self.assertEqual(len(record["oof_missing_keys"]), 32)
            self.assertEqual(len(record["inner_failed_eligible_fit_ids"]), 1)
        for row in result["predictions"]:
            if row["metodo"] in {"v2_intercept_calibrated", "v2_sigmoid_calibrated"}:
                self.assertIsNone(row["probabilidade"])


class InputContractTest(unittest.TestCase):
    def test_explicit_eligible_flag_cannot_override_pre_cutoff_ineligibility(self):
        rows = _rows()
        changed = next(row for row in rows if row["temporada"] == 2022)
        changed.update({
            "elegivel_previsao": True, "classificacao_ausente": 1,
            "posicao_classificacao": None, "posicao_classificacao_ausente": 1,
        })
        result = experiment.run_experiment(rows)
        cases = [row for row in result["predictions"] if _key(row) == _key(changed)]
        self.assertEqual(len(cases), len(METHODS))
        for row in cases:
            self.assertFalse(row["elegivel_previsao"])
            self.assertIsNone(row["probabilidade"])
            self.assertIn("classificacao_ausente", row["motivos_inelegibilidade"])

    def test_duplicate_identity_and_2026_are_rejected_before_fit(self):
        for rows in (
            _rows() + [copy.deepcopy(_rows()[0])],
            [dict(_rows()[0], temporada=2026)],
        ):
            with self.subTest(identity=[_key(row) for row in rows[-2:]]):
                with self.assertRaises(ValueError):
                    experiment.run_experiment(rows)

    def test_missing_feature_and_invalid_utc_are_rejected(self):
        for mutation in ("missing_feature", "naive_utc", "invalid_utc"):
            rows = _rows()
            if mutation == "missing_feature":
                del rows[0]["media_posicao_final_5"]
            else:
                rows[0]["limite_inferior_referencia_utc"] = (
                    "2021-03-01T15:00:00" if mutation == "naive_utc" else "2021-02-30T15:00:00Z"
                )
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    experiment.run_experiment(rows)


def _evaluation_fixture():
    """Two unequally sized GPs distinguish row and GP mean scoring."""
    rows, predictions = [], []
    for race, n, confidence in ((1, 8, 0.9), (2, 4, 0.6)):
        for driver in range(n):
            outcome = int(driver < 3)
            row = {
                "temporada": 2022, "rodada": race, "piloto_id": "driver_{}".format(driver),
                "podio": outcome, "elegivel_previsao": True,
                "posicao_classificacao": driver + 1,
            }
            rows.append(row)
            for method in ("a", "b"):
                predictions.append(dict(row, metodo=method, probabilidade=confidence if outcome else 1 - confidence))
    return rows, predictions


class EvaluationOracleTest(unittest.TestCase):
    def test_unscorable_fold_is_insufficient_without_invented_zero_metrics(self):
        for all_unknown in (True, False):
            with self.subTest(all_unknown=all_unknown):
                rows, predictions = _evaluation_fixture()
                for row in rows + predictions:
                    if row['rodada'] == 2:
                        row['temporada'] = 2023
                    if all_unknown or row['temporada'] == 2022:
                        row['podio'] = None
                result = runner.evaluate_methods(rows, predictions, methods=('a', 'b'))
                for method in ('a', 'b'):
                    actual = result['methods'][method]
                    self.assertEqual(actual['status'], 'cobertura_insuficiente')
                    self.assertIn('2022', actual['unscored_folds'])
                    self.assertIsNone(actual['folds']['2022'])
                    if all_unknown:
                        self.assertIsNone(actual['overall'])
                    else:
                        self.assertEqual(actual['overall']['n'], 4)
                    self.assertNotIn(method, result['gp_scores'])
                self.assertTrue(all(row['podio'] is None for row in rows if row['temporada'] == 2022))
                json.dumps(result, allow_nan=False)
                contrasts = dict(paired=[], global_calibration={}, predictive_criteria_met=False)
                with tempfile.TemporaryDirectory() as tmp:
                    for lang in ('pt', 'en'):
                        runner._report(Path(tmp), result, contrasts, {'methods': {}}, {}, lang)
                    for name in ('relatorio.md', 'report.en.md'):
                        report = (Path(tmp) / name).read_text()
                        self.assertIn('cobertura insuficiente', report)
                        self.assertIn('N/A', report)

    def test_duplicate_identity_is_rejected_even_when_first_prediction_is_unavailable(self):
        rows, predictions = _evaluation_fixture()
        unavailable = dict(predictions[0], probabilidade=None)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            runner.evaluate_methods(rows, [unavailable] + predictions, methods=('a', 'b'))

    def test_perfect_probabilities_keep_zero_loss_without_fabricating_calibration(self):
        rows, predictions = _evaluation_fixture()
        for row in predictions:
            row["probabilidade"] = float(row["podio"])
        result = runner.evaluate_methods(rows, predictions, methods=("a", "b"))
        for method in ("a", "b"):
            summary = result["methods"][method]["overall"]
            self.assertEqual(summary["brier"], 0.0)
            self.assertEqual(summary["log_loss"], 0.0)
            self.assertIsNone(summary["citl"])
            self.assertIsNone(summary["slope"])

    def test_gp_mean_brier_log_loss_and_podium_counts_match_elementary_arithmetic(self):
        rows, predictions = _evaluation_fixture()
        result = runner.evaluate_methods(rows, predictions, methods=("a", "b"))
        for method in ("a", "b"):
            actual = result["methods"][method]
            self.assertEqual(actual["status"], "complete")
            summary = actual["overall"]
            self.assertEqual(summary["n"], 12)
            self.assertEqual(summary["n_gp"], 2)
            self.assertAlmostEqual(summary["brier"], (8 * 0.01 + 4 * 0.16) / 12)
            self.assertAlmostEqual(summary["brier_mean_gp"], (0.01 + 0.16) / 2)
            self.assertAlmostEqual(summary["log_loss_mean_gp"], (-np.log(0.9) - np.log(0.6)) / 2)
            self.assertEqual(summary["top3_mean"], 3)
            self.assertEqual(summary["complete_podiums"], 2)
            self.assertEqual(summary["qualifying_complete_podiums"], 2)

    def test_unknown_target_is_excluded_from_scoring_without_becoming_zero(self):
        rows, predictions = _evaluation_fixture()
        rows[-1]["podio"] = None
        for row in predictions:
            if _key(row) == _key(rows[-1]):
                row["podio"] = None
        result = runner.evaluate_methods(rows, predictions, methods=("a", "b"))
        for method in ("a", "b"):
            actual = result["methods"][method]
            self.assertEqual(actual["status"], "complete")
            self.assertEqual(actual["unknown_eligible_targets"], 1)
            self.assertEqual(actual["overall"]["n"], 11)
            self.assertAlmostEqual(actual["overall"]["brier"], (8 * 0.01 + 3 * 0.16) / 11)
            self.assertEqual(actual["overall"]["top3_n_gp"], 1)

    def test_missing_prediction_blocks_comparison_instead_of_shrinking_common_cohort(self):
        rows, predictions = _evaluation_fixture()
        missing_key = _key(rows[0])
        predictions = [row for row in predictions if row["metodo"] != "b" or _key(row) != missing_key]
        result = runner.evaluate_methods(rows, predictions, methods=("a", "b"))
        self.assertEqual(result["methods"]["a"]["status"], "complete")
        self.assertEqual(result["methods"]["a"]["overall"]["n"], 12)
        self.assertEqual(result["methods"]["b"]["status"], "cobertura_insuficiente")
        self.assertEqual(result["methods"]["b"]["missing_keys"], [list(missing_key)])
        self.assertNotIn("b", result["gp_scores"])

    def test_paired_gp_delta_is_unweighted_and_bootstrap_cannot_mix_seasons(self):
        a, b = [], []
        for year, difference in ((2022, -0.2), (2023, 0.1)):
            for race, n in ((1, 10), (2, 100)):
                b.append({"season": year, "round": race, "n": n, "brier": 0.4, "log_loss": 0.7})
                a.append({"season": year, "round": race, "n": n, "brier": 0.4 + difference, "log_loss": 0.7 + difference})
        # Each season has exactly one possible contiguous two-GP block. Every
        # valid replicate has the same delta; a cross-season block changes it.
        result = runner.paired_interval(a, b, repetitions=24)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["delta_brier"], -0.05)
        self.assertAlmostEqual(result["delta_log_loss"], -0.05)
        self.assertIsNone(result["ci95_brier"])
        self.assertEqual(result["block_length"], 2)
        self.assertAlmostEqual(result["folds"]["2022"]["brier"], -0.2)
        self.assertAlmostEqual(result["folds"]["2023"]["brier"], 0.1)
        # Equal identities with different denominators cannot be paired.
        changed = copy.deepcopy(b)
        changed[0]["n"] += 1
        self.assertEqual(runner.paired_interval(a, changed, repetitions=24)["status"], "cobertura_insuficiente")
        changed = copy.deepcopy(b)
        changed[-1]["round"] = 4
        changed_a = copy.deepcopy(a)
        changed_a[-1]["round"] = 4
        self.assertEqual(runner.paired_interval(changed_a, changed, repetitions=24)["status"], "not_estimable")


class ResearchOutputGuardTest(unittest.TestCase):
    def test_runner_rejects_existing_or_escaping_destinations_before_loading_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            allowed = root / "reports/modelo_v2_calibracao_20261102"
            existing = allowed / "existing"
            existing.mkdir(parents=True)
            sentinel = existing / "sentinel.bin"
            sentinel.write_bytes(b"existing report bytes")
            outside = Path(directory) / "outside"
            outside.mkdir()
            (allowed / "escape").symlink_to(outside, target_is_directory=True)
            for destination in (
                root / "data/preparado", root / "models/modelo_v1", allowed,
                existing, outside / "result", allowed / "escape/result",
            ):
                with self.subTest(destination=destination), mock.patch.object(experiment, "load_dataset") as load:
                    with self.assertRaises(ValueError):
                        runner.run(root, destination, root / "baseline_must_not_be_read.json")
                    load.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"existing report bytes")
            self.assertFalse((root / "data/preparado").exists())
            self.assertFalse((outside / "result").exists())

    def test_preservation_checks_frozen_model_emission_and_extra_old_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = {
                "models/modelo_v1/model.bin": b"\x00frozen model\xff",
                "reports/operacao_2026/emissoes/registered.json": b'{"probability":0.123456789}',
                "old_source.py": b"# immutable prior source\n",
            }
            for relative, contents in originals.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            baseline = {"extra_protected_roots": ["old_source.py"]}
            baseline["files"] = runner.snapshot(root, baseline)
            before = runner.preservation(root, baseline)
            self.assertEqual(before["status"], "preserved")
            self.assertEqual(before["checked_files"], len(originals))
            (root / "old_source.py").write_bytes(b"changed source\n")
            (root / "reports/operacao_2026/emissoes/registered.json").unlink()
            (root / "models/modelo_v1/unexpected.bin").write_bytes(b"new bytes")
            after = runner.preservation(root, baseline)
            self.assertEqual(after["status"], "divergent")
            self.assertEqual(after["changed"], ["old_source.py"])
            self.assertEqual(after["missing"], ["reports/operacao_2026/emissoes/registered.json"])
            self.assertEqual(after["new"], ["models/modelo_v1/unexpected.bin"])
            self.assertEqual((root / "models/modelo_v1/model.bin").read_bytes(), originals["models/modelo_v1/model.bin"])


class CalibrationParameterOracleTest(unittest.TestCase):
    def test_intercept_solves_exact_binomial_score_equation(self):
        rates, outcomes = _exact_calibration()
        probabilities = expit(logit(rates) - 0.7)
        result = experiment.fit_calibrator(probabilities, outcomes, kind="intercept")
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["intercept"], 0.7, places=7)
        self.assertEqual(result["slope"], 1.0)
        adjusted = experiment.apply_calibrator(result, probabilities)
        np.testing.assert_allclose(adjusted, rates, atol=1e-8)
        self.assertAlmostEqual(float(np.sum(adjusted - outcomes)), 0.0, places=7)

    def test_sigmoid_recovers_two_independently_identified_parameters(self):
        rates, outcomes = _exact_calibration()
        probabilities = expit((logit(rates) - 0.7) / 0.6)
        result = experiment.fit_calibrator(probabilities, outcomes, kind="sigmoid")
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["intercept"], 0.7, places=6)
        self.assertAlmostEqual(result["slope"], 0.6, places=6)
        np.testing.assert_allclose(
            experiment.apply_calibrator(result, probabilities), rates, atol=2e-7,
        )

    def test_positive_calibrators_preserve_all_pairwise_rankings_and_ties(self):
        rates, outcomes = _exact_calibration()
        for kind in ("intercept", "sigmoid"):
            with self.subTest(kind=kind):
                fit = experiment.fit_calibrator(rates, outcomes, kind=kind)
                p = np.array([0.91, 0.12, 0.45, 0.45, 0.72])
                adjusted = np.asarray(experiment.apply_calibrator(fit, p))
                np.testing.assert_array_equal(
                    np.sign(p[:, None] - p[None, :]),
                    np.sign(adjusted[:, None] - adjusted[None, :]),
                )

    def test_negative_sigmoid_slope_is_explicit_and_cannot_fall_back(self):
        rates, outcomes = _exact_calibration()
        result = experiment.fit_calibrator(1 - rates, outcomes, kind="sigmoid")
        self.assertNotEqual(result["status"], "ok")
        self.assertIn("slope", result["reason"].lower())
        with self.assertRaises(ValueError):
            experiment.apply_calibrator(result, [0.2, 0.8])

    def test_nonidentifiable_sigmoid_has_no_predictions(self):
        result = experiment.fit_calibrator([0.4] * 12, [0, 1] * 6, kind="sigmoid")
        self.assertNotEqual(result["status"], "ok")
        self.assertTrue(result.get("reason"))
        with self.assertRaises(ValueError):
            experiment.apply_calibrator(result, [0.2, 0.8])

    def test_single_class_calibration_is_not_estimable(self):
        for kind in ("intercept", "sigmoid"):
            with self.subTest(kind=kind):
                result = experiment.fit_calibrator([0.2, 0.4, 0.7], [0, 0, 0], kind=kind)
                self.assertNotEqual(result["status"], "ok")
                with self.assertRaises(ValueError):
                    experiment.apply_calibrator(result, [0.3])

    def test_unknown_labels_and_invalid_probabilities_are_never_coerced(self):
        for probabilities, targets in (
            ([0.2, 0.5, 0.8], [0, None, 1]),
            ([0.2, np.nan, 0.8], [0, 1, 1]),
            ([0.2, np.inf, 0.8], [0, 1, 1]),
            ([0.2, -0.01, 0.8], [0, 1, 1]),
            ([0.2, 1.01, 0.8], [0, 1, 1]),
        ):
            with self.subTest(probabilities=probabilities, targets=targets):
                with self.assertRaises(ValueError):
                    experiment.fit_calibrator(probabilities, targets)


if __name__ == "__main__":
    unittest.main()
