"""Execute the isolated, predeclared temporal v2 calibration experiment."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.special import expit, logit
from threadpoolctl import threadpool_limits

from .run_statsmodels_audit import PINNED_VERSIONS, _csv, _json, _sha, load_calibration, snapshot_protected
from .statsmodels_audit import calibration_audit


PRIMARY = "v2_intercept_calibrated"
RAW = "v2_uncalibrated"
METHODS = ("v1_temporal", "q_probability", RAW, PRIMARY, "v2_sigmoid_calibrated")
PROTOCOLS = ("docs/experimento_v2_calibracao_20261102.md", "docs/en/V2_CALIBRATION_20261102.md")
FROZEN_PATHS = PROTOCOLS + (
    "pitwall/research/calibration_v2.py", "pitwall/research/run_calibration_v2.py",
    "tests/test_calibration_v2.py", "pitwall/research/statsmodels_audit.py",
    "pitwall/research/run_statsmodels_audit.py", "requirements_statsmodels_audit.txt",
    "requirements_modelo_v1.txt", "data/preparado/treino.csv", "data/preparado/validacao.csv",
    "data/preparado/teste_final_reservado.csv", "data/preparado/colunas.json",
    "models/modelo_v1/metadados.json", "reports/modelo_v1/previsoes_validacao.csv",
    "reports/avaliacao_final_v1/previsoes_pre_corrida.csv", "reports/avaliacao_final_v1/avaliacao_por_piloto.csv",
)


def snapshot(root, baseline):
    root = Path(root)
    files = snapshot_protected(root)
    for relative in baseline.get("extra_protected_roots", []):
        path = root / relative
        for file in ([path] if path.is_file() else path.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                files[str(file.relative_to(root))] = _sha(file)
    return files


def preservation(root, baseline):
    current, before = snapshot(root, baseline), baseline["files"]
    changed = sorted(name for name in current.keys() & before.keys() if current[name] != before[name])
    missing, new = sorted(before.keys() - current.keys()), sorted(current.keys() - before.keys())
    return {"status": "preserved" if not (changed or missing or new) else "divergent", "checked_files": len(before), "changed": changed, "missing": missing, "new": new}


def key(row):
    return int(row["temporada"]), int(row["rodada"]), row["piloto_id"]


def calibration_in_large(p, y):
    """Solve the binomial offset-GLM score, independently of its optimizer."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    if not len(p) or len(np.unique(y)) != 2 or not np.isfinite(p).all() or np.any((p <= 0) | (p >= 1)):
        return None
    z = logit(p)
    return float(brentq(lambda intercept: float(np.sum(expit(z + intercept) - y)), -1000, 1000, xtol=1e-12))


def _summary(lines):
    known = [r for r in lines if r["podio"] is not None]
    if not known:
        return None, [], None
    p = np.array([r["probabilidade"] for r in known], float)
    y = np.array([r["podio"] for r in known], float)
    gps = [key(r)[:2] for r in known]
    diag = calibration_audit(p, y, gps, bootstrap_reps=0)
    scores = diag["gp_metrics"]
    return {"n": len(known), "n_gp": len(set(gps)), "brier": diag["brier"], "log_loss": diag["log_loss"],
            "brier_mean_gp": diag["brier_mean_gp"], "log_loss_mean_gp": diag["log_loss_mean_gp"],
            "citl": diag["calibration_in_the_large"].get("intercept"),
            "joint_intercept": diag["joint"].get("intercept"), "slope": diag["joint"].get("slope"),
            "mean_probability": diag["mean_probability"], "observed_rate": diag["observed_rate"]}, scores, diag


