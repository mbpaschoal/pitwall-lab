# Stage 4 — v1 podium-probability model

[Português](../../reports/modelo_v1/relatorio.md)

This is a retrospective study. The experiment protocol was fixed before fitting. Training uses 2021–2023 only; validation uses previously explored 2024. **At the time of this report**, the 2025 test had not been opened or evaluated; see the separate subsequent 2025 report for the current evaluated status.

## Coverage

- Validation: 479 rows; 479 eligible; 0 ineligible; 479 known targets; 0 unknown targets.
- Probabilistic metrics: 479 rows.
- 2024 GPs: 24; common ranking-evaluable GPs: 24.
- Training: 1,319 eligible labelled rows fitted the pipeline; one row was ineligible. Training constant: `0.15011372251705837` on those same rows.
- Training exclusion: 2021/5, `mick_schumacher`, Monaco Grand Prix, `classificacao_ausente`. Full audit is in the original training-coverage artefact.
- Eight validation rows had ambiguous qualifying positions. Driver-level tie groups and boundary impacts are in the prediction CSV columns `empates_classificacao` and `empates_modelo`.

## Probabilistic metrics

| Method | Log loss | Brier |
|---|---:|---:|
| Logistic model | 0.22955624759095355 | 0.070917930921086059 |
| Training constant | 0.42325205376037162 | 0.12771914838843695 |

Lower is better for both. Calibration CSV/SVG use ten fixed bins and show counts; an empty bin is not zero frequency. The original calibration SVG is retained as an audit artefact.

## Top-three rankings

| Method | Evaluable GPs | Mean correct drivers | All-three proportion |
|---|---:|---:|---:|
| Model probability | 24 | 1.9583333333333333 | 0.25 |
| Qualifying | 24 | 1.875 | 0.16666666666666666 |

GP distribution with 0 / 1 / 2 / 3 correct drivers: model **1 / 5 / 12 / 6**; qualifying **1 / 5 / 14 / 4**.

Score only when all prepared participants are eligible, all targets known and exactly three positive targets. Incomplete GPs do not receive artificial zero. Qualifying is a ranking, not a probability; missing positions go last, ties use lexicographic `piloto_id`. The model orders decreasing probabilities with the same ID convention for exact ties only.

## Interpretation and limitations

The full standardised coefficients remain in the original coefficient artefact. The three largest absolute values in this run were `posicao_classificacao` (-1.9757), `media_pontos_equipe_5` (+0.5147), `historico_piloto_insuficiente` (-0.2835). Signs describe conditional associations affected by training/regularisation, not causal effects.

Individual probabilities need not sum to three and were not renormalised. Few seasons, correlated drivers within GPs, already explored 2024 validation and later source revisions limit conclusions. This report does not claim generalisation to 2025. The saved model is trusted local joblib; arbitrary third-party joblib/pickle must not be loaded.

[Download the original 2024 prediction CSV](../../reports/modelo_v1/previsoes_validacao.csv). Canonical scientific identifiers and values are preserved in the download.
