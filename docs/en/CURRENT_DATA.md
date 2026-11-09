# Current data, corrections and limitations

[Português](../DADOS_ATUAIS.md) · English

Drivers includes 2026 Mexico and São Paulo through traceable supplements. Coverage reaches **68 GPs, 1,398 results and 1,383 starts**. NC records retain a missing position and contribute to start counts when a start was verified. The baseline still covers 66 GPs and 330 sessions. [Workflow, sources and automatic pending states](DRIVER_UPDATES.md).

The descriptive archive is separate from v1 inputs: 66 GPs/330 sessions in 2024–2026 through Austin. Supplementary acquisition on 29 October was serial and cached. The nine scientific artefacts and previous recorded predictions were preserved.

## São Paulo — 9 November 2026 review

All five sessions have received-data status. FP2 retains the 21 cars classified by the FIA. Mean track temperature during the race was 24.6 °C from 95 valid readings with 98.95% coverage. The isolated zero was excluded from the mean and preserved in the original capture. The collector also received the revised classification with penalties for Antonelli and Leclerc, plus round 20 standings. The recorded São Paulo forecast remains available. The P1 research comparison remains inadmissible because the dashboard receipt was missing before the start. [Review receipt](../../operacao2026/adjudicacoes/2026-20-interlagos.json) · [FIA final classification](https://www.fia.com/system/files/decision-document/2026_sao_paulo_grand_prix_-_final_race_classification.pdf) · [P1 coverage](https://github.com/mbpaschoal/pitwall-lab/releases/tag/p1-2026-20-interlagos)

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
