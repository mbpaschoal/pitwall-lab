"""Synthetic statistical oracles for the isolated statsmodels research audit.

These tests do not load real historical targets, fit the frozen v1 object, or
write forecasts.  Numerical oracles use independently fitted scikit-learn
models and exact binomial counts rather than snapshots of implementation output.
"""

import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression

from pitwall.research.statsmodels_audit import (
    audit_design,
    calibration_audit,
    coefficient_stability,
    fit_ridge,
)


def _preprocess(raw):
    """Independent median/population-standard-deviation preprocessing oracle."""
    medians = np.nanmedian(raw, axis=0)
    medians = np.where(np.isnan(medians), 0.0, medians)
    filled = np.where(np.isnan(raw), medians, raw)
    means = filled.mean(axis=0)
    scales = filled.std(axis=0, ddof=0)
    scales = np.where(scales == 0.0, 1.0, scales)
    return (filled - means) / scales, medians, means, scales


def _sklearn_oracle(X, y):
    return LogisticRegression(
        C=1.0, penalty="l2", solver="lbfgs", tol=1e-11, max_iter=4000
    ).fit(X, y)


def _exact_calibration_fixture(gps=None):
    # Every probability bucket has its exact expected number of positives.
    probabilities_per_gp = [0.25] * 4 + [0.5] * 4 + [0.75] * 4
    labels_per_gp = [1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0]
    if gps is None:
        gps = [(year, round_) for year in (2024, 2025) for round_ in range(1, 5)]
    probabilities, labels, groups = [], [], []
    for gp in gps:
        probabilities.extend(probabilities_per_gp)
        labels.extend(labels_per_gp)
        groups.extend([gp] * len(labels_per_gp))
    return np.array(probabilities), np.array(labels), groups


def _stability_fixture():
    rng = np.random.RandomState(1729)
    raw, labels, groups = [], [], []
    for year in (2021, 2022, 2023):
        for round_ in range(1, 5):
            for driver in range(8):
                x = rng.normal() + 0.4 * (year - 2021) + 0.2 * round_
                z = rng.normal()
                missing = np.nan if driver == 0 else z
                raw.append([x, x, 3.0, missing])
                labels.append(int(rng.uniform() < expit(0.8 * x - 0.5 * z - 0.3)))
                groups.append((year, round_))
    return np.array(raw), np.array(labels), groups


class DesignAuditTest(unittest.TestCase):
    def test_identifies_exact_redundancy_and_only_computes_identifiable_vifs(self):
        x = np.arange(-3.0, 4.0)
        square = x * x
        raw = np.column_stack([np.zeros(7), x, x, 2 * x, square, x + square])
        before = raw.copy()
        result = audit_design(
            raw,
            ["zero", "x", "same_x", "double_x", "square", "sum"],
            raw_matrix=raw,
        )
        self.assertEqual(result["rank"], 2)
        self.assertEqual(result["rank_with_intercept"], 3)
        self.assertEqual([row["feature"] for row in result["constants"]], ["zero"])
        self.assertIn(["x", "same_x"], result["identical_pairs"])
        self.assertEqual(result["selected_features"], ["x", "square"])
        self.assertIn("sum", result["dependent_features"])
        self.assertEqual([row["feature"] for row in result["vif"]], ["x", "square"])
        for row in result["vif"]:
            self.assertAlmostEqual(row["vif"], 1.0, places=10)
        pair = next(
            row for row in result["raw_proportional_pairs"]
            if row["left"] == "x" and row["right"] == "double_x"
        )
        self.assertAlmostEqual(pair["right_per_left"], 2.0)
        np.testing.assert_array_equal(raw, before)
        json.dumps(result, allow_nan=False)

    def test_full_rank_design_remains_full_rank_after_including_intercept(self):
        X = np.array([[0, 0], [1, 0], [0, 1], [2, 3], [3, -1]], dtype=float)
        result = audit_design(X, ["a", "b"])
        self.assertEqual(result["rank"], 2)
        self.assertEqual(result["rank_with_intercept"], 3)
        self.assertEqual(result["selected_features"], ["a", "b"])
        self.assertEqual(result["dependent_features"], [])

    def test_nonfinite_and_duplicate_feature_names_are_rejected(self):
        with self.assertRaises(ValueError):
            audit_design(np.array([[0.0], [np.inf]]), ["x"])
        with self.assertRaises(ValueError):
            audit_design(np.array([[0.0, 1.0], [1.0, 2.0]]), ["x", "x"])


