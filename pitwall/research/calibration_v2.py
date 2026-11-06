"""Fixed temporal research experiment for reduced inputs and OOF calibration.

Only retrospective 2021–2025 sources are admitted. Frozen v1 artefacts are never
loaded as executable objects or modified. All returned models are plain research
records; this module has no publishing or operational emission path.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
from scipy.special import expit, logit

from pitwall.research.statsmodels_audit import fit_ridge, _preprocess


FEATURES_V1 = (
    "posicao_classificacao", "posicao_classificacao_repetida",
    "classificacao_ausente", "posicao_classificacao_ausente",
    "media_posicao_final_5", "taxa_podios_5", "n_posicoes_5", "n_podios_5",
    "media_pontos_equipe_5", "n_corridas_equipe_5", "n_participacoes_equipe_5",
    "historico_piloto_insuficiente", "historico_equipe_insuficiente",
    "equipe_pre_corrida_ausente", "referencia_temporal_ausente",
)
FEATURES_V2 = (
    "posicao_classificacao", "posicao_classificacao_repetida",
    "media_posicao_final_5", "taxa_podios_5", "media_pontos_equipe_5", "n_posicoes_5",
)
BOOLEAN_FEATURES = {
    "posicao_classificacao_repetida", "classificacao_ausente",
    "posicao_classificacao_ausente", "historico_piloto_insuficiente",
    "historico_equipe_insuficiente", "equipe_pre_corrida_ausente",
    "referencia_temporal_ausente",
}
METHODS = (
    "v1_temporal", "q_probability", "v2_uncalibrated",
    "v2_intercept_calibrated", "v2_sigmoid_calibrated",
)
OUTER_FOLDS = (2022, 2023, 2024, 2025)
INNER_WARMUP_GP = 8
INNER_BLOCK_GP = 4
MAX_BASE_FITS = 100
KEYS = ("temporada", "rodada", "piloto_id")
REFERENCE = "limite_inferior_referencia_utc"


def _utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("reference timestamps must be explicit UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("invalid UTC reference timestamp") from error
    return parsed.astimezone(timezone.utc)


def _key(row):
    return row["temporada"], row["rodada"], row["piloto_id"]


def _gp(row):
    return row["temporada"], row["rodada"]


def _ordered_gps(rows):
    """Keep calendar order and verify it against the known UTC references."""
    groups = sorted({_gp(row) for row in rows})
    previous = None
    for group in groups:
        references = [_utc(row[REFERENCE]) for row in rows if _gp(row) == group and row.get(REFERENCE)]
        if references:
            earliest = min(references)
            if previous is not None and earliest <= previous:
                raise ValueError("calendar GP order contradicts known UTC references")
            previous = earliest
        # A GP with no usable reference retains its calendar identity without
        # receiving any invented timestamp; it cannot supply eligible fit rows.
    return groups


def _number(value, allow_missing=True):
    if value is None or value == "":
        if allow_missing:
            return None
        raise ValueError("required numeric value is missing")
    if isinstance(value, str) and value in ("True", "False"):
        return float(value == "True")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid numeric value") from error
    if not np.isfinite(number):
        raise ValueError("non-finite numeric value")
    return number


def _normalise_rows(rows):
    result, seen = [], set()
    for original in rows:
        if not isinstance(original, dict):
            raise ValueError("dataset rows must be dictionaries")
        row = dict(original)
        for name in ("temporada", "rodada"):
            number = _number(row.get(name), allow_missing=False)
            if number != int(number) or isinstance(row.get(name), bool):
                raise ValueError("season and round must be integers")
            row[name] = int(number)
        if row["temporada"] not in range(2021, 2026) or row["rodada"] <= 0:
            raise ValueError("only retrospective seasons 2021–2025 are admitted")
        if not isinstance(row.get("piloto_id"), str) or not row["piloto_id"].strip():
            raise ValueError("driver identifier is required")
        identity = _key(row)
        if identity in seen:
            raise ValueError("duplicate canonical driver/GP key")
        seen.add(identity)
        for feature in FEATURES_V1:
            if feature not in row:
                raise ValueError("missing required input: " + feature)
            row[feature] = _number(row[feature])
            if feature in BOOLEAN_FEATURES and row[feature] not in (0.0, 1.0):
                raise ValueError("input indicator must be explicit zero or one: " + feature)
        target = _number(row.get("podio"))
        if target not in (None, 0.0, 1.0):
            raise ValueError("podium outcome must be zero, one, or unknown")
        row["podio"] = int(target) if target is not None else None
        reasons = []
        if row["classificacao_ausente"]:
            reasons.append("classificacao_ausente")
        reference = row.get(REFERENCE)
        if row["referencia_temporal_ausente"] or not reference:
            reasons.append("referencia_temporal_ausente")
        else:
            _utc(reference)
        row[REFERENCE] = reference or None
        row["elegivel_previsao"] = not reasons
        row["motivos_inelegibilidade"] = ";".join(reasons)
        row["alvo_conhecido"] = row["podio"] is not None
        if row.get("data_corrida"):
            try:
                race_date = datetime.fromisoformat(row["data_corrida"])
            except (TypeError, ValueError) as error:
                raise ValueError("invalid race date") from error
            # A date from a source is not a publication timestamp. This is the
            # already documented conservative release rule for previous races.
            release = datetime(race_date.year, race_date.month, race_date.day, tzinfo=timezone.utc) + timedelta(days=1)
            row["_released_by_protocol_utc"] = release.isoformat().replace("+00:00", "Z")
        result.append(row)
    return sorted(result, key=_key)


def load_dataset(root):
    """Read only the fixed prepared retrospective CSVs and their input schema.

    Audit/result/grid fields in the source CSVs are intentionally not projected
    into the returned rows. Unknown labels remain None. A split containing 2026
    or any contradictory season is refused before any fitting is possible.
    """
    root = Path(root).resolve()
    schema_path = (root / "data/preparado/colunas.json").resolve()
    if root not in schema_path.parents:
        raise ValueError("prepared schema resolves outside the project")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("entradas") != list(FEATURES_V1) or schema.get("chaves") != list(KEYS):
        raise ValueError("prepared schema differs from the frozen v1 allowlist")
    if set(FEATURES_V1) & set(schema.get("auditoria_proibida_como_entrada", [])):
        raise ValueError("an input overlaps prohibited outcome/audit columns")
    sources = (
        ("treino.csv", {2021, 2022, 2023}),
        ("validacao.csv", {2024}),
        ("teste_final_reservado.csv", {2025}),
    )
    rows = []
    fields = list(KEYS) + list(FEATURES_V1) + ["podio", REFERENCE, "data_corrida", "corrida"]
    for filename, years in sources:
        path = (root / "data/preparado" / filename).resolve()
        if root not in path.parents:
            raise ValueError("prepared source resolves outside the project")
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = set(KEYS) | set(FEATURES_V1) | {"podio", REFERENCE}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise ValueError("prepared source lacks required columns: " + filename)
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("duplicate CSV column")
            for original in reader:
                if int(original["temporada"]) not in years:
                    raise ValueError("source split contains an unexpected season")
                row = {field: original.get(field) for field in fields}
                row["source_id"] = "data/preparado/" + filename
                rows.append(row)
    return _normalise_rows(rows)


def _partition(rows, features=(), include_targets=False):
    ordered = sorted(rows, key=_key)
    fields = list(KEYS) + [REFERENCE] + list(features)
    if include_targets and "podio" not in fields:
        fields.append("podio")
    payload = []
    for row in ordered:
        record = {field: row.get(field) for field in fields}
        for feature in features:
            record[feature] = _number(record[feature])
        payload.append(record)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    references = [row[REFERENCE] for row in ordered if row.get(REFERENCE)]
    return {
        "n_rows": len(ordered), "n_gp": len({_gp(row) for row in ordered}),
        "keys": [list(_key(row)) for row in ordered],
        "gps": [list(group) for group in sorted({_gp(row) for row in ordered})],
        "min_reference_utc": min(references, key=_utc) if references else None,
        "max_reference_utc": max(references, key=_utc) if references else None,
        "hash_fields": fields, "sha256": hashlib.sha256(encoded).hexdigest(),
        "hash_encoding": "UTF-8 JSON list of projected rows, sorted canonical keys, sort_keys=True, compact separators, ensure_ascii=False, allow_nan=False",
    }


def _raw_matrix(rows, features):
    return np.asarray([[np.nan if row.get(feature) is None else float(row[feature]) for feature in features] for row in rows], dtype=float)


def prepare_design(train_rows, features, reduce=False):
    """Fit median/scaling/drop masks on these training rows only, without y."""
    features = list(features)
    if not train_rows or not features or len(features) != len(set(features)) or not set(features).issubset(FEATURES_V1):
        raise ValueError("non-empty training rows and a unique admitted feature list are required")
    raw = _raw_matrix(train_rows, features)
    if np.isinf(raw).any():
        raise ValueError("infinite input in training matrix")
    transformed, medians, means, scales = _preprocess(raw)
    selected, dropped = [], []
    basis = np.ones((len(train_rows), 1))
    for index, feature in enumerate(features):
        column = transformed[:, index]
        if reduce:
            if np.allclose(column, column[0], rtol=0, atol=1e-10):
                dropped.append({"feature": feature, "reason": "constant_in_training"})
                continue
            candidate = np.column_stack([basis, column])
            if np.linalg.matrix_rank(candidate) <= np.linalg.matrix_rank(basis):
                dropped.append({"feature": feature, "reason": "linear_dependency_in_training"})
                continue
            basis = candidate
        selected.append(index)
    matrix = np.column_stack([np.ones(len(train_rows)), transformed[:, selected]])
    design = {
        "features_requested": features, "features_selected": [features[index] for index in selected],
        "selected_indices": selected, "dropped_features": dropped,
        "medians": medians.tolist(), "means": means.tolist(), "scales": scales.tolist(),
        "rank_with_intercept": int(np.linalg.matrix_rank(matrix)),
        "reduce": bool(reduce), "train_partition": _partition(train_rows, features, include_targets=True),
    }
    design["vif"] = []
    if reduce and selected:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        for index, feature in enumerate(design["features_selected"], start=1):
            value = float(variance_inflation_factor(matrix, index))
            design["vif"].append({"feature": feature, "vif": value if np.isfinite(value) else None})
    return design


def fit_design(train_rows, features, reduce=False):
    """Fit the fixed C=1 base recipe; every failure is an explicit record."""
    design = prepare_design(train_rows, features, reduce=reduce)
    labels = np.asarray([row["podio"] for row in train_rows], dtype=float)
    if not np.isfinite(labels).all() or not np.isin(labels, [0, 1]).all():
        raise ValueError("model fitting requires known binary training labels")
    if len(np.unique(labels)) < 2:
        return dict(design, fit_status="failed", converged=False, failure_reason="training target has only one class")
    raw = _raw_matrix(train_rows, design["features_requested"])
    transformed = (np.where(np.isnan(raw), design["medians"], raw) - np.asarray(design["means"])) / np.asarray(design["scales"])
    x = transformed[:, design["selected_indices"]]
    try:
        if x.shape[1]:
            fitted = fit_ridge(x, labels, C=1.0)
        else:
            # The mathematically defined reduced model can have no slopes.
            # Its intercept-only MLE is explicit, not an identity calibration.
            intercept = float(logit(labels.mean()))
            fitted = {"coef": [], "intercept": intercept, "converged": True,
                      "gradient_max_abs": float(abs(expit(intercept) - labels.mean())),
                      "warnings": [], "C": 1.0, "alpha_intercept": 0.0,
                      "optimizer_message": "closed-form intercept-only Bernoulli MLE"}
        design.update(fitted)
        design["fit_status"] = "ok" if fitted["converged"] else "failed"
        if not fitted["converged"]:
            design["failure_reason"] = "penalised gradient exceeds the frozen tolerance"
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
        design.update(fit_status="failed", converged=False, failure_reason=str(error))
    return design


def predict_design(model, rows):
    """Apply only the transformations learned by ``fit_design``."""
    if model.get("fit_status") != "ok":
        raise ValueError("cannot predict with a failed research fit")
    if not rows:
        return []
    raw = _raw_matrix(rows, model["features_requested"])
    if np.isinf(raw).any():
        raise ValueError("infinite prediction input")
    transformed = (np.where(np.isnan(raw), model["medians"], raw) - np.asarray(model["means"])) / np.asarray(model["scales"])
    z = transformed[:, model["selected_indices"]]
    values = expit(model["intercept"] + z @ np.asarray(model["coef"]))
    if not np.isfinite(values).all():
        raise FloatingPointError("non-finite predicted probabilities")
    return values.tolist()


def fit_calibrator(probabilities, targets, kind="intercept"):
    """Estimate a fixed-form calibrator from chronological OOF labels only.

    The caller is responsible for OOF provenance; ``run_experiment`` enforces
    it and records all partitions. A sigmoid with nonpositive slope, separation,
    endpoint logits, or nonconvergence is unavailable, never an identity fallback.
    """
    import statsmodels.api as sm
    from statsmodels.tools.sm_exceptions import PerfectSeparationError

    if kind not in ("intercept", "sigmoid"):
        raise ValueError("unknown calibration kind")
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(targets, dtype=float)
    if p.ndim != 1 or y.shape != p.shape or not np.isfinite(p).all() or not np.isfinite(y).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("matching finite probabilities and known binary targets are required")
    if ((p < 0) | (p > 1)).any():
        raise ValueError("probabilities must be in [0,1]")
    record = {"kind": kind, "n_rows": len(p), "status": "not_estimable", "warnings": []}
    if not len(p) or len(np.unique(y)) < 2:
        return dict(record, reason="OOF calibration needs observations from both classes")
    if ((p <= 0) | (p >= 1)).any():
        return dict(record, reason="OOF endpoint or invalid probabilities prevent finite logits", endpoint_count=int(((p == 0) | (p == 1)).sum()))
    logs = logit(p)
    x = np.column_stack([np.ones(len(p)), logs]) if kind == "sigmoid" else np.ones((len(p), 1))
    if np.linalg.matrix_rank(x) != x.shape[1]:
        return dict(record, reason="OOF logit design is rank deficient")
    model = sm.GLM(y, x, family=sm.families.Binomial(), offset=logs if kind == "intercept" else None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = model.fit(maxiter=200, tol=1e-10)
            record["warnings"] = ["{}: {}".format(type(item.message).__name__, item.message) for item in caught]
            gradient = float(np.max(np.abs(model.score(result.params))) / len(y))
            if not result.converged or not np.isfinite(result.params).all() or not np.isfinite(gradient) or gradient > 1e-7 or any("PerfectSeparation" in warning or "RuntimeWarning" in warning for warning in record["warnings"]):
                return dict(record, reason="OOF calibration nonconvergence, separation, or numerical failure", gradient_max_abs=gradient if np.isfinite(gradient) else None)
            intercept = float(result.params[0])
            slope = float(result.params[1]) if kind == "sigmoid" else 1.0
            if slope <= 0:
                return dict(record, reason="sigmoid slope is not positive", estimated_intercept=intercept, estimated_slope=slope, gradient_max_abs=gradient)
            return dict(record, status="ok", intercept=intercept, slope=slope,
                        gradient_max_abs=gradient, converged=True,
                        interpretation="research calibration learned only from inner chronological OOF predictions")
        except (ValueError, FloatingPointError, np.linalg.LinAlgError, PerfectSeparationError) as error:
            record["warnings"] = ["{}: {}".format(type(item.message).__name__, item.message) for item in caught]
            return dict(record, reason=str(error))


def apply_calibrator(record, probabilities):
    """Apply a successful monotone OOF calibrator without clipping."""
    if record.get("status") != "ok" or record.get("slope", 0) <= 0:
        raise ValueError("calibrator is unavailable or not monotone")
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p <= 0) | (p >= 1)).any():
        raise ValueError("calibration application requires interior finite probabilities")
    values = expit(record["intercept"] + record["slope"] * logit(p))
    if not np.isfinite(values).all():
        raise FloatingPointError("non-finite calibrated prediction")
    return values.tolist()


def _check_temporal_partition(training, prediction):
    if not training or not prediction:
        return
    if {_gp(row) for row in training} & {_gp(row) for row in prediction}:
        raise ValueError("training and prediction share a GP")
    boundary = min(_utc(row[REFERENCE]) for row in prediction if row.get(REFERENCE))
    if any(_utc(row[REFERENCE]) >= boundary for row in training if row.get(REFERENCE)):
        raise ValueError("a training reference is not earlier than the prediction block")
    if any(_utc(row["_released_by_protocol_utc"]) > boundary for row in training if row.get("_released_by_protocol_utc")):
        raise ValueError("a training outcome is not released before the prediction block")


def run_experiment(rows, progress=None):
    """Execute four outer years and their fully nested chronological OOF fits.

    Base recipes and calibrator forms are fixed constants. No outer targets are
    passed to a fitter, feature selector, imputer, scaler, or calibrator. All
    original outer rows remain in predictions, including unavailable outcomes
    and explicit fit failures, so coverage cannot improve by silently dropping
    difficult cases.
    """
    rows = _normalise_rows(rows)
    predictions, fits, calibrations, coverage = [], [], [], []
    for year in OUTER_FOLDS:
        external = [row for row in rows if row["temporada"] == year]
        if not external:
            coverage.append({"outer_fold": year, "metodo": "all", "status": "no_outer_rows", "original_rows": 0})
            continue
        train_population = [row for row in rows if row["temporada"] < year]
        training = [row for row in train_population if row["elegivel_previsao"] and row["alvo_conhecido"]]
        eligible_external = [row for row in external if row["elegivel_previsao"]]
        _check_temporal_partition(training, eligible_external)
        if progress:
            progress("outer_fold", year, len(OUTER_FOLDS))
        trained = {}
        for label, features, reduce in (
            ("v1", FEATURES_V1, False),
            ("q", ("posicao_classificacao",), False),
            ("v2", FEATURES_V2, True),
        ):
            if not training:
                model = {"fit_status": "failed", "failure_reason": "no eligible known-label outer training rows", "converged": False,
                         "features_requested": list(features), "train_partition": _partition([], features, True)}
            else:
                model = fit_design(training, features, reduce=reduce)
            model.update({"fit_id": "outer-{}-{}".format(year, label), "outer_fold": year,
                          "purpose": "outer_" + label,
                          "predict_partition": _partition(eligible_external, features, False)})
            fits.append(model)
            trained[label] = model
        oof_rows = []
        train_gps = _ordered_gps(train_population)
        for start in range(INNER_WARMUP_GP, len(train_gps), INNER_BLOCK_GP):
            prior = set(train_gps[:start])
            block = set(train_gps[start:start + INNER_BLOCK_GP])
            inner_train = [row for row in train_population if _gp(row) in prior and row["elegivel_previsao"] and row["alvo_conhecido"]]
            inner_predict = [row for row in train_population if _gp(row) in block and row["elegivel_previsao"]]
            _check_temporal_partition(inner_train, inner_predict)
            if inner_train:
                model = fit_design(inner_train, FEATURES_V2, reduce=True)
            else:
                model = {"fit_status": "failed", "failure_reason": "no eligible known-label inner training rows", "converged": False,
                         "features_requested": list(FEATURES_V2), "train_partition": _partition([], FEATURES_V2, True)}
            model.update({"fit_id": "inner-{}-{}".format(year, start), "outer_fold": year, "purpose": "inner_v2",
                          "predict_partition": _partition(inner_predict, FEATURES_V2, False),
                          "warmup_gp": INNER_WARMUP_GP, "test_block_gp": [list(gp) for gp in train_gps[start:start + INNER_BLOCK_GP]]})
            fits.append(model)
            if model["fit_status"] == "ok":
                values = predict_design(model, inner_predict)
                for row, probability in zip(inner_predict, values):
                    oof_rows.append({**{key: row[key] for key in KEYS}, REFERENCE: row[REFERENCE],
                                     "probabilidade": probability, "podio": row["podio"],
                                     "alvo_conhecido": row["alvo_conhecido"], "source_fit_id": model["fit_id"]})
            if len(fits) > MAX_BASE_FITS:
                raise ValueError("fixed research budget of 100 base fits exceeded")
            if progress:
                progress("inner_oof", len(fits), MAX_BASE_FITS)
        known_oof = [row for row in oof_rows if row["alvo_conhecido"]]
        expected_oof = [row for row in train_population if _gp(row) in set(train_gps[INNER_WARMUP_GP:]) and row["elegivel_previsao"]]
        expected_keys = {_key(row) for row in expected_oof}
        actual_keys = {_key(row) for row in oof_rows}
        failed_inner = [fit["fit_id"] for fit in fits if fit["outer_fold"] == year and fit["purpose"] == "inner_v2" and fit["fit_status"] != "ok"]
        failed_eligible_inner = [fit["fit_id"] for fit in fits if fit["fit_id"] in failed_inner and fit["predict_partition"]["n_rows"] > 0]
        complete_oof = actual_keys == expected_keys and not failed_eligible_inner
        calibrator_by_kind = {}
        for kind in ("intercept", "sigmoid"):
            if complete_oof:
                record = fit_calibrator([row["probabilidade"] for row in known_oof], [row["podio"] for row in known_oof], kind=kind)
            else:
                record = {"kind": kind, "n_rows": len(known_oof), "status": "not_estimable", "warnings": [],
                          "reason": "incomplete chronological OOF coverage after an inner fit failure; calibrator not fitted on the surviving subset"}
            record.update({"outer_fold": year, "oof_rows": oof_rows,
                           "oof_partition": _partition(known_oof, ("probabilidade",), True),
                           "oof_all_partition": _partition(oof_rows, ("probabilidade",), True),
                           "outer_training_partition": _partition(training, FEATURES_V2, True),
                           "oof_expected_rows": len(expected_oof),
                           "oof_expected_known_rows": sum(row["alvo_conhecido"] for row in expected_oof),
                           "oof_coverage_complete": complete_oof,
                           "oof_missing_keys": [list(key) for key in sorted(expected_keys - actual_keys)],
                           "inner_failed_fit_ids": failed_inner,
                           "inner_failed_eligible_fit_ids": failed_eligible_inner})
            calibrations.append(record)
            calibrator_by_kind[kind] = record
        method_values, method_failures = {}, {}
        for method, label in (("v1_temporal", "v1"), ("q_probability", "q"), ("v2_uncalibrated", "v2")):
            model = trained[label]
            if model["fit_status"] == "ok":
                method_values[method] = predict_design(model, eligible_external)
            else:
                method_failures[method] = model["failure_reason"]
        for method, kind in (("v2_intercept_calibrated", "intercept"), ("v2_sigmoid_calibrated", "sigmoid")):
            record = calibrator_by_kind[kind]
            if "v2_uncalibrated" not in method_values:
                method_failures[method] = "outer v2 base model is unavailable"
            elif record["status"] != "ok":
                method_failures[method] = record["reason"]
            else:
                try:
                    method_values[method] = apply_calibrator(record, method_values["v2_uncalibrated"])
                except (ValueError, FloatingPointError) as error:
                    method_failures[method] = str(error)
        for method in METHODS:
            by_key = {_key(row): probability for row, probability in zip(eligible_external, method_values.get(method, []))}
            method_rows = []
            for row in external:
                probability = by_key.get(_key(row))
                status = "ok" if probability is not None else ("ineligible" if not row["elegivel_previsao"] else "fit_unavailable")
                method_rows.append({"metodo": method, "fold": year, **{key: row[key] for key in KEYS},
                                    "probabilidade": probability, "podio": row["podio"], "alvo_conhecido": row["alvo_conhecido"],
                                    "elegivel_previsao": row["elegivel_previsao"], "motivos_inelegibilidade": row["motivos_inelegibilidade"],
                                    "status": status, "failure_reason": method_failures.get(method) if status == "fit_unavailable" else None,
                                    "posicao_classificacao": row["posicao_classificacao"], "corrida": row.get("corrida"),
                                    REFERENCE: row[REFERENCE], "ranking_modelo": None, "ranking_classificacao": None})
            for group in sorted({_gp(row) for row in method_rows}):
                gp_rows = [row for row in method_rows if _gp(row) == group]
                candidates = [row for row in gp_rows if row["elegivel_previsao"]]
                for rank, row in enumerate(sorted(candidates, key=lambda r: (r["posicao_classificacao"] is None, r["posicao_classificacao"] if r["posicao_classificacao"] is not None else 0, r["piloto_id"])), start=1):
                    row["ranking_classificacao"] = rank
                available = [row for row in candidates if row["probabilidade"] is not None]
                for rank, row in enumerate(sorted(available, key=lambda r: (-r["probabilidade"], r["piloto_id"])), start=1):
                    row["ranking_modelo"] = rank
            predictions.extend(method_rows)
            coverage.append({"outer_fold": year, "metodo": method, "status": "ok" if method in method_values else "fit_unavailable",
                             "original_rows": len(external), "eligible_rows": len(eligible_external),
                             "known_target_rows": sum(row["alvo_conhecido"] for row in external),
                             "predicted_rows": len(by_key), "scored_rows": sum(row["probabilidade"] is not None and row["alvo_conhecido"] for row in method_rows),
                             "failed_rows": sum(row["status"] == "fit_unavailable" for row in method_rows),
                             "failure_reason": method_failures.get(method)})
    return {"predictions": predictions, "fit_records": fits, "calibration_records": calibrations, "coverage": coverage,
            "configuration": {"outer_folds": list(OUTER_FOLDS), "features_v1": list(FEATURES_V1), "features_v2": list(FEATURES_V2),
                              "C": 1.0, "inner_warmup_gp": INNER_WARMUP_GP, "inner_block_gp": INNER_BLOCK_GP,
                              "max_base_fits": MAX_BASE_FITS, "methods": list(METHODS),
                              "primary_candidate": "v2_intercept_calibrated", "secondary_candidate": "v2_sigmoid_calibrated",
                              "selection": "fixed recipes; no outer-target tuning; all calibrators fit only chronological inner OOF rows"}}
