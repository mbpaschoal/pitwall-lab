# Temporal protocol and evaluation split — stage 3

[Português](../protocolo_temporal.md) · English translation of the preserved historical protocol.

## What was being prepared

A **retrospective study** of main races from 2021 to 2025, with variables intended to reproduce pre-race information. At this historical stage there was no trained model, performance estimate, real-time prediction or dashboard. This is a historical statement, not the current product status.

The conceptual prediction time is **the end of the main session establishing the GP's base grid order**, before subsequent penalties and before the race. We use the `qualifying/` position, **not** the retrospective `results/` grid. Qualifying does not necessarily equal the actual starting grid.

### Sprint exception in 2021 and 2022

In those seasons, qualifying set the Sprint grid and the Sprint set the GP's base order. From 2023, Sprint results no longer set that grid.

- The normal reference is `Qualifying` on its calendar date, whether Friday, Saturday or Sunday. Do not assume a weekday or subtract one day from the GP date.
- For 2021–2022 calendar events with `Sprint`, the conceptual reference is the end of that session (`Sprint_2021_2022`). `classificacao_nao_define_grid_gp=1` records the distinction.
- The input remains the qualifying-endpoint position, from timed qualifying before the Sprint in those cases. It precedes the cutoff but is not presented as directly determining the GP grid. Sprint results are not queried or mixed with main-race history.
- `SprintShootout` and `SprintQualifying` from 2023 onwards do not replace main-GP qualifying.

## Times: known and unknown

The calendar provides session **start times**, not verified end times. We do not invent a one-hour duration; `fim_sessao_referencia_utc` stays empty.

The reproducible conservative rule for historical windows is:

1. `limite_inferior_referencia_utc` is the reference session's recorded UTC start. With only a date, or an empty `time`, use 00:00 UTC that day as a **lower bound**, not the actual session time. Non-empty times require UTC suffix `Z`; invalid times stop preparation.
2. A previous GP becomes available to the history at **00:00 UTC on the day after its UTC race date**. This administrative study rule is `liberado_pelo_protocolo_utc`; it is neither the result-publication time nor a measured race end.
3. Availability must be no later than the reference lower bound. Always exclude the current race. This also excludes races on the qualifying date, even if they ended earlier: a conservative exclusion rather than future-data filling.
4. A session dated after the race, or starting at/after the known GP start, causes an error. A reference obviously later than the target is rejected.
5. Without a session date, retain the row with `referencia_temporal_ausente=1`, empty means and zero counters. Do not evaluate it as a cutoff-valid prediction before investigating the date.

Dates are source UTC dates, not local dates inferred from the city. The protocol assumes a previous GP appearing in results had finished by the following UTC day; sample events are separated by several days. **Review this approximation for races crossing midnight, postponed races or events near the cutoff.** The audit records the exact events used. A future real prediction must record the observed session end and the publication/acquisition time of its information.

The session start lower bound applies to **historical results**, avoiding an invented end time. Qualifying position is conceptually admitted at the session end, not at its start. The CSV is not presented as a prediction issued at the lower-bound timestamp.

## Fundamental historical-source limitation

Jolpica queried today may include corrections, disqualifications and revisions decided **after** the historical cutoff, including earlier qualifying and race results. Tests show that calculations do not read the current race or future events, but **do not certify that every data version was already published at the historical cutoff**.

UTC acquisition timestamps and response hashes identify the collected snapshot; they **do not establish historical availability**. Older caches without this information retain acquisition time `desconhecida` (unknown). File times, commit dates and task start dates are not substitutes.

Removing this limitation would require versioned archives published at the historical instant, or dated session documents. Until then, describe a retrospective study with temporal-order controls, not a backtest with fully verified historical information availability.

## Split frozen before training

| Split | Seasons | Permitted use at this historical stage |
|---|---|---|
| Training | 2021–2023 | Subsequent model and transformer fitting. |
| Validation | 2024 | Development comparisons and decisions; already explored in stage 2, not untouched testing. |
| Reserved final test | 2025 | Integrity, coverage and mechanical feature preparation only; no performance measurement or target-guided decisions. |

All drivers in a race receive the same split. There is no random driver shuffle. `divisoes.csv` makes allocation auditable by season/round. History may cross years: the first 2024 race may use permitted late-2023 results. Windows are not reset in January.

### Walk-forward evaluation

For each race: build inputs from results released before its cutoff; record predictions without reading its target; store the target after the GP; allow its results into later races' windows subject to their cutoffs.

Earlier 2025 results may therefore enter later 2025 race windows. This **does not permit refitting weights, imputers, scales, feature selection, hyperparameters or thresholds on the test set**. These components must be frozen after training/validation. The stage-3 2025 report contains coverage and quality counts, not accuracy, favourite success rates or feature rankings.

### Missing data and future eligibility

Retain drivers missing qualifying and drivers appearing only in qualifying. Without a result the target is **unknown**, not negative. Define and freeze a cutoff-based eligibility rule before evaluating a future model; report unevaluable cases and investigate unknown targets without silent exclusions.

The outer-join population is an **audit** choice, not an entry list captured at the cutoff. `resultado_ausente` and a team ID obtained only from results must not accidentally become inputs.

## Transformations not performed at this stage

No training, hyperparameter search, performance comparison, learned imputation, scaling or feature selection; no changes to Hermes model configuration; no manual sports-result corrections or filling from future seasons.

## Primary sources and attribution

- [Jolpica contract, User-Agent and pagination](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md)
- [Rate limits](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md): 4/s and 500/h when originally consulted; subject to change.
- [Calendar and sessions](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md)
- [Optional qualifying position](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/qualifying.md)
- [Main-race results](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md)
- [F1 Sprint format change in 2023](https://www.formula1.com/en/latest/article/formula-1-confirms-f1-sprint-format-tweaks-for-2023-season.6v1c2lGggpLNEom2MMtjj0)
- [Data terms: CC BY-NC-SA 4.0](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md)

Non-commercial educational project. Preserve attribution and terms when redistributing data.
