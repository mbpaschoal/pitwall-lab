# Stage 5 — retrospective final evaluation of v1 in 2025

[Português](../../reports/avaliacao_final_v1/relatorio.md)

Status: evaluated for model v1.

This evaluation uses frozen v1 and the 2025 test source. Prediction and favourite selection happened before extracting `podio`; empty targets remained unknown, never zero. There was no fitting, calibration, feature selection or threshold change.

## Coverage

- Test rows: 480; eligible for prediction: 479; ineligible: 1.
- Known targets: 479; unknown: 1; probabilistic-metric rows: 478.
- GPs: 24; common ranking-evaluable GPs: 22.

## Probabilistic metrics

| Method | Log loss | Brier |
|---|---:|---:|
| Model | 0.20328013885785817 | 0.058518438214266853 |
| Training constant | 0.42379724063090557 | 0.12793920072881459 |

The model's Brier was lower than the constant's. Lower is better, but lower Brier alone does not prove better calibration. Descriptive calibration uses ten bins, retaining empty bins without artificial frequencies.

## Top-three rankings

| Method | Evaluable GPs | Mean correct drivers | All-three proportion |
|---|---:|---:|---:|
| Model | 22 | 2.3181818181818183 | 0.36363636363636365 |
| Qualifying | 22 | 2.2727272727272729 | 0.36363636363636365 |

Both rankings share the same GP cohort. GPs with fewer than three eligible drivers, an ineligible participant, an unknown target or a positive-target count different from three have undefined scores, not artificial zero. Ties use lexicographic `piloto_id`; missing qualifying positions follow known positions. Individual probabilities were not renormalised to sum to three per GP.

## Descriptive 2024 comparison and limits

2024 values in `comparacao_2024.json` have their own denominators: 479 probability rows and 24 ranking GPs, versus 478 and 22 in 2025. These are different seasons; no claim of statistical significance, causality or future performance follows.

Historical sources may contain post-cutoff revisions. The study remains retrospective and does not prove that a prediction was issued before every race. **2025 has already been evaluated for v1 and is not an untouched test for future research.**