def evaluate_methods(rows, predictions, methods=METHODS):
    """Use identical known-target populations, never a favourable intersection."""
    expected = {key(r): r for r in rows}
    if len(expected) != len(rows) or any(k[0] not in (2022, 2023, 2024, 2025) for k in expected):
        raise ValueError("evaluation requires unique retrospective outer-fold rows")
    eligible = {k for k, r in expected.items() if r["elegivel_previsao"]}
    indexed = {method: {} for method in methods}
    seen = set()
    for p in predictions:
        method, k = p["metodo"], key(p)
        if method not in indexed:
            continue
        if k not in expected or (method, k) in seen:
            raise ValueError("duplicate or unexpected prediction identity")
        seen.add((method, k))
        probability = p.get("probabilidade")
        if probability is not None:
            if k not in eligible or not np.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("invalid probability/eligibility")
            if p["podio"] != expected[k]["podio"]:
                raise ValueError("prediction/outcome target mismatch")
            indexed[method][k] = p
    results, gp_scores, diagnostics = {}, {}, {}
    gp_rows = defaultdict(list)
    for k, row in expected.items():
        gp_rows[k[:2]].append(row)
    ranking_q = []
    for gp, members in sorted(gp_rows.items()):
        valid = all(r["elegivel_previsao"] and r["podio"] is not None for r in members) and sum(r["podio"] or 0 for r in members) == 3
        def q_order(row):
            pos = row["posicao_classificacao"]
            return (float("inf") if pos is None or not np.isfinite(pos) else pos, row["piloto_id"])
        ranking_q.append({"temporada": gp[0], "rodada": gp[1], "avaliavel": valid,
                          "acertos": sum(r["podio"] for r in sorted(members, key=q_order)[:3]) if valid else None})
    for method in methods:
        mapping = indexed[method]
        missing = sorted(eligible - mapping.keys())
        if missing:
            results[method] = {"status": "cobertura_insuficiente", "missing_keys": [list(k) for k in missing]}
            continue
        lines = [mapping[k] for k in sorted(eligible)]
        overall, scores, diag = _summary(lines)
        folds = {}
        for year in sorted({k[0] for k in expected}):
            summary, _, _ = _summary([r for r in lines if int(r["temporada"]) == year])
            folds[str(year)] = summary
        unscored = [year for year, summary in folds.items() if summary is None]
        if overall is None or unscored:
            results[method] = {
                "status": "cobertura_insuficiente", "reason": "no known eligible targets in an evaluation fold",
                "n_eligible": len(eligible), "unscored_folds": unscored,
                "unknown_eligible_targets": sum(expected[k]["podio"] is None for k in eligible),
                "overall": overall, "folds": folds,
            }
            continue
        rankings = []
        for q in ranking_q:
            gp = (q["temporada"], q["rodada"])
            members = gp_rows[gp]
            top = sorted((mapping[key(r)] for r in members), key=lambda p: (-p["probabilidade"], p["piloto_id"]))[:3] if q["avaliavel"] else []
            rankings.append({"temporada": gp[0], "rodada": gp[1], "avaliavel": q["avaliavel"],
                             "acertos": sum(p["podio"] for p in top) if q["avaliavel"] else None})
        comparable = [r for r in rankings if r["avaliavel"]]
        q_valid = [r for r in ranking_q if r["avaliavel"]]
        overall.update({"top3_n_gp": len(comparable), "top3_mean": float(np.mean([r["acertos"] for r in comparable])) if comparable else None,
                        "complete_podiums": sum(r["acertos"] == 3 for r in comparable),
                        "qualifying_top3_mean": float(np.mean([r["acertos"] for r in q_valid])) if q_valid else None,
                        "qualifying_complete_podiums": sum(r["acertos"] == 3 for r in q_valid)})
        results[method] = {"status": "complete", "overall": overall, "folds": folds, "rankings": rankings,
                           "n_eligible": len(eligible), "unknown_eligible_targets": sum(expected[k]["podio"] is None for k in eligible)}
        gp_scores[method], diagnostics[method] = scores, diag
    return {"methods": results, "gp_scores": gp_scores, "calibration": diagnostics, "qualifying_rankings": ranking_q}


def _sample_gps(gps, rng):
    sampled = []
    for year in sorted({gp[0] for gp in gps}):
        season = sorted(gp for gp in gps if gp[0] == year)
        if len(season) < 2 or any(b[1] != a[1]+1 for a, b in zip(season, season[1:])):
            raise ValueError("paired block interval requires consecutive calendar rounds within each season")
        draw = []
        while len(draw) < len(season):
            start = rng.randint(len(season)-1)
            draw.extend(season[start:start+2])
        sampled.extend(draw[:len(season)])
    return sampled