class RidgeAuditTest(unittest.TestCase):
    def test_ridge_matches_independent_sklearn_even_with_redundant_columns(self):
        rng = np.random.RandomState(42)
        base = rng.normal(size=(200, 3))
        X = np.column_stack([base, base[:, 0], np.zeros(200)])
        y = rng.binomial(1, expit(0.4 + base @ np.array([0.9, -0.6, 0.3])))
        before = X.copy()
        expected = _sklearn_oracle(X, y)
        actual = fit_ridge(X, y, C=1.0)
        self.assertTrue(actual["converged"])
        self.assertAlmostEqual(actual["alpha_slopes"], 1 / len(y))
        np.testing.assert_allclose(actual["coef"], expected.coef_[0], atol=2e-5)
        self.assertAlmostEqual(actual["intercept"], expected.intercept_[0], places=5)
        np.testing.assert_allclose(
            expit(X @ np.asarray(actual["coef"]) + actual["intercept"]),
            expected.predict_proba(X)[:, 1], atol=3e-6,
        )
        np.testing.assert_array_equal(X, before)
        json.dumps(actual, allow_nan=False)

    def test_labels_must_be_known_binary_and_regularization_positive(self):
        X = np.array([[-1.0], [0.0], [1.0], [2.0]])
        for y in ([0, 1, np.nan, 0], [0, 1, 2, 0]):
            with self.subTest(labels=y):
                with self.assertRaises(ValueError):
                    fit_ridge(X, y)
        with self.assertRaises(ValueError):
            fit_ridge(X, [0, 0, 1, 1], C=0)


class CalibrationAuditTest(unittest.TestCase):
    def test_exact_binomial_oracle_recovers_zero_intercept_unit_slope(self):
        p, y, groups = _exact_calibration_fixture()
        result = calibration_audit(p, y, groups, bootstrap_reps=12)
        self.assertEqual(result["n_rows"], len(p))
        self.assertEqual(result["n_gp"], 8)
        self.assertEqual(result["joint"]["status"], "ok")
        self.assertAlmostEqual(result["joint"]["intercept"], 0.0, places=8)
        self.assertAlmostEqual(result["joint"]["slope"], 1.0, places=8)
        self.assertAlmostEqual(
            result["calibration_in_the_large"]["intercept"], 0.0, places=8
        )
        self.assertAlmostEqual(result["brier"], np.mean((p - y) ** 2), places=12)
        self.assertAlmostEqual(
            result["log_loss"], -np.mean(y * np.log(p) + (1 - y) * np.log1p(-p)),
            places=12,
        )
        self.assertEqual(len(result["bins"]), 10)
        self.assertEqual(sum(row["n"] for row in result["bins"]), len(p))
        for row in result["bins"]:
            if row["n"] == 0:
                self.assertIsNone(row["observed_rate"])
                self.assertIsNone(row["mean_probability"])
        self.assertNotIn("recalibrated_probabilities", result)
        json.dumps(result, allow_nan=False)

    def test_affine_logit_oracle_distinguishes_joint_intercept_from_citl(self):
        true_rate, y, groups = _exact_calibration_fixture()
        true_logit = np.log(true_rate / (1 - true_rate))
        forecast = expit((true_logit - 0.7) / 0.6)
        result = calibration_audit(forecast, y, groups, bootstrap_reps=8)
        self.assertAlmostEqual(result["joint"]["intercept"], 0.7, places=8)
        self.assertAlmostEqual(result["joint"]["slope"], 0.6, places=8)
        citl = result["calibration_in_the_large"]["intercept"]
        # The independent intercept-only score equation must be zero; this is
        # a different estimand from the joint calibration intercept above.
        adjusted_mean = expit(np.log(forecast / (1 - forecast)) + citl).mean()
        self.assertAlmostEqual(adjusted_mean, y.mean(), places=10)

    def test_endpoint_probabilities_are_counted_without_clipping(self):
        p, y, groups = _exact_calibration_fixture()
        p = np.append(p, [0.0, 1.0])
        y = np.append(y, [1, 1])  # One confidently incorrect prediction.
        groups.extend([(2024, 1), (2024, 1)])
        result = calibration_audit(p, y, groups, bootstrap_reps=12)
        self.assertEqual(result["excluded_endpoint_rows"], 2)
        self.assertEqual(result["n_logit_rows"], len(p) - 2)
        self.assertEqual(sum(row["n"] for row in result["bins"]), len(p))
        self.assertTrue(result["log_loss_infinite"])
        self.assertIsNone(result["log_loss"])
        self.assertAlmostEqual(result["brier"], np.mean((p - y) ** 2), places=12)
        json.dumps(result, allow_nan=False)

    def test_invalid_probabilities_and_unknown_labels_are_rejected(self):
        p, y, groups = _exact_calibration_fixture()
        for invalid in (np.nan, np.inf, -0.001, 1.001):
            changed = p.copy()
            changed[0] = invalid
            with self.subTest(probability=invalid):
                with self.assertRaises(ValueError):
                    calibration_audit(changed, y, groups, bootstrap_reps=4)
        with self.assertRaises(ValueError):
            calibration_audit(p, [None] + y[1:].tolist(), groups, bootstrap_reps=4)

    def test_bootstrap_is_reproducible_and_keeps_season_boundaries(self):
        p, y, groups = _exact_calibration_fixture()
        # Disturb counts by GP so this also tests nondegenerate intervals.
        y = y.copy()
        y[0] = 0
        y[15] = 1
        y[41] = 0
        first = calibration_audit(p, y, groups, bootstrap_reps=32, seed=123)
        second = calibration_audit(p, y, groups, bootstrap_reps=32, seed=123)
        self.assertEqual(first["bootstrap"], second["bootstrap"])
        bootstrap = first["bootstrap"]
        self.assertEqual(bootstrap["requested_replicates"], 32)
        self.assertEqual(bootstrap["block_length"], 2)
        self.assertEqual(bootstrap["seed"], 123)
        self.assertEqual(
            bootstrap["successful_replicates"] + bootstrap["failed_replicates"], 32
        )
        self.assertEqual({row["season"] for row in bootstrap["season_blocks"]}, {2024, 2025})
        self.assertEqual(first["n_gp"], 8)  # Round 1 in two years is two GPs.

    def test_calendar_gaps_do_not_become_artificially_adjacent_blocks(self):
        p, y, groups = _exact_calibration_fixture(
            [(2024, 1), (2024, 3), (2025, 1), (2025, 3)]
        )
        result = calibration_audit(p, y, groups, bootstrap_reps=16)
        self.assertEqual(result["bootstrap"]["status"], "not_estimable")
        self.assertEqual(result["bootstrap"]["successful_replicates"], 0)

    def test_constant_forecast_does_not_claim_identifiable_calibration_slope(self):
        _, y, groups = _exact_calibration_fixture()
        result = calibration_audit(np.full(len(y), 0.5), y, groups, bootstrap_reps=8)
        self.assertEqual(result["joint"]["status"], "not_estimable")
        self.assertIsNone(result["joint"].get("slope"))
        self.assertAlmostEqual(
            result["calibration_in_the_large"]["intercept"], 0.0, places=8
        )

    def test_perfect_separation_is_not_reported_as_finite_reliable_estimation(self):
        p, _, groups = _exact_calibration_fixture()
        y = (p > 0.5).astype(int)
        result = calibration_audit(p, y, groups, bootstrap_reps=8)
        self.assertEqual(result["joint"]["status"], "not_estimable")
        self.assertIsNone(result["joint"].get("slope"))


class CoefficientStabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw, cls.y, cls.groups = _stability_fixture()
        cls.X, cls.medians, cls.means, cls.scales = _preprocess(cls.raw)
        cls.reference = _sklearn_oracle(cls.X, cls.y)
        cls.features = ["x", "duplicate_x", "constant", "sometimes_missing"]
        cls.raw_before = cls.raw.copy()
        cls.y_before = cls.y.copy()
        cls.groups_before = copy.deepcopy(cls.groups)
        cls.result = coefficient_stability(
            cls.raw, cls.y, cls.groups, cls.features,
            cls.medians, cls.means, cls.scales, cls.reference.coef_[0],
            reference_intercept=float(cls.reference.intercept_[0]),
        )

    def test_baseline_reproduces_reference_recipe_and_inputs_are_unchanged(self):
        np.testing.assert_allclose(
            self.result["baseline"]["coef"], self.reference.coef_[0], atol=3e-5
        )
        np.testing.assert_array_equal(self.raw, self.raw_before)
        np.testing.assert_array_equal(self.y, self.y_before)
        self.assertEqual(self.groups, self.groups_before)
        self.assertEqual(len(self.result["jackknife"]), 12)
        self.assertEqual(self.result["failures"], [])
        json.dumps(self.result, allow_nan=False)

    def test_omitted_gp_relearns_imputation_and_scale_on_remaining_rows(self):
        row = next(x for x in self.result["jackknife"] if x["omitted_gp"] == [2021, 1])
        mask = np.array([gp != (2021, 1) for gp in self.groups])
        X, medians, means, scales = _preprocess(self.raw[mask])
        expected = _sklearn_oracle(X, self.y[mask])
        self.assertEqual(row["n_rows"], int(mask.sum()))
        np.testing.assert_allclose(row["medians"], medians, atol=1e-12)
        np.testing.assert_allclose(row["means"], means, atol=1e-12)
        np.testing.assert_allclose(row["scales"], scales, atol=1e-12)
        np.testing.assert_allclose(row["coef"], expected.coef_[0], atol=3e-5)
        np.testing.assert_allclose(
            row["coef_reference_scale"], expected.coef_[0] * self.scales / scales,
            atol=3e-5,
        )

    def test_expanding_fit_has_no_future_training_seasons(self):
        self.assertEqual(
            [row["training_seasons"] for row in self.result["expanding"]],
            [[2021], [2021, 2022], [2021, 2022, 2023]],
        )
        for row in self.result["expanding"]:
            allowed = set(row["training_seasons"])
            self.assertEqual(row["n_rows"], sum(gp[0] in allowed for gp in self.groups))

    def test_redundant_coefficients_remain_symmetric_and_constant_stays_zero(self):
        for row in self.result["jackknife"]:
            self.assertAlmostEqual(row["coef_reference_scale"][0], row["coef_reference_scale"][1], places=8)
            self.assertAlmostEqual(row["coef_reference_scale"][2], 0.0, places=12)
        constant = next(row for row in self.result["feature_summary"] if row["feature"] == "constant")
        self.assertEqual(constant["zero_count"], 12)

    def test_coefficient_sensitivity_rejects_validation_or_operational_years(self):
        for year in (2024, 2025, 2026):
            groups = [(year, 1)] + self.groups[1:]
            with self.subTest(year=year):
                with self.assertRaises(ValueError):
                    coefficient_stability(
                        self.raw, self.y, groups, self.features,
                        self.medians, self.means, self.scales, self.reference.coef_[0],
                    )


