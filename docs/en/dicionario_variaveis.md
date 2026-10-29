# Variable dictionary — stage 3

[Português](../dicionario_variaveis.md) · English. Canonical field names remain unchanged in both languages.

## Unit of analysis and files

One row represents **season + round + piloto_id**. Joins use Jolpica IDs; names are labels. The population is the **outer union** of drivers in qualifying and main-race results, preserving unmatched participants. It does not reconstruct an entry list frozen at prediction time; drivers known only from results are flagged.

| File in `data/preparado/` | Role |
|---|---|
| `identificacao.csv` | Keys, labels, team and temporal metadata. |
| `entradas.csv` | Keys and permitted inputs only. Keys are join fields, not automatic model inputs. |
| `alvos.csv` | Keys and target; empty means unknown, not zero. |
| `auditoria_resultados.csv` | Keys and current-race outcomes, forbidden as inputs. |
| `base_historica.csv` | Complete audit view, not an instruction to feed every column into a model. |
| `colunas.json` | Explicit key, identification, input, target and forbidden-audit lists. |
| `auditoria_janelas.json` | Exact contributing race IDs and protocol-release dates; audit, not inputs. |
| `divisoes.csv` | One split per race. `treino.csv`, `validacao.csv`, `teste_final_reservado.csv` contain the respective complete rows. |
| `verificacao.json` | Source/output counts and hashes; generated last. |

## Identification: not automatic numeric inputs

| Field | Definition |
|---|---|
| `temporada`, `rodada`, `piloto_id` | Stable source row key. |
| `corrida`, `data_corrida`, `circuito_id`, `piloto` | Event name, source UTC date, circuit ID and driver label. |
| `equipe_id` | Identification team: prefer qualifying; use result only if missing, never to calculate the team input. |
| `equipe_id_entrada` | Team found **in qualifying**. Empty without qualifying; current-result team is not a substitute. |
| `divisao` | `treino` (2021–2023), `validacao` (2024), `teste_final_reservado` (2025). |
| `sessao_referencia` | `Qualifying`, or `Sprint_2021_2022` when Sprint establishes the GP base order. |
| `limite_inferior_referencia_utc` | Calendar session start; if only a date or empty `time`, UTC start of that day. A non-empty time requires `Z`; invalid values block preparation. **Not a session-end timestamp.** |
| `fim_sessao_referencia_utc` | Empty: the API does not provide a verified end time. No invented duration. |
| `precisao_referencia` | `inicio_sessao`, `inicio_dia` or `desconhecida`. |
| `classificacao_nao_define_grid_gp` | Flags 2021–2022 Sprint weekends: qualifying is timed qualifying before the Sprint, not the final GP order. |

## Inputs and formulae

Select previous GPs released **before the conservative limit** in the [temporal protocol](protocolo_temporal.md). Order by race date/time, then season/round. Never use the current race, even with an incorrect date. Release time is a study rule, not proof of historical publication.

Let $H_d$ be the ordered set of the driver's **up to five most recent previous participations**, and $n_d=|H_d|$. Participation means a **result-endpoint record**, not necessarily a race start. A GP without a driver result does not occupy a slot.

For a team, select its **up to five most recent previous GPs whose results contain its literal constructorId**. Let $G_e$ be those events, $m_e=|G_e|$, $P_e$ their team-driver records, and $n_e=|P_e|$. This is five team events, not five driver rows.

| Input | Definition |
|---|---|
| `posicao_classificacao` | Positive integer `QualifyingResults.position` when reported. Not `Results.grid`. Q1/Q2/Q3 do not invent missing positions. Preserve repeated source positions rather than forcing a unique order. |
| `posicao_classificacao_repetida` | 1 if the same positive qualifying position occurs for multiple drivers in that GP; otherwise 0, including missing positions. Flags ambiguity without an invented sporting tie-break or grid substitution. |
| `classificacao_ausente` | 1 without a driver qualifying record, otherwise 0. |
| `posicao_classificacao_ausente` | 1 for a missing position, even when a qualifying record exists. Distinguishes session presence from position availability. |
| `media_posicao_final_5` | $\sum_{r\in H_d}position_r/n_d$; empty if $n_d=0$. Lower means better numeric positions, not proof of finishing every race. |
| `taxa_podios_5` | $\sum_{r\in H_d}1(1\le position_r\le3)/n_d$; empty if $n_d=0$. Recent observed frequency, not calibrated probability. |
| `n_posicoes_5` | $n_d$, position-mean denominator, 0–5. |
| `n_podios_5` | $n_d$, podium-frequency denominator, 0–5. Equal because statuses are not removed. |
| `media_pontos_equipe_5` | $\sum_{p\in P_e}points_p/n_e$: points per **driver record**, not total points per GP. Empty if $n_e=0$. Sprint points are not added. |
| `n_corridas_equipe_5` | $m_e$, 0–5 team events. |
| `n_participacoes_equipe_5` | $n_e$, actual points-mean denominator. Do not assume two drivers per event. |
| `historico_piloto_insuficiente` | 1 if $n_d<5$; missing history is not filled from future data. |
| `historico_equipe_insuficiente` | 1 if $m_e<5$. |
| `equipe_pre_corrida_ausente` | 1 when `equipe_id_entrada` is unavailable; points mean empty and both team counters zero. |
| `referencia_temporal_ausente` | 1 without even a reference-session date. Preserve the row without calculated history; it is not a temporally validated prediction before investigation. |

Zero counters mean no observations, **not poor performance**. Means/rates with one to four observations use only those observations and disclose the denominator. Means are not rounded before calculating other variables; CSVs preserve Python's numeric representation.

## Target and audit: mandatory separation

| Field | Role and definition |
|---|---|
| `podio` | **Target**: 1 for main-race numeric position 1–3, 0 for other known results; empty for a qualifying participant without an API result. |
| `posicao_final` | Audit: source's current numeric finishing position. Forbidden input. |
| `pontos` | Audit: current main-race points. Forbidden input. |
| `status` | Audit: original outcome, including retirement, DNS and disqualification. Forbidden input. |
| `grid_resultado` | Audit: retrospective result grid, including zero; never replaces qualifying position. |
| `resultado_ausente` | Join audit: 1 without a result. Not an input: it can depend on post-cutoff information. |

DNS, Did not start, retirements and disqualifications with a result record remain in history and target according to numeric position. This avoids selectively excluding poor outcomes, but includes administrative positions assigned by the source. These positions are not pace measures or necessarily positions when crossing the finish line.

## Team changes, rookies and sample start

Driver history follows literal `driverId` through team changes. Team history follows **literal constructorId**: renamed teams with the same ID keep history; different IDs are not manually merged even with sporting continuity. A renamed team's history may therefore restart.

No observations since 2021 does not necessarily indicate an F1 debut: it can mean a veteran at sample start or a return after an absence. No 2020 collection artificially fills the start. Missing position, missing team and short history have separate indicators. No learned imputation, scaling or feature selection was fitted at this stage.

## Attribution and limitations

Public Jolpica-F1 data, CC BY-NC-SA 4.0. Transformations: identifier joins, temporal windows, missingness indicators and chronological splits. Historical sources may contain later revisions, including disqualifications and position corrections. Acquisition and timestamping today do not prove historical availability.

Contracts are in the official `jolpica/jolpica-f1` repository: `docs/README.md`, `docs/endpoints/qualifying.md`, `results.md` and `races.md`. Full primary links are in the temporal protocol.