def paired_interval(scores_a, scores_b, repetitions=2000):
    a = {(r["season"], r["round"]): r for r in scores_a}
    b = {(r["season"], r["round"]): r for r in scores_b}
    if a.keys() != b.keys() or any(a[k]["n"] != b[k]["n"] for k in a):
        return {"status": "cobertura_insuficiente"}
    gps = sorted(a)
    if not gps or any(a[k]["log_loss"] is None or b[k]["log_loss"] is None for k in gps):
        return {"status": "not_estimable"}
    rng = np.random.RandomState(42)
    draws = []
    try:
        for _ in range(repetitions):
            sampled = _sample_gps(gps, rng)
            draws.append([np.mean([a[k][metric]-b[k][metric] for k in sampled]) for metric in ("brier", "log_loss")])
    except ValueError as error:
        return {"status": "not_estimable", "reason": str(error)}
    intervals = np.quantile(draws, [0.025, 0.975], axis=0).T
    result = {"status": "ok", "n_gp": len(gps), "replicates": repetitions, "seed": 42, "block_length": 2, "folds": {}}
    for i, metric in enumerate(("brier", "log_loss")):
        result["delta_"+metric] = float(np.mean([a[k][metric]-b[k][metric] for k in gps]))
        result["ci95_"+metric] = intervals[i].tolist() if intervals[i, 1]-intervals[i, 0] > 1e-12 else None
    for year in sorted({gp[0] for gp in gps}):
        subset = [gp for gp in gps if gp[0] == year]
        result["folds"][str(year)] = {metric: float(np.mean([a[k][metric]-b[k][metric] for k in subset])) for metric in ("brier", "log_loss")}
    result["conditional_on_fitted_predictions"] = True
    return result


def calibration_contrast(predictions, repetitions=2000):
    indexed = {}
    for method in (PRIMARY, RAW):
        indexed[method] = {key(p): p for p in predictions if p["metodo"] == method and p.get("probabilidade") is not None and p["podio"] is not None}
    a, b = indexed[PRIMARY], indexed[RAW]
    if a.keys() != b.keys() or not a:
        return {"status": "cobertura_insuficiente"}
    keys = sorted(a)
    groups = defaultdict(list)
    for i, k in enumerate(keys): groups[k[:2]].append(i)
    pa, pb, y = [np.array(v) for v in ([a[k]["probabilidade"] for k in keys], [b[k]["probabilidade"] for k in keys], [a[k]["podio"] for k in keys])]
    ca, cb = calibration_in_large(pa, y), calibration_in_large(pb, y)
    if ca is None or cb is None:
        return {"status": "not_estimable"}
    rng, draws, failed = np.random.RandomState(42), [], 0
    try:
        for _ in range(repetitions):
            sample = _sample_gps(sorted(groups), rng)
            ix = np.concatenate([groups[g] for g in sample])
            da, db = calibration_in_large(pa[ix], y[ix]), calibration_in_large(pb[ix], y[ix])
            if da is None or db is None: failed += 1
            else: draws.append(abs(da)-abs(db))
    except ValueError as error:
        return {"status": "not_estimable", "reason": str(error)}
    interval = np.quantile(draws, [0.025, 0.975]).tolist() if len(draws) >= 0.95*repetitions else None
    if interval and interval[1]-interval[0] <= 1e-12: interval = None
    return {"status": "ok" if interval else "not_estimable", "delta_abs_citl": abs(ca)-abs(cb), "ci95_delta_abs_citl": interval,
            "primary_citl": ca, "raw_citl": cb, "successful_replicates": len(draws), "failed_replicates": failed,
            "seed": 42, "block_length": 2, "conditional_on_fitted_predictions": True}