class AuditSourceProtectionTest(unittest.TestCase):
    @staticmethod
    def _csv(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _calibration_sources(self, root, year=2025):
        rows = []
        for driver, eligible, known, target, probability in (
            ("a", "1", "1", "0", "0.2"),
            ("b", "1", "1", "1", "0.7"),
            ("unknown", "1", "0", "", "0.4"),
            ("ineligible", "0", "1", "0", ""),
        ):
            rows.append({
                "temporada": str(year), "rodada": "1", "piloto_id": driver,
                "elegivel_previsao": eligible, "alvo_conhecido": known,
                "podio": target, "probabilidade_modelo": probability,
            })
        if year == 2024:
            prediction_path = root / "reports/modelo_v1/previsoes_validacao.csv"
            outcome_path = prediction_path
        else:
            prediction_path = root / "reports/avaliacao_final_v1/previsoes_pre_corrida.csv"
            outcome_path = root / "reports/avaliacao_final_v1/avaliacao_por_piloto.csv"
        self._csv(prediction_path, rows)
        self._csv(outcome_path, rows)
        return prediction_path, outcome_path, rows

    def test_calibration_loader_excludes_unknown_targets_without_creating_negatives(self):
        from pitwall.research.run_statsmodels_audit import load_calibration

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for year in (2024, 2025):
                self._calibration_sources(root, year)
                p, y, groups, coverage = load_calibration(root, year)
                np.testing.assert_array_equal(p, [0.2, 0.7])
                np.testing.assert_array_equal(y, [0, 1])
                self.assertEqual(groups, [(year, 1), (year, 1)])
                self.assertEqual(coverage["original_rows"], 4)
                self.assertEqual(coverage["eligible_rows"], 3)
                self.assertEqual(coverage["unknown_targets"], 1)
                self.assertEqual(coverage["analysed_rows"], 2)
                self.assertFalse(coverage["untouched_test"])

    def test_calibration_loader_rejects_2026_before_reading_any_sources(self):
        from pitwall.research.run_statsmodels_audit import load_calibration

        with tempfile.TemporaryDirectory() as folder:
            for year in (2023, 2026):
                with self.subTest(year=year):
                    with self.assertRaises(ValueError):
                        load_calibration(Path(folder), year)

    def test_calibration_loader_requires_same_keys_and_exact_frozen_probabilities(self):
        from pitwall.research.run_statsmodels_audit import load_calibration

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            predictions, outcomes, rows = self._calibration_sources(root)
            self._csv(outcomes, rows[:-1])
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                load_calibration(root, 2025)
            changed = copy.deepcopy(rows)
            changed[0]["probabilidade_modelo"] = "0.21"
            self._csv(outcomes, changed)
            with self.assertRaisesRegex(ValueError, "probability mismatch"):
                load_calibration(root, 2025)
            self._csv(outcomes, rows)
            self._csv(predictions, rows + rows[:1])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_calibration(root, 2025)

    def test_unknown_target_cannot_have_a_populated_negative_label(self):
        from pitwall.research.run_statsmodels_audit import load_calibration

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, outcome_path, rows = self._calibration_sources(root)
            rows[2]["podio"] = "0"
            self._csv(outcome_path, rows)
            with self.assertRaisesRegex(ValueError, "unknown outcome"):
                load_calibration(root, 2025)

    def test_protection_detects_changed_missing_and_new_files_and_registered_emission(self):
        from pitwall.research.run_statsmodels_audit import snapshot_protected, verify_protected

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = root / "models/modelo_v1/model.joblib"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"frozen-model")
            predictions = root / "reports/modelo_v1/previsoes_validacao.csv"
            predictions.parent.mkdir(parents=True)
            predictions.write_bytes(b"frozen-predictions")
            emission_dir = root / "registered/custom-emission"
            emission_dir.mkdir(parents=True)
            emission = emission_dir / "probabilities.csv"
            emission.write_bytes(b"recorded-probabilities")
            registry = root / "operacao2026/eventos/emissoes_registradas.json"
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps([{"diretorio": "registered/custom-emission"}]))
            baseline = snapshot_protected(root)
            self.assertIn("registered/custom-emission/probabilities.csv", baseline)
            self.assertEqual(verify_protected(root, baseline)["status"], "preserved")
            emission.write_bytes(b"changed-emission")
            predictions.unlink()
            new_model = model.parent / "unexpected-model.joblib"
            new_model.write_bytes(b"unexpected")
            result = verify_protected(root, {"files": baseline})
            self.assertEqual(result["status"], "divergent")
            self.assertEqual(result["changed"], ["registered/custom-emission/probabilities.csv"])
            self.assertEqual(result["missing"], ["reports/modelo_v1/previsoes_validacao.csv"])
            self.assertEqual(result["new"], ["models/modelo_v1/unexpected-model.joblib"])

    def test_destination_cannot_overwrite_sources_or_an_existing_audit(self):
        from pitwall.research.run_statsmodels_audit import run_audit

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            existing = root / "reports/statsmodels_audit_20261102/existing"
            existing.mkdir(parents=True)
            marker = existing / "result.json"
            marker.write_text("preserve me", encoding="utf-8")
            for destination in (
                root / "models/modelo_v1",
                root / "reports/statsmodels_audit_20261102",
                existing,
            ):
                with self.subTest(destination=str(destination)):
                    with self.assertRaisesRegex(ValueError, "new child"):
                        run_audit(root, destination, bootstrap_reps=0)
            self.assertEqual(marker.read_text(), "preserve me")

    def test_training_loader_enforces_allowlist_and_frozen_source_hashes(self):
        from pitwall.research.run_statsmodels_audit import FEATURES, load_training

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = []
            for driver, target in (("a", "0"), ("b", "1"), ("unknown", "")):
                row = {name: "0" for name in FEATURES}
                row.update({
                    "temporada": "2021", "rodada": "1", "piloto_id": driver,
                    "divisao": "treino", "podio": target,
                    "limite_inferior_referencia_utc": "2021-03-27T00:00:00Z",
                    "posicao_final": "999", "status": "post-race-secret",
                    "pontos": "999", "grid_resultado": "999",
                    "media_posicao_final_5": "",
                })
                rows.append(row)
            source = root / "data/preparado/treino.csv"
            self._csv(source, rows)
            schema = root / "data/preparado/colunas.json"
            schema.write_text(json.dumps({
                "entradas": list(FEATURES),
                "auditoria_proibida_como_entrada": ["posicao_final", "status", "pontos", "grid_resultado"],
            }))
            metadata = root / "models/modelo_v1/metadados.json"
            metadata.parent.mkdir(parents=True)
            metadata.write_text(json.dumps({
                "entradas": list(FEATURES),
                "hashes_fontes_permitidas": {
                    "treino.csv": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "colunas.json": hashlib.sha256(schema.read_bytes()).hexdigest(),
                },
            }))
            X, y, groups, names, _, coverage = load_training(root)
            self.assertEqual(X.shape, (2, 15))
            self.assertEqual(names, list(FEATURES))
            self.assertTrue(np.isnan(X[:, names.index("media_posicao_final_5")]).all())
            self.assertFalse(np.any(X == 999))
            np.testing.assert_array_equal(y, [0, 1])
            self.assertEqual(groups, [(2021, 1), (2021, 1)])
            self.assertEqual(coverage["unknown_targets"], 1)
            source.write_text(source.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "frozen v1 provenance"):
                load_training(root)


if __name__ == "__main__":
    unittest.main()
