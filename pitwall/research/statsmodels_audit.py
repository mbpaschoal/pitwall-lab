"""Pure statistical diagnostics for the isolated statsmodels research audit.

This module never reads or writes project artefacts. Ridge fits are research
replicas, not updates of the frozen v1. Calibration fits diagnose existing
probabilities and never return recalibrated predictions.
"""

from __future__ import annotations

from collections import Counter
import warnings

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit


ZERO_TOL = 1e-10
SIGN_TOL = 1e-6
GRADIENT_TOL = 1e-7


def _matrix(values, allow_missing=False):
    x = np.array(values, dtype=float, copy=True)
    if x.ndim != 2 or not x.shape[0] or not x.shape[1]:
        raise ValueError("a non-empty two-dimensional matrix is required")
    if np.isinf(x).any() or (not allow_missing and np.isnan(x).any()):
        raise ValueError("matrix contains invalid or non-finite values")
    return x


def _binary(values, n):
    y = np.array(values, dtype=float, copy=True)
    if y.shape != (n,) or not np.isfinite(y).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("known binary targets with matching length are required")
    return y


def _groups(values, n):
    groups = []
    for value in values:
        if not isinstance(value, (tuple, list, np.ndarray)) or len(value) != 2:
            raise ValueError("GP identifiers must be (season, round) pairs")
        try:
            invalid = any(isinstance(v, (bool, np.bool_)) or not np.isfinite(float(v)) or int(v) != float(v) for v in value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("invalid GP identifier") from error
        if invalid:
            raise ValueError("invalid GP identifier")
        season, race = (int(v) for v in value)
        if season not in range(2021, 2026) or race <= 0:
            raise ValueError("audit accepts retrospective 2021–2025 GP identifiers only")
        groups.append((season, race))
    if len(groups) != n:
        raise ValueError("GP identifiers do not match observations")
    return groups


def _warning_messages(caught):
    return ["{}: {}".format(type(w.message).__name__, str(w.message)) for w in caught]


def _rank(x):
    singular = np.linalg.svd(x, compute_uv=False)
    tolerance = float(max(x.shape) * np.finfo(float).eps * singular[0]) if len(singular) else 0.0
    return int(np.sum(singular > tolerance)), singular, tolerance


def audit_design(X, feature_names, raw_matrix=None):
    """Check identifiability without fitting an outcome model.

    ``X`` is the matrix after the frozen training transformations. Independent
    columns are retained in the supplied allowlist order, after an intercept.
    VIF is computed only on this full-rank reduced matrix. No variable is chosen
    by its association with the target or by predictive performance.
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    x = _matrix(X)
    names = list(feature_names)
    if len(names) != x.shape[1] or len(set(names)) != len(names):
        raise ValueError("feature names must be unique and match matrix columns")
    rank, singular, tolerance = _rank(x)
    augmented = np.column_stack([np.ones(len(x)), x])
    augmented_rank, _, _ = _rank(augmented)
    constants, identical, proportional = [], [], []
    constant_indices = set()
    for j, name in enumerate(names):
        if np.allclose(x[:, j], x[0, j], rtol=0, atol=ZERO_TOL):
            constants.append({"feature": name, "value": float(x[0, j])})
            constant_indices.add(j)
    for j in range(len(names)):
        for k in range(j + 1, len(names)):
            if j not in constant_indices and k not in constant_indices and np.allclose(x[:, j], x[:, k], rtol=1e-10, atol=ZERO_TOL):
                identical.append([names[j], names[k]])
    if raw_matrix is not None:
        raw = _matrix(raw_matrix, allow_missing=True)
        if raw.shape != x.shape:
            raise ValueError("raw matrix shape differs from transformed matrix")
        for j in range(len(names)):
            for k in range(j + 1, len(names)):
                a, b = raw[:, j], raw[:, k]
                valid = np.isfinite(a) & np.isfinite(b)
                if not np.array_equal(np.isfinite(a), np.isfinite(b)) or valid.sum() < 2:
                    continue
                a, b = a[valid], b[valid]
                if np.ptp(a) <= ZERO_TOL or np.ptp(b) <= ZERO_TOL:
                    continue
                factor = float(np.dot(a, b) / np.dot(a, a))
                if abs(factor) > ZERO_TOL and np.allclose(b, factor * a, rtol=1e-10, atol=ZERO_TOL):
                    proportional.append({"left": names[j], "right": names[k], "right_per_left": factor, "n_observed": int(valid.sum())})
    selected, dependent = [], []
    reduced = np.ones((len(x), 1))
    current_rank = 1
    for j, name in enumerate(names):
        candidate = np.column_stack([reduced, x[:, j]])
        candidate_rank, _, _ = _rank(candidate)
        if candidate_rank > current_rank:
            selected.append(name)
            reduced = candidate
            current_rank = candidate_rank
        elif j not in constant_indices:
            dependent.append(name)
    vifs = []
    for j, name in enumerate(selected, start=1):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = float(variance_inflation_factor(reduced, j))
        vifs.append({"feature": name, "vif": value if np.isfinite(value) else None, "warnings": _warning_messages(caught)})
    full_rank = rank == x.shape[1]
    condition = float(singular[0] / singular[-1]) if full_rank and singular[-1] > 0 else None
    reduced_rank, reduced_singular, _ = _rank(reduced)
    return {
        "n_rows": len(x), "n_features": len(names), "rank": rank,
        "rank_with_intercept": augmented_rank, "constants": constants,
        "identical_pairs": identical, "raw_proportional_pairs": proportional,
        "selected_features": selected, "dependent_features": dependent,
        "selection_rule": "deterministic allowlist order, conditional on intercept; no targets used",
        "reduced_rank_with_intercept": reduced_rank,
        "reduced_condition_number": float(reduced_singular[0] / reduced_singular[-1]),
        "vif": vifs,
        "svd": {"singular_values": singular.tolist(), "tolerance": tolerance, "condition_number": condition, "condition_infinite": not full_rank},
    }


def fit_ridge(X, y, C=1.0):
    """Fit a research replica of sklearn's unweighted logistic L2 objective.

    The statsmodels GLM objective is mean negative log likelihood plus
    ``alpha * beta**2 / 2``; hence alpha is ``1/(C*n)`` on slopes and zero on
    the intercept. In statsmodels 0.14.6 the pure-ridge branch ignores the usual
    iteration/tolerance kwargs, so we explicitly refine its estimate using the
    same GLM likelihood and score, and check the penalised first-order condition.
    This function deliberately provides no conventional p-values or intervals.
    """
    import statsmodels.api as sm

    x = _matrix(X)
    target = _binary(y, len(x))
    if len(np.unique(target)) != 2:
        raise ValueError("ridge fit requires both target classes")
    if not np.isfinite(C) or C <= 0:
        raise ValueError("C must be positive and finite")
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.r_[0.0, np.repeat(1.0 / (C * len(x)), x.shape[1])]
    model = sm.GLM(target, design, family=sm.families.Binomial())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        initial = model.fit_regularized(alpha=penalty, L1_wt=0.0, opt_method="BFGS")
        def objective(beta):
            return float(-model.loglike(beta) / len(x) + np.sum(penalty * beta**2) / 2)
        def score(beta):
            return -model.score(beta) / len(x) + penalty * beta
        polished = minimize(objective, np.asarray(initial.params), jac=score, method="L-BFGS-B", options={"maxiter": 2000, "gtol": 1e-10, "ftol": 1e-15, "maxls": 50})
    params = np.asarray(polished.x)
    gradient = float(np.max(np.abs(score(params))))
    finite = bool(np.isfinite(params).all() and np.isfinite(gradient))
    if not finite or not np.isfinite(objective(params)):
        raise FloatingPointError("ridge optimisation produced non-finite parameters, objective, or score")
    convergence = finite and gradient <= GRADIENT_TOL
    return {
        "coef": params[1:].tolist(), "intercept": float(params[0]),
        "converged": bool(convergence), "gradient_max_abs": gradient,
        "gradient_tolerance": GRADIENT_TOL,
        "optimizer_success": bool(polished.success), "optimizer_message": str(polished.message),
        "optimizer_iterations": int(polished.nit), "objective": objective(params),
        "alpha_slopes": float(penalty[1]), "alpha_intercept": 0.0,
        "C": float(C), "n_rows": len(x), "warnings": _warning_messages(caught),
    }


def _preprocess(raw):
    """Training-only median imputation and population standardisation."""
    medians = np.array([np.median(column[np.isfinite(column)]) if np.isfinite(column).any() else 0.0 for column in raw.T])
    imputed = np.where(np.isnan(raw), medians, raw)
    means = imputed.mean(axis=0)
    scales = imputed.std(axis=0, ddof=0)
    scales[scales <= np.finfo(float).eps] = 1.0
    return (imputed - means) / scales, medians, means, scales


def coefficient_stability(X_raw, y, gp_ids, feature_names, reference_medians, reference_means, reference_scales, reference_coef, C=1.0, reference_intercept=None, progress=None):
    """Sensitivity of fixed-recipe research replicas within v1 training data.

    Leave-one-GP-out and expanding-prefix replicas refit transforms on their
    own training rows. Slopes are also expressed in frozen-training standard
    deviation units, allowing comparison across changing scales. Quantiles are
    descriptive sensitivity ranges, not confidence intervals. All fits retain
    the full feature recipe, including its redundancies and penalty geometry.
    """
    raw = _matrix(X_raw, allow_missing=True)
    target = _binary(y, len(raw))
    groups = _groups(gp_ids, len(raw))
    if any(year not in (2021, 2022, 2023) for year, _ in groups):
        raise ValueError("coefficient sensitivity is restricted to v1 training 2021–2023")
    names = list(feature_names)
    vectors = [np.asarray(v, dtype=float) for v in (reference_medians, reference_means, reference_scales, reference_coef)]
    if len(names) != raw.shape[1] or len(set(names)) != len(names) or any(v.shape != (raw.shape[1],) or not np.isfinite(v).all() for v in vectors):
        raise ValueError("invalid reference transforms or feature names")
    medians, means, scales, reference = vectors
    if (scales <= 0).any():
        raise ValueError("reference scales must be positive")
    transformed = (np.where(np.isnan(raw), medians, raw) - means) / scales
    baseline = fit_ridge(transformed, target, C=C)
    baseline["coef_reference_scale"] = list(baseline["coef"])
    baseline["max_abs_difference_frozen_coefficient"] = float(np.max(np.abs(np.asarray(baseline["coef"]) - reference)))
    if reference_intercept is not None:
        if not np.isfinite(reference_intercept):
            raise ValueError("reference intercept must be finite")
        baseline["absolute_difference_frozen_intercept"] = float(abs(baseline["intercept"] - reference_intercept))
        baseline["max_abs_difference_frozen_training_probability"] = float(np.max(np.abs(expit(baseline["intercept"] + transformed @ np.asarray(baseline["coef"])) - expit(reference_intercept + transformed @ reference))))
    all_gps = sorted(set(groups))
    jackknife, expanding, failures = [], [], []
    def execute(mask, identity):
        selected = raw[mask]
        z, med, mean, scale = _preprocess(selected)
        fit = fit_ridge(z, target[mask], C=C)
        beta = np.asarray(fit["coef"])
        fit.update(identity)
        fit.update({"n_gp": len({g for g, keep in zip(groups, mask) if keep}),
                    "medians": med.tolist(), "means": mean.tolist(), "scales": scale.tolist(),
                    "coef_raw": (beta / scale).tolist(),
                    "coef_reference_scale": (beta * scales / scale).tolist(),
                    "constant_features": [name for j, name in enumerate(names) if np.ptp(z[:, j]) <= ZERO_TOL],
                    "intercept_raw": float(fit["intercept"] - np.sum(beta * mean / scale)),
                    "intercept_comparison_caveat": "Changing medians prevents a global intercept equivalence on rows with missing inputs."})
        if not fit["converged"]:
            failures.append({"identity": identity, "reason": "penalised gradient exceeds tolerance", "gradient_max_abs": fit["gradient_max_abs"]})
        return fit
    for index, omitted in enumerate(all_gps):
        if progress:
            progress("coefficient_jackknife", index + 1, len(all_gps))
        mask = np.array([g != omitted for g in groups])
        try:
            jackknife.append(execute(mask, {"omitted_gp": list(omitted)}))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            failures.append({"identity": {"omitted_gp": list(omitted)}, "reason": str(error)})
    for end_year in sorted({g[0] for g in groups}):
        mask = np.array([g[0] <= end_year for g in groups])
        identity = {"training_seasons": sorted({g[0] for g, keep in zip(groups, mask) if keep})}
        try:
            expanding.append(execute(mask, identity))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            failures.append({"identity": identity, "reason": str(error)})
    successful = [fit for fit in jackknife if fit["converged"]]
    summary = []
    for j, name in enumerate(names):
        values = np.array([fit["coef_reference_scale"][j] for fit in successful])
        nonzero = np.abs(values) > SIGN_TOL
        ref_sign = int(np.sign(reference[j])) if abs(reference[j]) > SIGN_TOL else 0
        row = {"feature": name, "reference_coefficient": float(reference[j]),
               "n_jackknife_successful": len(values), "reference_sign": ref_sign,
               "zero_count": int(np.sum(~nonzero)),
               "sign_flip_count": int(np.sum(nonzero & (np.sign(values) != ref_sign))) if ref_sign else None,
               "constant_in_jackknife_count": sum(name in fit["constant_features"] for fit in successful),
               "jackknife_mean": float(values.mean()) if len(values) else None,
               "jackknife_sd": float(values.std(ddof=1)) if len(values) > 1 else None,
               "jackknife_min": float(values.min()) if len(values) else None,
               "jackknife_max": float(values.max()) if len(values) else None,
               "jackknife_max_abs_change": float(np.max(np.abs(values - reference[j]))) if len(values) else None,
               "jackknife_q025": float(np.quantile(values, 0.025)) if len(values) else None,
               "jackknife_q975": float(np.quantile(values, 0.975)) if len(values) else None}
        summary.append(row)
    return {"baseline": baseline, "feature_names": names, "feature_summary": summary,
            "jackknife": jackknife, "expanding": expanding, "failures": failures,
            "n_rows": len(raw), "n_gp": len(all_gps),
            "coefficient_comparison_units": "frozen-training standard deviations",
            "interpretation": "descriptive sensitivity, not confidence intervals or causal effects",
            "redundancy_caveat": "Ridge shares coefficients among redundant columns; individual coefficients do not identify separate effects.",
            "sign_zero_tolerance": SIGN_TOL,
            "training_seasons": sorted({g[0] for g in groups})}


def _calibration_fit(p, y, groups, cluster=True):
    """Return calibration point estimates with explicit fit-failure statuses."""
    import statsmodels.api as sm
    from statsmodels.tools.sm_exceptions import PerfectSeparationError

    logs = logit(p)
    group_labels = {group: j for j, group in enumerate(sorted(set(groups)))}
    codes = np.array([group_labels[g] for g in groups])
    output = {}
    for kind in ("joint", "calibration_in_the_large"):
        if len(np.unique(y)) < 2:
            output[kind] = {"status": "not_estimable", "reason": "target has only one class", "warnings": []}
            continue
        x = np.column_stack([np.ones(len(p)), logs]) if kind == "joint" else np.ones((len(p), 1))
        if np.linalg.matrix_rank(x) < x.shape[1]:
            output[kind] = {"status": "not_estimable", "reason": "calibration design is rank deficient (constant logit)", "warnings": []}
            continue
        offset = logs if kind == "calibration_in_the_large" else None
        model = sm.GLM(y, x, family=sm.families.Binomial(), offset=offset)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                fit = model.fit(maxiter=200, tol=1e-10)
                messages = _warning_messages(caught)
                bad_warning = any("PerfectSeparation" in m or "RuntimeWarning" in m for m in messages)
                if not fit.converged or not np.isfinite(fit.params).all() or bad_warning:
                    output[kind] = {"status": "not_estimable", "reason": "nonconvergence, separation, or numerical warning", "warnings": messages}
                    continue
                result = {"status": "ok", "intercept": float(fit.params[0]), "warnings": messages,
                          "n_rows": len(p), "n_gp": len(group_labels),
                          "ci95_cluster": None, "cluster_ci_status": "not_requested"}
                if kind == "joint":
                    result["slope"] = float(fit.params[1])
                if cluster and len(group_labels) >= 2:
                    try:
                        robust = model.fit(maxiter=200, tol=1e-10, cov_type="cluster", cov_kwds={"groups": codes, "use_correction": True})
                        covariance = np.asarray(robust.cov_params())
                        if not np.isfinite(covariance).all() or np.linalg.matrix_rank(covariance) < len(robust.params):
                            raise ValueError("clustered covariance is singular or non-finite")
                        intervals = np.asarray(robust.conf_int(alpha=0.05))
                        if not robust.converged or not np.isfinite(intervals).all():
                            raise ValueError("non-finite clustered covariance")
                        result["ci95_cluster"] = {"intercept": intervals[0].tolist()}
                        if kind == "joint":
                            result["ci95_cluster"]["slope"] = intervals[1].tolist()
                        result["cluster_covariance"] = covariance.tolist()
                        result["cluster_ci_status"] = "ok"
                    except (ValueError, np.linalg.LinAlgError, FloatingPointError, ZeroDivisionError, PerfectSeparationError) as error:
                        result["cluster_ci_status"] = "not_estimable"
                        result["cluster_ci_reason"] = str(error)
                elif cluster:
                    result["cluster_ci_status"] = "not_estimable"
                    result["cluster_ci_reason"] = "fewer than two GPs"
                result["warnings"] = _warning_messages(caught)
                output[kind] = result
            except (ValueError, np.linalg.LinAlgError, FloatingPointError, ZeroDivisionError, PerfectSeparationError) as error:
                output[kind] = {"status": "not_estimable", "reason": str(error), "warnings": _warning_messages(caught)}
    return output


def calibration_audit(probabilities, y, gp_ids, bootstrap_reps=2000, seed=42, progress=None):
    """Audit frozen out-of-training probabilities, without recalibrating them.

    Joint ideal: calibration intercept=0 and slope=1. Calibration-in-the-large
    instead fixes slope=1 using a logit offset. Cluster intervals are marginal
    normal intervals, assume independent GPs, and are not a joint test of the
    ideal pair. Moving blocks of two adjacent calendar rounds are resampled
    within each season, conditional on the existing probabilities. The bootstrap
    does not include original-model training or feature-selection uncertainty.

    Endpoints remain in scores and bins, but are counted and excluded from logit
    diagnostics; they are never silently clipped. A season with missing calendar
    rounds is refused for block inference rather than treating distant races as
    adjacent or selectively dropping singleton runs.
    """
    p = np.array(probabilities, dtype=float, copy=True)
    if p.ndim != 1 or not len(p) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("finite probabilities in [0,1] are required")
    target = _binary(y, len(p))
    groups = _groups(gp_ids, len(p))
    if isinstance(bootstrap_reps, bool) or int(bootstrap_reps) != bootstrap_reps or bootstrap_reps < 0:
        raise ValueError("bootstrap_reps must be a nonnegative integer")
    bins = []
    for i in range(10):
        mask = (np.minimum((p * 10).astype(int), 9) == i)
        bins.append({"index": i, "lower": i / 10, "upper": (i + 1) / 10,
                     "n": int(mask.sum()), "mean_probability": float(p[mask].mean()) if mask.any() else None,
                     "observed_rate": float(target[mask].mean()) if mask.any() else None})
    assigned = np.where(target == 1, p, 1 - p)
    impossible = int((assigned == 0).sum())
    log_loss = float(-np.log(assigned).mean()) if not impossible else None
    interior = (p > 0) & (p < 1)
    ps, ys = p[interior], target[interior]
    gs = [g for g, keep in zip(groups, interior) if keep]
    calibration = _calibration_fit(ps, ys, gs) if len(ps) else {
        name: {"status": "not_estimable", "reason": "no interior probabilities", "warnings": []}
        for name in ("joint", "calibration_in_the_large")}
    output = {"n_rows": len(p), "n_gp": len(set(groups)), "n_logit_rows": len(ps),
              "excluded_endpoint_rows": int((~interior).sum()),
              "brier": float(np.mean((p - target)**2)), "log_loss": log_loss,
              "log_loss_infinite": bool(impossible), "impossible_outcome_count": impossible,
              "mean_probability": float(p.mean()), "observed_rate": float(target.mean()),
              "bins": bins, **calibration}
    gp_metrics = []
    for season, race in sorted(set(groups)):
        mask = np.array([group == (season, race) for group in groups])
        gp_assigned = assigned[mask]
        gp_impossible = bool((gp_assigned == 0).any())
        gp_metrics.append({"season": season, "round": race, "n": int(mask.sum()),
                           "brier": float(np.mean((p[mask] - target[mask])**2)),
                           "log_loss": None if gp_impossible else float(-np.log(gp_assigned).mean()),
                           "log_loss_infinite": gp_impossible})
    output["gp_metrics"] = gp_metrics
    output["brier_mean_gp"] = float(np.mean([metric["brier"] for metric in gp_metrics]))
    output["log_loss_mean_gp"] = None if impossible else float(np.mean([metric["log_loss"] for metric in gp_metrics]))
    seasons = []
    issue = None
    for year in sorted({g[0] for g in gs}):
        gps = sorted({g for g in gs if g[0] == year})
        blocks = [[list(a), list(b)] for a, b in zip(gps[:-1], gps[1:]) if b[1] == a[1] + 1]
        seasons.append({"season": year, "gps": [list(g) for g in gps], "n_gp": len(gps), "blocks": blocks})
        if len(gps) < 2 or len(blocks) != len(gps) - 1:
            issue = "a season has fewer than two GPs or gaps between calendar rounds"
    bootstrap = {"status": "not_estimable", "seed": int(seed), "block_length": 2,
                 "requested_replicates": int(bootstrap_reps), "successful_replicates": 0,
                 "failed_replicates": 0, "season_blocks": seasons,
                 "intervals": None, "failures": [],
                 "minimum_success_fraction": 0.95,
                 "conditional_on_frozen_probabilities": True,
                 "interval_interpretation": "marginal percentile intervals; not a joint test of intercept=0 and slope=1"}
    output["bootstrap"] = bootstrap
    if not seasons:
        issue = "no interior probabilities for block resampling"
    if not bootstrap_reps:
        bootstrap.update(status="not_requested", reason="zero bootstrap replicates requested")
        return output
    if issue:
        bootstrap["reason"] = issue
        return output
    if calibration["joint"]["status"] != "ok":
        bootstrap["reason"] = "joint calibration is not estimable"
        return output
    row_indices = {gp: np.array([i for i, g in enumerate(gs) if g == gp], dtype=int) for gp in set(gs)}
    rng = np.random.RandomState(seed)
    draws = []
    failure_counts = Counter()
    for rep in range(int(bootstrap_reps)):
        if progress and (rep == 0 or (rep + 1) % 100 == 0 or rep + 1 == bootstrap_reps):
            progress("calibration_bootstrap", rep + 1, int(bootstrap_reps))
        indices, sampled_groups = [], []
        for season in seasons:
            gp_list = [tuple(g) for g in season["gps"]]
            sampled = []
            while len(sampled) < len(gp_list):
                start = rng.randint(len(gp_list) - 1)
                sampled.extend(gp_list[start:start + 2])
            for gp in sampled[:len(gp_list)]:
                indices.extend(row_indices[gp])
                sampled_groups.extend([gp] * len(row_indices[gp]))
        fitted = _calibration_fit(ps[indices], ys[indices], sampled_groups, cluster=False)
        if all(fitted[k]["status"] == "ok" for k in ("joint", "calibration_in_the_large")):
            draws.append([fitted["joint"]["intercept"], fitted["joint"]["slope"], fitted["calibration_in_the_large"]["intercept"]])
        else:
            reasons = "; ".join(sorted({v.get("reason", "unknown fit failure") for v in fitted.values() if v["status"] != "ok"}))
            failure_counts[reasons] += 1
    bootstrap["successful_replicates"] = len(draws)
    bootstrap["failed_replicates"] = int(bootstrap_reps) - len(draws)
    bootstrap["failures"] = [{"reason": reason, "count": count} for reason, count in sorted(failure_counts.items())]
    if len(draws) >= max(2, int(np.ceil(0.95 * bootstrap_reps))):
        intervals = np.quantile(np.asarray(draws), [0.025, 0.975], axis=0).T
        bootstrap["intervals"] = {name: intervals[j].tolist() for j, name in enumerate(("intercept", "slope", "calibration_in_the_large"))}
        bootstrap["status"] = "ok"
        bootstrap["conditional_on_successful_fits"] = bool(failure_counts)
        bootstrap["degenerate_intervals"] = [name for name, interval in bootstrap["intervals"].items() if abs(interval[1] - interval[0]) <= ZERO_TOL]
        bootstrap["interval_status"] = {name: "ok" for name in bootstrap["intervals"]}
        for name in bootstrap["degenerate_intervals"]:
            bootstrap["intervals"][name] = None
            bootstrap["interval_status"][name] = "not_estimable: degenerate bootstrap distribution"
        if len(bootstrap["degenerate_intervals"]) == 3:
            bootstrap["status"] = "not_estimable"
            bootstrap["reason"] = "all bootstrap distributions are degenerate; intervals withheld"
    else:
        bootstrap["reason"] = "fewer than 95% requested replicates succeeded; percentile intervals withheld"
    return output