def comparisons(evaluation, predictions):
    pairs = [(PRIMARY, "v1_temporal"), (PRIMARY, "q_probability"), (PRIMARY, RAW), (RAW, "v1_temporal"), ("v2_sigmoid_calibrated", RAW)]
    results = []
    for candidate, reference in pairs:
        if any(evaluation["methods"][m]["status"] != "complete" for m in (candidate, reference)):
            results.append({"candidate": candidate, "reference": reference, "status": "cobertura_insuficiente"})
            continue
        result = paired_interval(evaluation["gp_scores"][candidate], evaluation["gp_scores"][reference])
        result.update(candidate=candidate, reference=reference)
        if result["status"] == "ok":
            favourable = sum(f["brier"] < 0 for f in result["folds"].values())
            supported = result["delta_brier"] <= -0.002 and result["ci95_brier"] and result["ci95_brier"][1] < 0 and result["delta_log_loss"] <= 0 and favourable >= 3
            result["favourable_folds"] = favourable
            result["conclusion"] = "melhora_sustentada" if supported else ("sem_ganho" if result["delta_brier"] >= 0 else "inconclusivo")
        results.append(result)
    global_cal = calibration_contrast(predictions)
    if global_cal.get("status") == "ok" and all(evaluation["methods"][m]["status"] == "complete" for m in (PRIMARY, RAW)):
        primary, raw = [evaluation["methods"][m] for m in (PRIMARY, RAW)]
        favourable = sum(abs(primary["folds"][y]["citl"]) < abs(raw["folds"][y]["citl"]) for y in primary["folds"] if primary["folds"][y]["citl"] is not None and raw["folds"][y]["citl"] is not None)
        nonworse = primary["overall"]["brier_mean_gp"] <= raw["overall"]["brier_mean_gp"] and primary["overall"]["log_loss_mean_gp"] <= raw["overall"]["log_loss_mean_gp"]
        global_cal["favourable_folds"] = favourable
        global_cal["conclusion"] = "melhora_global_sustentada" if global_cal["delta_abs_citl"] < 0 and global_cal["ci95_delta_abs_citl"][1] < 0 and favourable >= 3 and nonworse else "inconclusivo"
    primary_contrasts = [r for r in results if r["candidate"] == PRIMARY and r["reference"] in ("v1_temporal", "q_probability")]
    return {"paired": results, "global_calibration": global_cal,
            "predictive_criteria_met": all(r.get("conclusion") == "melhora_sustentada" for r in primary_contrasts) and len(primary_contrasts) == 2,
            "automatic_promotion": False}


def _plots(destination, evaluation):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for method, data in evaluation["methods"].items():
        if data["status"] != "complete": continue
        years = list(data["folds"])
        axes[0].plot(years, [data["folds"][y]["brier_mean_gp"] for y in years], marker="o", label=method)
        axes[1].plot(years, [abs(data["folds"][y]["citl"]) if data["folds"][y]["citl"] is not None else np.nan for y in years], marker="o", label=method)
    axes[0].set_title("Brier médio por GP / GP-mean Brier")
    axes[1].set_title("Viés global / Global bias: |CITL|")
    for ax in axes:
        ax.set_xlabel("Ano avaliado / Evaluated year"); ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Validação temporal / Temporal validation — menor é melhor / lower is better")
    fig.savefig(destination / "temporal_comparison.png", dpi=160)
    plt.close(fig)


