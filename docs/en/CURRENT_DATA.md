# Current data, corrections and limitations

[Português](../DADOS_ATUAIS.md) · English

Drivers includes 2026 Mexico and São Paulo through traceable supplements. Coverage reaches **68 GPs, 1,398 results and 1,383 starts**. NC records retain a missing position and contribute to start counts when a start was verified. The baseline still covers 66 GPs and 330 sessions. [Workflow, sources and automatic pending states](DRIVER_UPDATES.md).

The descriptive archive is separate from v1 inputs: 66 GPs/330 sessions in 2024–2026 through Austin. Supplementary acquisition on 29 October was serial and cached. The nine scientific artefacts and previous recorded predictions were preserved.

## Team profiles

Profiles cover all 11 teams on the 2026 grid. Base, power unit and technical leadership reflect sources checked on 11 November 2026. The selected GP stays in the links back to race team results and standings.

Titles through 2025 come from historical standings and driver entries by constructor in F1DB v2026.19.0 under CC BY 4.0. Fangio clinched the 1954 title with Mercedes and also raced for Maserati that year. The FIA confirmed Mercedes' ninth constructors' title and Kimi Antonelli's drivers' title in 2026. Renault, Benetton and Brawn GP retain their individual championship credits. [Catalogue and team sources](../../frontend_assets/perfis_equipes.json) · [F1DB](https://github.com/f1db/f1db/releases/tag/v2026.19.0)

Local campaigns show each constructor's accumulated points and position by round. Each 2026 Mercedes campaign stops at the round where its title was clinched. Title years before the local coverage link to the corresponding Formula 1 standings.

## Drivers' Hall of Fame

The Photo Archive uses originals with a license for each photograph. The catalog records credits, sources, dimensions and hashes of the local variants. The inventory cross-references F1DB championship results with chassis entries. Seasons with several chassis require historical verification of each model. [Photo catalog](../../frontend_assets/acervo_fotografico.json) · [Inventory](../../frontend_assets/inventario_campeoes.json)

Champions Duel calculates age from the birth date and the date of the deciding Grand Prix recorded in F1DB. The count includes the first title season and every earlier season in which the driver started at least one Grand Prix.

The catalogue covers 36 champions and 77 titles from 1950 to 2026. The driver list matches the official Hall of Fame. F1DB v2026.20.0 supplies title seasons, constructors, deciding Grands Prix and statistics through the São Paulo race on 8 November 2026. The profiles link to the official biographies and the FIA's confirmation of Antonelli's title. The 1954 entry records Fangio's season with Maserati and Mercedes. [Catalogue](../../frontend_assets/hall_da_fama.json) · [Formula 1 Hall of Fame](https://www.formula1.com/en/drivers/hall-of-fame) · [F1DB v2026.20.0](https://github.com/f1db/f1db/releases/tag/v2026.20.0)

## Full calendar audit

The 9 November 2026 audit covers all 15 pages across 71 selectable rounds for 1,065 combinations. The calendar has 24 rounds in 2024, 24 in 2025 and 23 in 2026. The [inventory by round and session](../evidence/auditoria-calendario-20261109.json) records coverage and missing fields in the distributed files.

| Pages | Coverage and gaps |
| --- | --- |
| Predictions for this GP · How the Lab did | 68 GPs have probabilities, including 65 retrospective studies and three pre-race forecasts. Spain and São Paulo 2025 were excluded from the retrospective rankings. São Paulo 2026 still awaits admission to the post-race assessment. |
| GP overview · Sessions and laps | All 68 races have results, and 340 sessions have aggregate timing. Individual laps cover all 68 main races and eight other sessions at 2026 Mexico and São Paulo. Baku 2025 qualifying has a separate FIA supplement. The other 263 sessions have aggregate times in the package. Of the distributed individual lap records, 527 have no duration. |
| Tyres and pit stops | All 68 completed GPs have tyres and main-race stops. At 18 Sprint weekends the selector now opens on the main race. Sprint has tyre stints and no pit-stop records in this archive. Nine of 2,492 main-race stops have no duration, all at Mexico 2026. |
| Weather | 68 races have observed temperatures, rainfall records and mean humidity, pressure and wind readings. Atmospheric context and archived forecasts are shown separately where available. |
| Circuit history · Teams at this GP | 70 GPs have earlier editions at the same circuit. Madrid made its debut in 2026. The 68 completed GPs have team results. |
| Driver profiles · Head to head | Both use the descriptive archive of 68 GPs. The position-change panel has its own 67-GP window through Mexico 2026. |
| Drivers' championship · Teams' championship | Both standings tables are available for all 68 completed rounds. |
| How it works · Sources and limits · F1 terms | Method, references and glossary use the same content across all GPs. |

Las Vegas, Qatar and Abu Dhabi 2026 are the three upcoming rounds at the audit cutoff. Circuit facts and track history are available. Recorded forecasts, results, timing, tyres, stops, observed weather and round standings still await data. Inventory gaps refer to the distributed archive.

## São Paulo — 9 November 2026 review

All five sessions have received-data status. FP2 retains the 21 cars classified by the FIA. Mean track temperature during the race was 24.6 °C from 95 valid readings with 98.95% coverage. The isolated zero was excluded from the mean and preserved in the original capture. The collector also received the revised classification with penalties for Antonelli and Leclerc, plus round 20 standings. The recorded São Paulo forecast remains available. The P1 research comparison remains inadmissible because the dashboard receipt was missing before the start. [Review receipt](../../operacao2026/adjudicacoes/2026-20-interlagos.json) · [FIA final classification](https://www.fia.com/system/files/decision-document/2026_sao_paulo_grand_prix_-_final_race_classification.pdf) · [P1 coverage](https://github.com/mbpaschoal/pitwall-lab/releases/tag/p1-2026-20-interlagos)

### São Paulo coverage by tab

| Tabs | Coverage and gaps |
| --- | --- |
| Predictions for this GP · How the Lab did | The pre-race forecast is available. São Paulo's result still awaits admission to the forecast scorecard. The classification is already available in Races. |
| GP overview · Sessions and laps | Podium, circuit facts and a shortcut to the full classification. All five sessions have published times. Available laps can be explored by driver and session. |
| Tyres and stops · Weather | Published stints and stops by session, with source gaps marked. Observed weather includes rain, temperatures, humidity, pressure and wind speed. The archived forecast has a separate section. |
| Circuit history · Teams at this GP | Five prior editions from 2021 to 2025, with a filter for the current roster. The teams table groups 22 race results into 11 teams. |
| Driver profiles · Head to head | Descriptive archive of 68 GPs. The profile's position-change panel has its own cutoff through Mexico 2026. |
| Drivers' championship · Teams' championship | 25 drivers and 11 teams at round 20. |
| How it works · Sources and limits · F1 terms | Method, references, scope and glossary. These pages document the product and its sources. |

## Mexico — opening compound recovered on 2 November 2026

All five operational Mexico sessions have received-data status after review. Lawson's opening FP3 run is recovered as **MEDIUM on laps 1–8**: GP Tempo directly identifies the compound on laps 2–8, while FIA confirms an uninterrupted opening eight-lap run. Lap 1 is explicitly identified as documentary reconstruction by continuity in the interface and CSV. Its missing lap time and initial tyre age remain unknown.

The tyre selector exposes practice, qualifying and Race with session-specific pit-lane passages. Native and reviewed coverage remain distinct; received-data status does not certify complete source fields. Catalogue review retains observed race timing and preserves the conservative free-access wait in a separate field. [Sources, reconstruction, versions and public receipts](../../reports/lawson_tyres_mexico_20261102/README.md).

Version **0.8.20** is confirmed on the public site in PT/EN and desktop/mobile with actual CSV downloads. The automatic update retained the recovery and refreshed championship standings.

This operational supplement does not automatically extend the Drivers conditions archive or change the model and registered probabilities. Versioned records below are historical and retain the limitations known at each delivery.

## Mexico alternative sources — 0.8.3

Documentary review recovers all 22 FP3 times and identifies Lawson by number, name and team in this event's official entry list. Temporal scope excludes one pre-FP3 pit record and 84 pre-qualifying records; originals remain preserved. The final classification and stewards' decision establish Lawson as DSQ, without a numeric position or valid times.

The track mean now uses 100 valid readings: 40.7 °C, 98.0% coverage, without interpolation. The FIA report also records the anomalous zero; it does not reveal that minute's real temperature. Lawson's initial FP3 compound (laps 1–8) remains unavailable and is not inferred from later stints. Reviews reach both cache and automatic collection. [Sources, decisions and remaining gaps](../../reports/mexico_fontes_alternativas_20261101/README.md).

## Mexico operation — 0.8.1

The separate weekend feed now contains 22 observed results, 1360 lap records, tyres, stops and full round-19 standings (24 drivers and 11 teams). Weather uses actual racing intervals: mean air temperature is 24.2 °C; the track mean is withheld because an isolated 0 °C reading lies between 37.4 and 37.5 °C. FP3 and some qualifying pit data remain partly withheld because source profiles are missing. Operational data do not silently extend the Drivers conditions archive or alter the model or its scientific evaluation. [Audit and outstanding gaps](../../reports/auditoria_calendario_mexico_20261101/README.md) · [Automatic operation](WEEKEND_OPERATION.md).

## Drivers quality gate — 0.2.0

The [current audit](../../reports/pilotos_condicoes_20261029/README.en.md) supersedes the tyre status in the initial review below: 295 checks handled, 50 bounds adjudicated, nine compounds recovered and 17 practice/qualifying compounds unavailable in both consulted feeds. These gaps remain missing and block analyses that need them; they do not affect race-result comparisons by conditions. There are 66 main races, 1,354 results, 1,340 starts and eight races with rain recorded during actual racing intervals. All 66 FIA maps were reviewed by edition, including lengths that changed between years and Suzuka's figure-eight layout. No same-race result entered the frozen predictions.

## The 112-item queue

| State | Count |
|---|---:|
| Qualifying conflicts resolved through documents | 71 |
| Baku/Q recovered through alternative FIA source | 1 |
| Corrected quality states | 2 |
| Archive origin identified | 1 |
| Absences confirmed in the official table | 6 |
| Tyre limitations confirmed at source | 31 |

The 71 conflicts comprise 55 confirmed archive values, 11 confirmed canonical values and five DQ markers retained as a distinct category. No numeric DQ position was invented. The six absences did not become fabricated times or sporting explanations.

Baku/Q 2025: 243 FIA passages, comprising 223 durations and 20 reference clock times for 20 drivers. No invented UTC, sectors or validity flags. Remaining tyre limitations comprise 17 stint and 14 strategy cases; checks of 17 sessions confirmed 50 absent/inconsistent boundaries. Alternative FastF1 retrieval encountered 401/404 and stopped; this does not prove absence across every possible source.

## History and circuits

History uses literal circuit identity and earlier dates, excluding the current race, future races and Sprint. It shows up to five available previous editions by driver. Austin 2026 uses 2021–2025; Austin 2024 uses 2018, 2019, 2021, 2022 and 2023 without inventing 2020. Madrid does not inherit Barcelona. DNS/DSQ are result records, not evidence of an actual start.

The 26 profiles include approximate altitude at calendar coordinates from Open-Meteo/Copernicus DEM GLO-90. Austin is 154 m at that point/model, without a claim about circuit minimum/maximum elevation. DRS activation-zone counts use FIA 2025 references, not certification of each historical configuration. DRS does not apply in 2026. Records established after a selected season are not projected backwards.

## Public evidence and local reproduction

The [verification summary](../evidence/data-resolution.json) records counts, hashes and official URLs. [Qualifying supplements](../evidence/qualifying-complements.csv), [FIA laps](../evidence/fia-laps.csv) and the [adjudicated queue](../evidence/pendencias.csv) retain canonical IDs and original values. English definitions appear in the dictionary and summary. Queue evidence paths refer to the local archive; raw documents/caches are not redistributed through this index. Official URLs allow source inspection; acquisition today does not establish historical availability.

Archive origin was identified through original-ZIP metadata, Kaggle ID and equality of 14 CSVs. Original acquisition UTC remains unknown. The currently declared licence does not separately certify the historical version. [Source-specific conditions](../../publicacao/templates/FONTES_E_DADOS.md) remain distinct.

## Tyre-age revision — 0.8.2

Presentation 0.8.6 labels missing or `UNKNOWN` compounds as “Not reported” and provides a textual legend for known codes. Initial age is the laps already accumulated by the tyre set at the start of the stint: zero remains the published value without proving new tyres, while missing age stays empty in the table/CSV. Hover uses the same age; bar width still represents only published boundaries. “Comparable boundaries” refers to the driver’s stint sequence, not the validity of tyre age or compound. These PT/EN display changes do not alter the base archive, complement or forecasts.

The [v1 complement](../../frontend_assets/complemento_idade_pneus_v1.json) revises only initial age for 262 archive stints across 55 sessions and 47 Grands Prix: 210 previously zero values are now positive, 36 changed to zero and 16 changed between positive values. The details table and CSV show revised ages; chart compounds and lap bounds remain unchanged.

The base projection and original snapshots remain intact. The reader applies the revision offline, checking hashes and a unique match by session, driver, compound, lap bounds and previous age. A missing required revision or mismatch fails explicitly. The JSON retains native identities, source URLs, hashes and UTC capture times for the three historical responses used in the audit. These are later descriptive revisions, not information retrospectively available at the forecast cutoff.

The 194 structurally revised cells and 58 without unique linkage remain excluded. All 388 operational Mexico ages already agreed with the captured response and were left unchanged. [OpenF1 PR #478](https://github.com/br-g/openf1/pull/478) explains the `StartLaps` change; not every upstream revision is automatically attributed to it. The v1 model and recorded forecast probabilities remain preserved.


## Mexico posterior evaluation — 0.8.7

The final FIA classification admits all 22 podium targets: Lab 2/3, qualifying 1/3, zero exclusions. Five documented retirements retain unknown positions. The public annex is hash-bound to the frozen emission; later evidence never changes its probabilities or rankings. [Audit report](../../reports/avaliacao_mexico_20261102/relatorio.en.md).
