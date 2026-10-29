# Model v1 experiment — plan fixed before training

Created by: MBPaschoal
Status: frozen historical protocol; English translation
Type: experiment protocol

[Português](../experimento_modelo_v1.md)

## Question and periods

Estimate an individual driver's probability of finishing on the podium in a main GP. The target is known binary `podio`; an unknown result remains unknown, never zero. The order of the three podium drivers is not predicted.

- Training: 2021–2023, exclusively `data/preparado/treino.csv`.
- Validation: 2024, exclusively `data/preparado/validacao.csv`. Already explored in previous stages; not untouched testing.
- Reserved final test: 2025. **At the time this historical plan was fixed, opening, evaluating or using it for decisions was prohibited**, including via complete historical tables, global input/target files or stage-3 regeneration. It was subsequently evaluated under the separate final-evaluation plan.
- Column metadata: only `data/preparado/colunas.json`.
- No Jolpica queries or historical collection/preparation; precomputed windows remain as received.

This protocol preceded the first fit; its hash is recorded in experiment metadata. Inputs, eligibility, hyperparameters and calibration bins must not change to favour observed 2024 results. Implementation bugs must be identified, tested and documented, rather than presented as new experiments.

## Pre-race population and eligibility

The prepared data are a retrospective outer join, not an entry list frozen at the cutoff. A driver is eligible when:

1. A qualifying record exists (`classificacao_ausente=0`), identifying participation through a pre-race-admitted source without using subsequent result existence.
2. A temporal reference exists (`referencia_temporal_ausente=0`, lower bound populated), following stage 3.

Do not exclude on result, final position, points, retrospective grid, retirement, DNS or disqualification. Do not select predictions using `resultado_ausente`. The current-result team never replaces the pre-race team.

- Entire qualifying record absent: retain coverage row without a v1 prediction, with reason.
- Qualifying record present but position absent: still eligible; the pipeline uses the training median. The qualifying benchmark puts missing positions last.
- Repeated/ambiguous position: preserve value and indicator; do not exclude drivers, invent sporting tie-breaks or substitute `Results.grid`.
- Rookies/short history: still eligible. Impute missing means while preserving counters/indicators. Missingness is not zero performance or necessarily an F1 debut.

Prediction eligibility is separate from target availability. Fit only eligible labelled training rows. All eligible validation rows receive probabilities, including unknown targets. Probabilistic metrics use only known targets and disclose denominators. Record missingness/exclusions by driver/GP without silently dropping rows.

## Authorised inputs and isolation

Exact ordered allowlist, checked against `colunas.json`:

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

Indicators constant in the eligible population remain, with zero coefficients when there is no variation. Do not select variables using performance. Keys, names, team, dates, split, targets and audit are not automatic inputs. Reject lists outside the allowlist or overlapping forbidden schema fields; do not infer inputs by numeric type or by excluding a few fields.

Convert CSV `True`/`False` and `0`/`1` explicitly. Empty numeric cells become NaN only in the working matrix. Reject invalid non-numeric/infinite values, targets outside empty/0/1, duplicate keys and inconsistent periods. Preserve original data.

## Fixed model

Python/scikit-learn versions are in `requirements_modelo_v1.txt`; use the project environment.

1. `SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=False)`: medians learned only from eligible labelled training rows. Entirely empty training features follow the imputer's documented zero rule. Missingness indicators are already explicit inputs.
2. `StandardScaler`: means/scales learned only from imputed training rows. Constant inputs must not divide by zero.
3. `LogisticRegression(C=1.0, penalty='l2', solver='lbfgs', max_iter=2000, tol=1e-4, class_weight=None, random_state=42)`.

The seed is explicit for reproducibility; `lbfgs` does not randomly sample examples. No hyperparameter search, automatic balancing, learned calibration or validation fitting. Treat non-convergence as an error. Limit native threads to one while fitting; last digits may vary across platforms/BLAS.