def _report(destination, evaluation, contrasts, frozen_v1, engine, language):
    en = language == "en"
    fmt = lambda v: "N/A" if v is None else "{:.6f}".format(v)
    lines = ["# " + ("V2 temporal calibration experiment" if en else "Experimento v2 de calibração temporal"), "", "Created by: MBPaschoal", "Status: executed locally; retrospective development", "Type: experiment report", "Date: 2026-11-02", "", "[Português](relatorio.md) · [English](report.en.md)", "",
             "Primary: `v2_intercept_calibrated`. Secondary: `v2_sigmoid_calibrated`.", "",
             ("Outer evaluation 2022–2025 uses prior-year expanding training. Calibration learns only from inner temporal OOF predictions. These years were already explored; they are not untouched testing. Frozen v1 and recorded probabilities are preserved." if en else "Avaliações externas 2022–2025 usam treino cumulativo nos anos anteriores. Calibração aprende somente com previsões OOF temporais internas. Esses anos já foram explorados; não são teste intocado. V1 e probabilidades registradas preservados."), "",
             "| Método / Method | N | GPs | Brier GP | Log loss GP | CITL | Inclinação / Slope | Top 3 | Pódios / Podiums |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for method, data in evaluation["methods"].items():
        if data["status"] != "complete": lines += ["| {} | cobertura insuficiente | | | | | | | |".format(method)]; continue
        r = data["overall"]
        lines += ["| {} | {} | {} | {} | {} | {} | {} | {} | {}/{} |".format(method, r["n"], r["n_gp"], fmt(r["brier_mean_gp"]), fmt(r["log_loss_mean_gp"]), fmt(r["citl"]), fmt(r["slope"]), fmt(r["top3_mean"]), r["complete_podiums"], r["top3_n_gp"])]
    first = next((d["overall"] for d in evaluation["methods"].values() if d["status"] == "complete"), None)
    if first: lines += ["", "Ranking Q: {} correct members per GP; {}/{} complete podiums. / integrantes corretos por GP; pódios completos.".format(fmt(first["qualifying_top3_mean"]), first["qualifying_complete_podiums"], first["top3_n_gp"])]
    lines += ["", "## " + ("Paired contrasts" if en else "Contrastes pareados"), "", "| Candidato / Candidate | Referência / Reference | Δ Brier GP | IC95% / CI95% | Δ log loss GP | Folds favoráveis / Favourable folds | Conclusão / Conclusion |", "|---|---|---:|---|---:|---:|---|"]
    for r in contrasts["paired"]:
        interval = r.get("ci95_brier")
        lines += ["| {} | {} | {} | {} | {} | {} | {} |".format(r["candidate"], r["reference"], fmt(r.get("delta_brier")), str(interval) if interval else "N/A", fmt(r.get("delta_log_loss")), r.get("favourable_folds", "N/A"), r.get("conclusion", r["status"]))]
    lines += ["", "```json", json.dumps(contrasts["global_calibration"], ensure_ascii=False, indent=2), "```", "", ("Predictive criteria met: {}. No automatic promotion." if en else "Critérios preditivos atendidos: {}. Sem promoção automática.").format(contrasts["predictive_criteria_met"]), "",
              "## " + ("Per-fold results" if en else "Resultados por fold"), "", "| Método / Method | Avaliação / Evaluation | N | Brier GP | Log loss GP | CITL |", "|---|---:|---:|---:|---:|---:|"]
    for method, data in evaluation["methods"].items():
        for year, r in data.get("folds", {}).items():
            if r is None:
                lines += ["| {} | {} | 0 | N/A | N/A | N/A |".format(method, year)]
                continue
            lines += ["| {} | {} | {} | {} | {} | {} |".format(method, year, r["n"], fmt(r["brier_mean_gp"]), fmt(r["log_loss_mean_gp"]), fmt(r["citl"]))]
    lines += ["", "![Temporal comparison](temporal_comparison.png)", "", "## " + ("Actual preserved v1, secondary 2024/2025 comparison" if en else "V1 real preservado, comparação secundária 2024/2025"), "", "| Método / Method | N | Brier GP | Log loss GP | CITL |", "|---|---:|---:|---:|---:|"]
    for method, data in frozen_v1["methods"].items():
        if data["status"] == "complete":
            r=data["overall"]; lines += ["| {} | {} | {} | {} | {} |".format(method, r["n"], fmt(r["brier_mean_gp"]), fmt(r["log_loss_mean_gp"]), fmt(r["citl"]))]
    lines += ["", ("The actual saved v1 trained on 2021–2023. Temporal-v1 uses all prior years, including 2024 for 2025 evaluation, so it has a different information budget. Neither saved model nor recorded predictions were changed." if en else "O v1 real salvo foi treinado em 2021–2023. A réplica temporal usa todos os anos anteriores, incluindo 2024 ao avaliar 2025; os orçamentos de informação são diferentes. Modelo salvo e previsões registradas não foram alterados."), "",
              "## " + ("Limits and provenance" if en else "Limites e proveniência"), "", ("Calibration is monotonic and preserves the reduced base ranking. OOF models have smaller training samples than the final refit. Intervals condition on fitted outer predictions; two-GP blocks can miss longer dependence. Global bias near zero does not certify the whole curve. No 2026 fitting or test-driven selection. All failed fits and coverage are retained." if en else "As calibrações monotônicas preservam o ranking da base reduzida. Modelos OOF têm treino menor que o refit final. ICs condicionam nas previsões externas ajustadas; blocos de dois GPs podem perder dependência longa. Viés global próximo de zero não certifica a curva inteira. Sem ajuste com 2026 ou seleção pelos resultados de avaliação. Falhas e cobertura ficam registradas."), "",
              "[Evaluation](evaluation.json) · [Contrasts](comparisons.json) · [Fits/OOF/coverage](experiment.json) · [Predictions](predictions.csv) · [Frozen execution](execution_frozen.json) · [Preservation](preservation.json) · [Manifest](manifest.json)", ""]
    (destination / ("report.en.md" if en else "relatorio.md")).write_text("\n".join(lines))


def run(root, destination, baseline_path):
    from .calibration_v2 import load_dataset, run_experiment
    root, destination = Path(root).resolve(), Path(destination).resolve()
    allowed = root / "reports/modelo_v2_calibracao_20261102"
    if destination.exists() or destination == allowed or not destination.is_relative_to(allowed):
        raise ValueError("output must be a new experiment directory, never sources")
    baseline = json.loads(Path(baseline_path).read_text())
    before = preservation(root, baseline)
    if before["status"] != "preserved": raise ValueError("protected files differ before experiment: {}".format(before))
    versions = {p: importlib.metadata.version(p) for p in PINNED_VERSIONS}
    if versions != PINNED_VERSIONS: raise ValueError("research environment differs from pinned versions")
    destination.mkdir(parents=True)
    frozen = {"created_utc": datetime.now(timezone.utc).isoformat(), "packages": versions, "native_threads": 1,
              "configuration": {"C": 1, "primary": PRIMARY, "warmup_gps": 8, "inner_block_gps": 4, "outer_years": [2022,2023,2024,2025], "bootstrap_replicates": 2000, "seed": 42, "block_length": 2},
              "hashes": {name: _sha(root/name) for name in FROZEN_PATHS}}
    _json(destination/"execution_frozen.json", frozen)
    try:
        with threadpool_limits(limits=1):
            rows = load_dataset(root)
            engine = run_experiment(rows, progress=lambda *args: print(*args, flush=True))
            _json(destination/"experiment.json", engine)
            predictions = engine["predictions"]
            _csv(destination/"predictions.csv", predictions)
            eval_rows = [r for r in rows if r["temporada"] in (2022,2023,2024,2025)]
            evaluation = evaluate_methods(eval_rows, predictions)
            _json(destination/"evaluation.json", evaluation)
            print("paired bootstrap and global calibration contrast", flush=True)
            contrasts = comparisons(evaluation, predictions)
            _json(destination/"comparisons.json", contrasts)
            secondary_predictions = [p for p in predictions if p["temporada"] in (2024,2025)]
            for year in (2024,2025):
                # Source rows retain stable keys; outcome joins are checked by the audited loader.
                p,y,gps,_ = load_calibration(root,year)
                path = root/("reports/modelo_v1/previsoes_validacao.csv" if year==2024 else "reports/avaliacao_final_v1/avaliacao_por_piloto.csv")
                from .run_statsmodels_audit import _rows, _flag
                for row in _rows(path):
                    if _flag(row["elegivel_previsao"]):
                        secondary_predictions.append({"metodo":"v1_frozen","temporada":year,"rodada":int(row["rodada"]),"piloto_id":row["piloto_id"],"probabilidade":float(row["probabilidade_modelo"]),"podio":int(row["podio"]) if _flag(row["alvo_conhecido"]) else None})
            secondary = evaluate_methods([r for r in eval_rows if r["temporada"] in (2024,2025)],secondary_predictions,methods=METHODS+("v1_frozen",))
            _json(destination/"frozen_v1_comparison.json", secondary)
            _plots(destination,evaluation)
            _report(destination,evaluation,contrasts,secondary,engine,"pt"); _report(destination,evaluation,contrasts,secondary,engine,"en")
        after=preservation(root,baseline)
        _json(destination/"preservation.json",after)
        if after["status"]!="preserved": raise ValueError("protected sources changed during experiment")
        if any(_sha(root/name)!=digest for name,digest in frozen["hashes"].items()): raise ValueError("frozen experiment code/protocol/input changed during execution")
        manifest={"schema":"pitwall-v2-calibration-v1","status":"completed","protected_files":after["checked_files"],"predictive_criteria_met":contrasts["predictive_criteria_met"],"automatic_promotion":False,"files":{p.name:_sha(p) for p in sorted(destination.iterdir()) if p.is_file()}}
        _json(destination/"manifest.json",manifest)
        return manifest
    except Exception as error:
        _json(destination/"failure.json",{"type":type(error).__name__,"message":str(error),"preservation":preservation(root,baseline)})
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination",type=Path)
    parser.add_argument("--preservation-baseline",type=Path)
    args=parser.parse_args()
    parent=args.root/"reports/modelo_v2_calibracao_20261102"
    destination=args.destination or parent/datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    result=run(args.root,destination,args.preservation_baseline or parent/"protected_before.json")
    print(json.dumps({"destination":str(destination),"status":result["status"],"predictive_criteria_met":result["predictive_criteria_met"]}))


if __name__=="__main__": main()
