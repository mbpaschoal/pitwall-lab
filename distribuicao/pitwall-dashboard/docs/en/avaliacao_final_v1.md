# Retrospective final evaluation of v1 — plan preceding access to 2025

Created by: MBPaschoal
Status: historical plan frozen before evaluation; English translation
Type: final evaluation protocol
UTC registration before access: 2026-10-18T06:43:57.198266+00:00

[Português](../avaliacao_final_v1.md)

## Commitment and initial state

This plan was registered before loading actual 2025 test data. The 100 existing tests passed with actual test/mixed data and network blocked. Legacy tests fit simulated examples only; the real v1 fit was not rerun. Metadata were checked. Source commit: `9a3b7b832334888af799e981cd173f26339c28d2`.

Evaluate only saved v1. Do not call `fit`, `fit_transform` or `partial_fit` at any pipeline stage; do not recalculate medians, scales, coefficients, calibration, variables, hyperparameters or thresholds. Do not train another version or respond to 2025 outcomes by changing rules. Repeating the same frozen evaluation for verification is allowed. Document implementation bugs without searching for a favourable combination.

## Frozen identity — SHA-256 before opening the test

| Artefact | SHA-256 |
|---|---|
| `models/modelo_v1/modelo.joblib` | `16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3` |
| `models/modelo_v1/metadados.json` | `77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6` |
| `docs/experimento_modelo_v1.md` | `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569` |
| `treinar_modelo_v1.py` | `cdf1c2ea005f36f032ebd1694786e9118ae343a282172fafb748cbf5c2294de3` |
| `reports/modelo_v1/metricas.json` | `e06613f5178fecdd06e7afdccb0503ab4f277e5712c61c5cf85f193ae240686f` |

The pipeline is trusted and local, not third-party joblib. Preserve the trainer, original plan, model and all stage-4 artefacts byte for byte. The evaluation manifest also records this plan, schema, script, test source and each output, excluding self-reference. Do not record personal paths or credentials.

## Permitted sources and execution

After registration, only `data/preparado/teste_final_reservado.csv` is authorised as test data. `colunas.json`, local model/metadata, documents and `reports/modelo_v1/metricas.json` are permitted auxiliaries. Do not read training, validation, full/mixed history, historical JSON or 2026 data. No API calls, collection or regeneration.

Before prediction validate a non-empty CSV, literal split `teste_final_reservado`, literal season `2025`, unique populated keys, positive rounds, exact schema/input list. Reject mixed years/splits, invalid/infinite numbers and forbidden fields in inputs. Audit columns may exist in the full CSV but never enter the matrix, eligibility or selection. Boolean/NaN conversion preserves v1 definitions.

Existing sequential preparation can use earlier 2025 results in later 2025 windows. This does not authorise recalculating windows or refitting. The [temporal protocol](protocolo_temporal.md) still applies.

## Inputs — unchanged v1 list and order

```text
posicao_classificacao
posicao_classificacao_repetida
classificacao_ausente
posicao_classificacao_ausente
media_posicao_final_5
taxa_podios_5
n_posicoes_5
n_podios_5
media_pontos_equipe_5
n_corridas_equipe_5
n_participacoes_equipe_5
historico_piloto_insuficiente
historico_equipe_insuficiente
equipe_pre_corrida_ausente
referencia_temporal_ausente
```

Median imputation, StandardScaler and logistic regression retain saved parameters, including `C=1`. Transforming/predicting does not mean relearning. Individual probabilities are not renormalised to sum to three per GP.

## Separate eligibility, prediction and target stages

Apply v1 eligibility: qualifying record present and temporal reference available with a lower bound. Do not exclude on final position, points, retirement, DNS, disqualification or `resultado_ausente`.

- Missing qualifying record: retain coverage row, no prediction, with reason.
- Present record/missing position: eligible; saved imputation applies. Qualifying ranking puts missing positions last.
- Repeated/ambiguous positions and insufficient history: preserve values/flags; no exclusion or invented sporting tie-break.
- Separate pre-race projection from target extraction/validation. Predict and select favourites without accessing `podio` or audited outcomes; only afterwards join targets by key to score. The CSV contains both, but prediction does not use targets.
- Empty target remains unknown, not zero, and does not prevent prediction for an eligible participant. Record `alvo_conhecido` only during evaluation.

## Frozen benchmarks and tie-breaking

A. Training constant from metadata: **`0.15011372251705837`**. Do not recalculate in 2025 or reopen training to estimate it.

B. Qualifying rank: ascending numeric position, missing positions last, ties by lexicographic `piloto_id`. Ranking has no fabricated probabilities and does not use the old retrospective grid.

Model: descending probability, exact ties by lexicographic ID. Select up to three favourites per GP using only these rules. Record all tied groups, including equally prioritised missing positions. A zero-based inclusive start `i` and exclusive end `j` crosses the boundary exactly when `i < 3 < j`. Preserve the reviewed stage-4 correction. Do not alter favourites after looking at targets.

## Metrics and denominators — unchanged definitions

Model and constant use the same eligible known-target rows:

- Binary log loss with explicit `[0,1]` classes.
- Brier: mean `(p-y)^2`.
- Ten uniform calibration bins `[0,0.1)`, …, `[0.9,1]`: counts, mean prediction and observed frequency. Empty bins retain zero count and undefined means, not zero frequency. Plot x=mean prediction, y=observed frequency without artificial method offsets.

A common GP ranking cohort requires at least three eligible drivers, every prepared GP participant eligible, all targets known and exactly three positives. Incomplete GPs remain with reasons and undefined scores, never artificial zero. This does not change predictions or favourites.

Report mean correct podium drivers (0–3), 0/1/2/3 distribution and all-three proportion regardless of order. With no evaluable GPs, mean/proportion are undefined. Individual probability metrics may remain valid in an unevaluable GP. Disclose individual/GP denominators, exclusions, ambiguities, unknown targets and excluded-GP lists.

## Comparison, delivery and subsequent state

Compare descriptively with published 2024 metrics, using separate denominators. These are different seasons: do not claim statistical significance, future superiority or causality. Report benchmark losses without improving v1 in response. Lower Brier alone does not prove improved calibration.

Deliver a separate script, driver predictions, driver/GP coverage, GP evaluations, metrics, calibration CSV/SVG, descriptive comparison, Portuguese report and hash manifest to new `reports/avaliacao_final_v1/`, refusing divergent overwrites even after partial failure. Preserve `models/modelo_v1/` and `reports/modelo_v1/`.

Actual execution and verification must prove no fitting and unchanged bytes. New boundary tests use clearly labelled simulated data; actual verification uses only authorised data, without network. Do not run the trainer during final reproduction.

After actual evaluation explicitly record: **2025 has changed from reserved to evaluated for v1, and cannot be described as untouched in later experiments.** Preserve the historical context of this and earlier plans. Update the current README/project status without rewriting historical results. No dashboard was part of that historical evaluation task.