Save the fitted pipeline and metadata for versions, inputs, parameters, medians, scales, coefficients, intercept and hashes of **permitted files only**. Do not read mixed receipts or 2025 files to build metadata. Only load trusted, locally produced joblib/pickle artefacts; arbitrary third-party files are unsafe.

## Benchmarks and tie-breaking fixed before evaluation

A. Constant probability = positive training targets / known targets, on exactly the model's eligible labelled training rows. Apply it to all eligible validation rows; do not estimate it in 2024.

B. Qualifying rank: ascending numeric qualifying position, missing positions last; ties by lexicographic `piloto_id`. No result, points or status. This is a reproducible computational convention, **not** a sporting tie-break. Record tied groups and whether they cross the top-three selection boundary. No probability is assigned to this benchmark.

Model rank: descending probability, exact ties by lexicographic driver ID, with the same tie audit. Select favourites before reading targets to score them. Both rankings use identical eligible participants. The old retrospective-grid reference is **not** an experiment comparator.

## Validation metrics and coverage

### Probabilities

Compare model and constant on the same eligible 2024 rows with known targets:

- Binary log loss, explicit classes `[0,1]`, lower is better.
- Binary Brier score, mean `(probability-target)^2`, lower is better.
- Descriptive calibration in **ten fixed uniform bins**: `[0,0.1)`, …, `[0.9,1]`. Report count, mean prediction and observed frequency; do not plot empty bins as zero frequency. Show reliability plots and counts/histograms for both methods.

These metrics combine discrimination and calibration. A lower Brier alone does not prove better calibration; a small-sample curve does not certify calibrated probabilities for other seasons.

### Top three

Select top three using inputs/probabilities only. Score both rankings on a common GP cohort requiring at least three eligible drivers, every participant in the GP's prepared union eligible, all targets known and exactly three positives.

Evaluation conditions do not change predictions or selected favourites. Incomplete GPs remain explicitly unevaluable, without artificial zero scores. Report evaluable-GP denominators and coverage over all 2024 races.

Metrics: mean correct drivers (0–3), distribution of 0/1/2/3 correct drivers, and proportion identifying all three regardless of order. Without evaluable GPs, values remain undefined. Explain exclusions; individual probability metrics can remain valid when a complete GP ranking comparison is not possible.

Independent binary probabilities need not sum to three per GP. Do not renormalise to force that sum or interpret it as a predicted number of podium places.

## Reproduction, tests and communication

Historical experiment command: `./.venv/bin/python treinar_modelo_v1.py`. One-time dependency installation: `./.venv/bin/python -m pip install -r requirements_modelo_v1.txt`. Historical full suite: `./.venv/bin/python -m unittest discover -s tests -v`. These commands are documented for context, not invoked by viewing this document; the full suite can execute scientific work.

Tests reject forbidden fields; prove all three fitting stages use training only and remain invariant under validation changes; separate prediction/selection from targets; preserve unknown targets; block actual 2025/mixed data and network; reproduce outputs; refuse divergent overwrites.

Report standardised coefficients/intercept without causality: conditional training associations affected by correlation and regularisation, not effects of manipulating variables. Acknowledge few seasons, within-GP dependence, previously explored 2024 validation, sporting changes and retrospective revisions. Do not claim 2025 generalisation or conceal benchmark losses.

## Primary technical references

- [Pipelines and leakage](https://scikit-learn.org/1.6/common_pitfalls.html)
- [Imputation](https://scikit-learn.org/1.6/modules/generated/sklearn.impute.SimpleImputer.html)
- [Scaling](https://scikit-learn.org/1.6/modules/generated/sklearn.preprocessing.StandardScaler.html)
- [Logistic regression](https://scikit-learn.org/1.6/modules/generated/sklearn.linear_model.LogisticRegression.html)
- [Metrics and calibration](https://scikit-learn.org/1.6/modules/calibration.html)
- [Persistence](https://scikit-learn.org/1.6/model_persistence.html)

Sports-data sources and limits: [temporal protocol](protocolo_temporal.md) and [dictionary](dicionario_variaveis.md). Public Jolpica-F1 data under CC BY-NC-SA 4.0; no new queries at this historical stage.
