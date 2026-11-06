"""Offline, isolated audit of frozen v1 inputs, coefficients and probabilities.

Run explicitly with ``python -m pitwall.research.run_statsmodels_audit``.
The dashboard does not import this module. No v1 trainer/joblib is loaded and
the only outcome-model fits are separate diagnostic research replicas.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np
from scipy.special import expit
from threadpoolctl import threadpool_limits

from .statsmodels_audit import audit_design, calibration_audit, coefficient_stability


FEATURES = (
    "posicao_classificacao", "posicao_classificacao_repetida",
    "classificacao_ausente", "posicao_classificacao_ausente",
    "media_posicao_final_5", "taxa_podios_5", "n_posicoes_5", "n_podios_5",
    "media_pontos_equipe_5", "n_corridas_equipe_5", "n_participacoes_equipe_5",
    "historico_piloto_insuficiente", "historico_equipe_insuficiente",
    "equipe_pre_corrida_ausente", "referencia_temporal_ausente",
)
PROTOCOLS = (
    "docs/auditoria_statsmodels_20261102.md",
    "docs/en/STATSMODELS_AUDIT_20261102.md",
)
INPUTS = (
    "data/preparado/treino.csv", "data/preparado/colunas.json",
    "data/preparado/validacao.csv", "data/preparado/teste_final_reservado.csv",
    "models/modelo_v1/metadados.json",
    "reports/modelo_v1/previsoes_validacao.csv",
    "reports/avaliacao_final_v1/previsoes_pre_corrida.csv",
    "reports/avaliacao_final_v1/avaliacao_por_piloto.csv",
)
CODE = (
    "pitwall/research/statsmodels_audit.py",
    "pitwall/research/run_statsmodels_audit.py",
    "requirements_statsmodels_audit.txt", "requirements_modelo_v1.txt",
    "tests/test_statsmodels_audit.py",
)
PINNED_VERSIONS = {
    "numpy": "1.26.4", "scipy": "1.13.1", "pandas": "2.2.3",
    "scikit-learn": "1.6.1", "joblib": "1.5.3", "threadpoolctl": "3.6.0",
    "statsmodels": "0.14.6", "patsy": "1.0.2", "matplotlib": "3.9.4",
}
PROTECTED_ROOTS = (
    "data/preparado", "models/modelo_v1", "reports/modelo_v1",
    "reports/avaliacao_final_v1", "reports/operacao_2026/emissoes",
    "operacao2026/eventos", "treinar_modelo_v1.py", "avaliar_modelo_v1.py",
    "preparar_historico.py", "requirements_modelo_v1.txt",
    "docs/protocolo_temporal.md", "docs/dicionario_variaveis.md",
    "docs/experimento_modelo_v1.md", "docs/avaliacao_final_v1.md",
    "docs/experimento_modelo_v2_a_b1.md",
    "docs/adendo_metodologia_v2_fontes_circuito_20261026.md",
    "registro_emissoes.py",
)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def _rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise ValueError("empty source: {}".format(path))
    if any(None in row for row in rows):
        raise ValueError("malformed CSV: {}".format(path))
    return rows


def _flag(value):
    if str(value) in ("1", "True"):
        return True
    if str(value) in ("0", "False"):
        return False
    raise ValueError("invalid boolean: {!r}".format(value))


def _number(value, missing=False):
    text = str(value).strip()
    if missing and not text:
        return float("nan")
    if text in ("True", "False"):
        return float(text == "True")
    result = float(text)
    if not math.isfinite(result):
        raise ValueError("nonfinite numeric source")
    return result


def _key(row, allowed_years):
    year, race = int(row["temporada"]), int(row["rodada"])
    driver = row["piloto_id"].strip()
    if year not in allowed_years or race <= 0 or not driver:
        raise ValueError("source outside declared seasons or missing identity")
    return year, race, driver


def _index(rows, allowed_years):
    index = {}
    for row in rows:
        key = _key(row, allowed_years)
        if key in index:
            raise ValueError("duplicate source identity: {}".format(key))
        index[key] = row
    return index


def load_training(root):
    """Return only allowlisted X and known y from eligible 2021–2023 rows."""
    root = Path(root)
    metadata = json.loads((root / "models/modelo_v1/metadados.json").read_text())
    schema = json.loads((root / "data/preparado/colunas.json").read_text())
    names = list(FEATURES)
    if metadata["entradas"] != names or schema["entradas"] != names:
        raise ValueError("v1 feature allowlist/order mismatch")
    prohibited = set(schema.get("auditoria_proibida_como_entrada", [])) | {"podio"}
    if prohibited.intersection(names):
        raise ValueError("outcome/audit field cannot enter X")
    source = root / "data/preparado/treino.csv"
    expected = metadata["hashes_fontes_permitidas"]
    if _sha(source) != expected["treino.csv"] or _sha(root / "data/preparado/colunas.json") != expected["colunas.json"]:
        raise ValueError("training/schema no longer matches frozen v1 provenance")
    index = _index(_rows(source), {2021, 2022, 2023})
    matrix, targets, groups, excluded = [], [], [], []
    unknown, ineligible = 0, 0
    for key, row in sorted(index.items()):
        if row["divisao"] != "treino":
            raise ValueError("training split mismatch")
        known = bool(row["podio"].strip())
        target = _number(row["podio"]) if known else None
        if known and target not in (0, 1):
            raise ValueError("target must be binary or unknown")
        reasons = []
        if _flag(row["classificacao_ausente"]):
            reasons.append("classificacao_ausente")
        if _flag(row["referencia_temporal_ausente"]) or not row["limite_inferior_referencia_utc"].strip():
            reasons.append("referencia_temporal_ausente")
        unknown += int(not known)
        ineligible += int(bool(reasons))
        if reasons or not known:
            excluded.append({"key": list(key), "reasons": reasons + ([] if known else ["unknown_target"])})
            continue
        matrix.append([_number(row[name], missing=True) for name in names])
        targets.append(target)
        groups.append(key[:2])
    if not matrix:
        raise ValueError("no eligible labelled training observations")
    coverage = {"original_rows": len(index), "analysed_rows": len(matrix),
                "unknown_targets": unknown, "ineligible_rows": ineligible,
                "n_gp": len(set(groups)), "n_drivers": len({key[2] for key in index}),
                "seasons": [2021, 2022, 2023], "excluded": excluded}
    return np.asarray(matrix), np.asarray(targets), groups, names, metadata, coverage


def load_calibration(root, year):
    """Strictly join frozen predictions and targets; no 2026 diagnostics."""
    if year not in (2024, 2025):
        raise ValueError("calibration accepts only preserved 2024 and 2025 predictions")
    root = Path(root)
    path = "reports/modelo_v1/previsoes_validacao.csv" if year == 2024 else "reports/avaliacao_final_v1/previsoes_pre_corrida.csv"
    predictions = _index(_rows(root / path), {year})
    outcomes = predictions if year == 2024 else _index(_rows(root / "reports/avaliacao_final_v1/avaliacao_por_piloto.csv"), {year})
    if set(predictions) != set(outcomes):
        raise ValueError("prediction/outcome identity mismatch")
    p, y, groups, excluded = [], [], [], []
    eligible_count, unknown = 0, 0
    for key, row in sorted(predictions.items()):
        outcome = outcomes[key]
        eligible = _flag(row["elegivel_previsao"])
        if eligible != _flag(outcome["elegivel_previsao"]):
            raise ValueError("prediction/outcome eligibility mismatch")
        # Compare even ineligible rows: a populated/empty probability must agree.
        if row["probabilidade_modelo"] != outcome["probabilidade_modelo"]:
            raise ValueError("prediction/outcome frozen probability mismatch")
        known = _flag(outcome["alvo_conhecido"])
        if not known and outcome["podio"].strip():
            raise ValueError("unknown outcome has a populated target")
        target = _number(outcome["podio"]) if known else None
        if known and target not in (0, 1):
            raise ValueError("known outcome must be binary")
        eligible_count += int(eligible)
        unknown += int(not known)
        if not eligible or not known:
            excluded.append({"key": list(key), "reasons": ([] if eligible else ["ineligible"]) + ([] if known else ["unknown_target"])})
            continue
        probability = _number(row["probabilidade_modelo"])
        if not 0 <= probability <= 1:
            raise ValueError("probability outside [0,1]")
        p.append(probability)
        y.append(target)
        groups.append(key[:2])
    if not p:
        raise ValueError("no evaluable preserved probabilities")
    return np.asarray(p), np.asarray(y), groups, {
        "season": year, "original_rows": len(predictions), "eligible_rows": eligible_count,
        "unknown_targets": unknown, "analysed_rows": len(p), "n_gp": len(set(groups)),
        "excluded": excluded, "retrospective": True, "untouched_test": False,
    }


def snapshot_protected(root):
    """Hash protected source bytes including registered emissions of any year."""
    root = Path(root).resolve()
    paths = set(PROTECTED_ROOTS)
    registry = root / "operacao2026/eventos/emissoes_registradas.json"
    if registry.exists():
        for row in json.loads(registry.read_text()):
            paths.add(row["diretorio"])
    files = set()
    for relative in paths:
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("protected source escapes root")
        if path.is_dir():
            files.update(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        elif path.is_file():
            files.add(path)
    return {str(path.relative_to(root)): _sha(path) for path in sorted(files)}


def verify_protected(root, baseline):
    expected = baseline.get("files", baseline)
    current = snapshot_protected(root)
    missing = sorted(set(expected) - set(current))
    changed = sorted(k for k in expected.keys() & current.keys() if expected[k] != current[k])
    new = sorted(set(current) - set(expected))
    return {"status": "preserved" if not (missing or changed or new) else "divergent",
            "checked_files": len(expected), "changed": changed, "missing": missing, "new": new}


def _csv(path, rows):
    if not rows:
        return
    fields = list(rows[0])
    with Path(path).open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _metrics_by_gp(p, y, groups):
    result = []
    for gp in sorted(set(groups)):
        mask = np.array([g == gp for g in groups])
        assigned = np.where(y[mask] == 1, p[mask], 1 - p[mask])
        result.append({"temporada": gp[0], "rodada": gp[1], "n": int(mask.sum()),
                       "brier": float(np.mean((p[mask] - y[mask])**2)),
                       "log_loss": float(-np.log(assigned).mean()) if np.all(assigned > 0) else None})
    return result


def _plots(destination, calibration, stability):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    for ax, year in zip(axes, ("2024", "2025")):
        bins = [b for b in calibration[year]["bins"] if b["n"]]
        ax.plot([0, 1], [0, 1], "--", color="#666666", label="Ideal")
        ax.scatter([b["mean_probability"] for b in bins], [b["observed_rate"] for b in bins],
                   s=[20 + 2*b["n"] for b in bins], color="#135E82", alpha=0.75)
        for b in bins:
            ax.annotate(str(b["n"]), (b["mean_probability"], b["observed_rate"]), xytext=(4, 5), textcoords="offset points", fontsize=8)
        ax.set(xlim=(-0.03, 1.03), ylim=(-0.03, 1.03), title=year,
               xlabel="Probabilidade média / Mean probability", ylabel="Frequência / Observed rate")
        ax.grid(alpha=0.15)
    fig.suptitle("Calibração descritiva / Descriptive calibration — N por faixa / per bin")
    fig.savefig(destination / "calibration.png", dpi=170)
    plt.close(fig)

    rows = [row for row in stability["feature_summary"] if row["jackknife_min"] is not None and row["constant_in_jackknife_count"] < row["n_jackknife_successful"]]
    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    for i, row in enumerate(rows):
        ax.plot([row["jackknife_min"], row["jackknife_max"]], [i, i], color="#135E82", linewidth=4, alpha=0.65)
        ax.scatter(row["reference_coefficient"], i, color="#AD3F30", zorder=3, s=32)
    ax.axvline(0, color="#777777", linewidth=0.8)
    ax.set_yticks(range(len(rows)), [r["feature"] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Coeficiente na escala congelada / Coefficient in frozen scale")
    ax.set_title("Retirar um GP / Leave one GP out: amplitude / range\nPonto vermelho: v1 / Red point: v1; amplitude não é IC / range is not a CI")
    ax.grid(axis="x", alpha=0.15)
    fig.savefig(destination / "coefficient_stability.png", dpi=170)
    plt.close(fig)


def _report(destination, result, language):
    english = language == "en"
    design, stability, calibration = (result[k] for k in ("design", "stability", "calibration"))
    title = "Statistical audit with statsmodels" if english else "Auditoria estatística com statsmodels"
    lines = ["# " + title, "", "Created by: MBPaschoal", "Status: executed; retrospective diagnostic research", "Type: research audit report", "Date: 2026-11-02", "",
             "[Português](relatorio.md) · [English](report.en.md)", ""]
    lines += (["This audit preserves frozen v1 and all recorded predictions. It does not recalibrate, promote a model, use 2026 for fitting or establish causal effects."] if english else ["Esta auditoria preserva o v1 e as previsões registradas. Não recalibra probabilidades, promove modelo, usa 2026 para ajuste ou estabelece efeitos causais."])
    lines += ["", "## " + ("Redundancy" if english else "Redundâncias"), ""]
    lines += [("Training: {n_rows} rows; {n_features} columns; rank {rank}, or {rank_with_intercept} including intercept." if english else "Treino: {n_rows} linhas; {n_features} colunas; posto {rank}, ou {rank_with_intercept} com intercepto.").format(**design), ""]
    lines += [("Constant columns: " if english else "Colunas constantes: ") + ", ".join("`" + c["feature"] + "`" for c in design["constants"]) + ".", ""]
    for pair in design["raw_proportional_pairs"]:
        lines += ["- `{right}` = {right_per_left:.8g} × `{left}` ({n_observed} observações / observations).".format(**pair)]
    lines += ["", ("The deterministic full-rank view is diagnostic only. The ridge replicas retain all 15 inputs: removing duplicate columns changes the L2 penalty. Redundant slopes cannot be interpreted as separately identified effects." if english else "A visão de posto completo é somente diagnóstica. As réplicas regularizadas mantêm as 15 entradas: remover duplicatas altera a penalização L2. Coeficientes redundantes não representam efeitos separadamente identificados."), "", "[JSON](redundancy.json) · [VIF CSV](vif.csv)", "", "## " + ("Calibration" if english else "Calibração"), "",
              "| Coorte / Cohort | N | GPs | Brier | Log loss | Intercepto / Intercept | Inclinação / Slope | Calibração global / CITL |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    fmt = lambda value: "N/A" if value is None else "{:.5f}".format(value)
    for label in ("2024", "2025", "2024-2025"):
        c = calibration[label]
        lines += ["| {} | {} | {} | {} | {} | {} | {} | {} |".format(label, c["n_rows"], c["n_gp"], fmt(c["brier"]), fmt(c["log_loss"]), fmt(c["joint"].get("intercept")), fmt(c["joint"].get("slope")), fmt(c["calibration_in_the_large"].get("intercept")))]
    lines += ["", ("Joint calibration ideal is intercept=0, slope=1. Calibration-in-the-large (CITL) fits a separate intercept with slope fixed at 1; its ideal is 0. Pooled seasons are a secondary summary. 2024 was explored and 2025 already evaluated; neither is an untouched test." if english else "O ideal da calibração conjunta é intercepto=0 e inclinação=1. A calibração global (CITL) estima outro intercepto com inclinação fixa em 1; ideal=0. O conjunto das temporadas é resumo secundário. 2024 foi explorada e 2025 já avaliada; nenhuma é teste intocado."), "", "| Coorte / Cohort | IC95% a / CI95% a | IC95% b / CI95% b | IC95% CITL / CI95% CITL | Réplicas válidas / Valid replicates |", "|---|---|---|---|---:|"]
    for label in ("2024", "2025", "2024-2025"):
        bootstrap = calibration[label]["bootstrap"]
        intervals = bootstrap.get("intervals") or {}
        fci = lambda name: "[{:.5f}, {:.5f}]".format(*intervals[name]) if intervals.get(name) is not None else "N/A"
        lines += ["| {} | {} | {} | {} | {}/{} |".format(label, fci("intercept"), fci("slope"), fci("calibration_in_the_large"), bootstrap["successful_replicates"], bootstrap["requested_replicates"])]
    repetitions = calibration["2024"]["bootstrap"]["requested_replicates"]
    lines += ["", ("Intervals use 2-GP moving blocks within seasons, {} samples, seed 42. They condition on frozen probabilities; they exclude original-model training uncertainty, may miss longer dependence and are not a joint calibration/equivalence test. GP-cluster marginal normal intervals and all warnings/failures are retained in JSON." if english else "Os intervalos usam blocos móveis de dois GPs dentro da temporada, {} réplicas e semente 42. São condicionais às probabilidades congeladas, não incluem incerteza do treinamento original, podem perder dependência mais longa e não são teste conjunto de calibração/equivalência. ICs marginais normais agrupados por GP e todos os avisos/falhas constam no JSON.").format(repetitions), "", "![Calibração / Calibration](calibration.png)", "", "[JSON](calibration.json) · [Bins CSV](calibration_bins.csv) · [GP metrics CSV](metrics_by_gp.csv)", "", "## " + ("Coefficient stability" if english else "Estabilidade dos coeficientes"), ""]
    baseline = stability["baseline"]
    converged_count = sum(fit["converged"] for fit in stability["jackknife"])
    lines += [("Converged leave-GP-out fits: {}/{}. Recorded fit failures: {}. Baseline converged: {}." if english else "Ajustes com exclusão de GP convergidos: {}/{}. Falhas de ajuste registradas: {}. Réplica-base convergiu: {}.").format(converged_count, stability["n_gp"], len(stability["failures"]), baseline["converged"]), ""]
    lines += [("Independent ridge replica: maximum absolute coefficient difference from saved v1 = {:.8g}; maximum reconstructed training probability difference = {:.8g}." if english else "Réplica regularizada independente: diferença absoluta máxima de coeficiente para o v1 salvo = {:.8g}; diferença máxima nas probabilidades reconstituídas de treino = {:.8g}.").format(baseline["max_abs_difference_frozen_coefficient"], baseline["max_abs_difference_frozen_training_probability"]), "", ("The same L2 objective is used, with alpha=1/(C*n), C=1 and unpenalized intercept. Small differences reflect optimizer tolerances, not a replacement model. GLM likelihood/score are explicitly refined because the statsmodels pure-ridge API ignores iteration/tolerance kwargs." if english else "O objetivo L2 é o mesmo: alpha=1/(C*n), C=1 e intercepto sem penalização. Pequenas diferenças refletem tolerâncias do otimizador, não substituição do modelo. A verossimilhança/score GLM recebem refinamento explícito porque a API de ridge do statsmodels ignora kwargs de iteração/tolerância."), "",
              "| Entrada / Feature | v1 | Mínimo / Minimum | Máximo / Maximum | Trocas de sinal / Sign flips | Constante / Constant |", "|---|---:|---:|---:|---:|---:|"]
    for row in stability["feature_summary"]:
        lines += ["| `{}` | {} | {} | {} | {} | {} |".format(row["feature"], fmt(row["reference_coefficient"]), fmt(row["jackknife_min"]), fmt(row["jackknife_max"]), row["sign_flip_count"] if row["sign_flip_count"] is not None else "N/A", row["constant_in_jackknife_count"])]
    lines += ["", ("Each fit omits a whole training GP and refits imputation/scaling on remaining 2021–2023 rows. Slopes are expressed in frozen-training SD units; ranges/quantiles are sensitivity summaries, not confidence intervals. Sparse support and redundant inputs limit individual-coefficient interpretation. Expanding 2021, 2021–2022 and 2021–2023 fits are included in JSON/CSV. Changing medians prevents global intercept equivalence for missing rows." if english else "Cada ajuste retira um GP inteiro do treino e refaz imputação/escala nas linhas restantes de 2021–2023. Coeficientes usam unidades do desvio do treino congelado; amplitudes/quantis são resumos de sensibilidade, não intervalos de confiança. Suporte escasso e redundâncias limitam a interpretação individual. Ajustes cumulativos 2021, 2021–2022 e 2021–2023 constam no JSON/CSV. Medianas diferentes impedem equivalência global dos interceptos em linhas ausentes."), "", "![Estabilidade / Stability](coefficient_stability.png)", "", "[JSON](coefficient_stability.json) · [Summary CSV](coefficient_summary.csv) · [All fits CSV](coefficient_fits.csv)", "", "## " + ("Preservation and reproducibility" if english else "Preservação e reprodução"), "",
              "[Manifest](manifest.json) · [Before](protected_before.json) · [After](preservation.json) · [Frozen execution](execution_frozen.json)", "", "```bash", "venv/.statsmodels-audit/bin/python -B -m pitwall.research.run_statsmodels_audit", "```", "", ("Use a new output directory. This is a local research delivery; it makes no public-deployment or predictive-improvement claim." if english else "Usar diretório novo de saída. Esta é uma entrega local de pesquisa; não comprova publicação pública ou melhora preditiva."), ""]
    (destination / ("report.en.md" if english else "relatorio.md")).write_text("\n".join(lines), encoding="utf-8")


def run_audit(root, destination, baseline_path=None, bootstrap_reps=2000):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    allowed = root / "reports/statsmodels_audit_20261102"
    if destination == allowed or not destination.is_relative_to(allowed) or destination.exists():
        raise ValueError("audit output must be a new child of reports/statsmodels_audit_20261102")
    baseline = json.loads(Path(baseline_path).read_text()) if baseline_path else {"files": snapshot_protected(root)}
    before_check = verify_protected(root, baseline)
    if before_check["status"] != "preserved":
        raise ValueError("protected artefacts differ before execution: {}".format(before_check))
    destination.mkdir(parents=True, exist_ok=False)
    _json(destination / "protected_before.json", baseline)
    versions = {name: importlib.metadata.version(name) for name in PINNED_VERSIONS}
    if versions != PINNED_VERSIONS:
        raise ValueError("audit environment differs from pinned package versions")
    frozen = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "executable": sys.executable,
              "packages": versions, "bootstrap_replicates": bootstrap_reps,
              "seed": 42, "block_length": 2, "C": 1.0, "native_threads": 1,
              "fit_seasons": [2021, 2022, 2023], "calibration_seasons": [2024, 2025],
              "module_paths": {name: importlib.util.find_spec(name).origin for name in ("numpy", "scipy", "pandas", "sklearn", "statsmodels", "patsy", "matplotlib")},
              "integrity_only_inputs": ["data/preparado/validacao.csv", "data/preparado/teste_final_reservado.csv"],
              "hashes": {name: _sha(root / name) for name in PROTOCOLS + CODE + INPUTS}}
    _json(destination / "execution_frozen.json", frozen)
    progress = lambda stage, done, total: print("{} {}/{}".format(stage, done, total), flush=True) if done == 1 or done == total or done % 10 == 0 else None
    try:
        with threadpool_limits(limits=1):
            X, y, groups, names, metadata, train_coverage = load_training(root)
            ref = metadata["parametros_aprendidos"]
            med, mean, scale, beta = [np.asarray(ref[k]) for k in ("medianas_imputador", "media_normalizador", "escala_normalizador", "coeficientes")]
            transformed = (np.where(np.isnan(X), med, X) - mean) / scale
            design = audit_design(transformed, names, raw_matrix=X)
            _json(destination / "redundancy.json", design)
            _csv(destination / "vif.csv", [{"feature": row["feature"], "vif": row["vif"]} for row in design["vif"]])
            stability = coefficient_stability(X, y, groups, names, med, mean, scale, beta, reference_intercept=ref["intercepto"], progress=progress)
            _json(destination / "coefficient_stability.json", stability)
            _csv(destination / "coefficient_summary.csv", stability["feature_summary"])
            fits = []
            for kind in ("jackknife", "expanding"):
                for fit in stability[kind]:
                    for j, name in enumerate(names):
                        fits.append({"kind": kind, "omitted_gp": str(fit.get("omitted_gp", "")), "training_seasons": str(fit.get("training_seasons", "")), "feature": name, "coef_reference_scale": fit["coef_reference_scale"][j], "coef_raw": fit["coef_raw"][j], "n_rows": fit["n_rows"], "converged": fit["converged"], "gradient_max_abs": fit["gradient_max_abs"]})
            _csv(destination / "coefficient_fits.csv", fits)
            calibration, coverage, all_p, all_y, all_groups, gp_metrics = {}, {"training": train_coverage}, [], [], [], []
            for year in (2024, 2025):
                p, target, gps, cov = load_calibration(root, year)
                print("calibration {}".format(year), flush=True)
                calibration[str(year)] = calibration_audit(p, target, gps, bootstrap_reps=bootstrap_reps, progress=progress)
                coverage[str(year)] = cov
                all_p.extend(p); all_y.extend(target); all_groups.extend(gps)
                gp_metrics.extend(_metrics_by_gp(p, target, gps))
            print("calibration pooled 2024–2025 (secondary)", flush=True)
            calibration["2024-2025"] = calibration_audit(all_p, all_y, all_groups, bootstrap_reps=bootstrap_reps, progress=progress)
            _json(destination / "calibration.json", calibration)
            _json(destination / "coverage.json", coverage)
            _csv(destination / "metrics_by_gp.csv", gp_metrics)
            bins = [{"cohort": label, **row} for label, data in calibration.items() for row in data["bins"]]
            _csv(destination / "calibration_bins.csv", bins)
            result = {"design": design, "stability": stability, "calibration": calibration}
            _plots(destination, calibration, stability)
            _report(destination, result, "pt"); _report(destination, result, "en")
        preservation = verify_protected(root, baseline)
        _json(destination / "preservation.json", preservation)
        if preservation["status"] != "preserved":
            raise ValueError("protected files changed during audit")
        changed_inputs = [name for name, digest in frozen["hashes"].items() if _sha(root / name) != digest]
        if changed_inputs:
            raise ValueError("audit code/protocol/input changed during execution: {}".format(changed_inputs))
        limitations = []
        if not stability["baseline"]["converged"]:
            limitations.append("ridge baseline not converged")
        if stability["failures"]:
            limitations.append("coefficient sensitivity contains failed fits")
        for label, data in calibration.items():
            if any(data[k]["status"] != "ok" for k in ("joint", "calibration_in_the_large")) or data["bootstrap"]["status"] != "ok":
                limitations.append("{} calibration contains non-estimable diagnostics".format(label))
        manifest = {"schema": "pitwall-statsmodels-audit-v1", "status": "completed_with_limitations" if limitations else "completed",
                    "diagnostic_limitations": limitations,
                    "created_utc": frozen["created_utc"], "versions": versions,
                    "protected_files": preservation["checked_files"], "model_v1_updated": False,
                    "recorded_probabilities_updated": False, "new_operational_probabilities": False,
                    "files": {p.name: _sha(p) for p in sorted(destination.iterdir()) if p.is_file()}}
        _json(destination / "manifest.json", manifest)
        return manifest
    except Exception as error:
        _json(destination / "failure.json", {"error_type": type(error).__name__, "error": str(error), "preservation": verify_protected(root, baseline)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--preservation-baseline", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("audit-%Y%m%dT%H%M%SZ")
    destination = args.destination or args.root / "reports/statsmodels_audit_20261102" / stamp
    manifest = run_audit(args.root, destination, baseline_path=args.preservation_baseline)
    print(json.dumps({"destination": str(destination.resolve()), "status": manifest["status"], "protected_files": manifest["protected_files"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
