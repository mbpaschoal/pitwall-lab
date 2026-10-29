# Driver data audit

Created by: MBPaschoal  
Status: Validated for race-result comparisons by conditions; source limits disclosed  
Type: Report

[Português](README.md)

The [consolidated gate](consolidado_v1/gate_dados.json) admits descriptive comparisons by weather and circuit. It **does not claim that every source field is complete**: 17 practice/qualifying tyre compounds remain unavailable and cannot support tyre comparisons. The [295-item ledger](consolidado_v1/pendencias.csv) separates recovery, applicable absence, exclusion and source limitations.

| Check | Outcome |
|---|---|
| Main races | 66: 24 in 2024, 24 in 2025 and 18 in 2026 |
| Actual race intervals | Race status and chequered flag; suspensions excluded |
| Sensors | Rainfall, temperatures, humidity, pressure and wind pass in all 66 races |
| Rain recorded during the race | Eight races; this does not classify a wet or dry track |
| Cloud cover and WMO code | 70 hourly samples within active race intervals, covering all 66 races; ECMWF IFS/Open-Meteo reconstruction |
| Results and starts | 1,354 results, 1,340 starts and 14 DNS |
| Tyre bounds | 30 reconstructed using the alternative source; 17 zero-completed-lap records and three DNS have no applicable bounds |
| Missing compounds | Nine recovered, 30 orphan records excluded, two zero-completed-lap cases and 17 disclosed gaps |
| Circuits | 66 edition-specific FIA maps reviewed; Suzuka has its own figure-eight category |
| Preservation | 614 protected scientific files and original sources retain their hashes |

## Corrections that affect interpretation

- `session_type=Race` can also identify a Sprint. Main races are selected using the literal session name `Race`; 18 Sprints do not enter main-race denominators.
- Weekend or whole-session rainfall does not establish rain during racing. Pre-start, post-finish and suspension samples are excluded. This audit supersedes the brainstorm inventory's initial claim of 13 rainy races.
- Spa/2025 illustrates the difference between falling rain and a wet track: the start delay is not racing time. “No rain recorded” does not mean “dry track”.
- Hadjar/Australia/2025 is DNS according to the native result and [Honda](https://global.honda/en/F1/race/2025/Australia/), although the canonical table labels him retired. The supplemental denominator is corrected without rewriting the original. Zero-lap retirements and disqualified drivers with observed laps still count as starters.
- In Australia/2026, 960 unique driver/UTC timestamp/duration pairs have lap numbers differing by one. Timestamp/duration matching establishes session identity with 95.7% coverage. The [supplemental lap layer](../../frontend_assets/pilotos_condicoes.json) selects alternative-source numbering; it does not shift unmatched native rows by assumption.
- Reconstructed bounds describe alternative-source stints, not independently proven physical tyre-set identity between providers. Lawson/Australia/2025 has an explicit compound disagreement, which prevents fills across incompatible stint ordinals.
- São Paulo has 15 main numbered corners, not 16. Subdivisions such as 1A or 20A are not counted as additional main corners. Length is edition-specific: Spielberg/2024 is 4.318 km, while 2025/2026 maps report 4.326 km; Marina Bay changes from 4.940 km in 2024 to 4.927 km in 2025/2026.

## Quality rules and limits

Each sensor field must have valid observations in at least 95% of one-minute bins and no gap exceeding 180 seconds, including interval edges. This is a quality rule, not statistical confidence. Observed zero, empty, invalid and unobserved are distinct. Wind direction uses a circular mean.

Cloud cover and WMO codes are hourly gridded-model samples. They do not replace rainfall sensors, are not interpolated as measurements and do not establish a wet track. Hourly precipitation totals are not prorated into measured racing-minute rainfall. Elevation is a DEM approximation at the calendar coordinate, not mean track elevation or elevation change.

TracingInsights and OpenF1 may share the underlying F1 timing feed. Agreement verifies the data join, not independent scientific confirmation. `FastF1Generated` rows cannot supply observed laps. Public requests for the F1 timing index and a specific archive file returned HTTP 401; these responses were preserved without retries.

All 17 remaining compounds appear in [the ledger](consolidado_v1/pendencias.csv) as `lacuna_explicada_limite_fonte`. None belongs to a main race. They remain unavailable rather than assumed compounds, zeros or complete data. Any future analysis requiring these fields must fail its own quality gate.

## Sources and reproduction

- [OpenF1](https://openf1.org/docs/): race control and track sensors.
- [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api): reconstructed atmospheric context.
- [TracingInsights / tif1](https://github.com/TracingInsights/tif1/blob/main/DATA_REFERENCE.md): lap schema; yearly files are pinned to commits in acquisition receipts.
- [TracingInsights / DDocs](https://github.com/TracingInsights/DDocs/tree/9f647f7c62a838405c85219e5eb2feb5c3575027): archive of FIA/F1-authored documents, retaining original URLs, edition, hashes and publication dates. PDFs are not bundled with the public dashboard.
- [FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py): telemetry uses UTC, from which `LapStartDate` derives. Serialized pandas timestamps without an offset follow that source contract; other providers still require explicit timezones.

Collectors ran serially with cache, UTC/SHA-256 receipts and at least 3.1 seconds between requests. Reproducible local tools are `pitwall.data.race_weather`, `pitwall.data.tyre_reconciliation`, `pitwall.data.driver_source_audit`, `pitwall.data.circuit_conditions` and `pitwall.data.driver_quality_report`. Each requires a new destination to preserve prior evidence.

The frozen predictive v1, its 15 inputs, emissions and probabilities remain unchanged. These later sources serve descriptive analysis and audit.

## Reproducing the projections

```sh
python -m pitwall.data.driver_conditions --acquisition data/acervo_historico/pilotos-condicoes-20261029 --gate reports/pilotos_condicoes_20261029/consolidado_v1/gate_dados.json --output frontend_assets/pilotos_condicoes.json
python -m pitwall.data.driver_archive_projection --drivers frontend_assets/pilotos_condicoes.json --archive frontend_assets/acervo_dashboard.json --panels frontend_assets/paineis_editoriais.json --verified-on 2026-10-29
```

The first command requires the audited local snapshots, retained outside the public package. The second is idempotent and applies descriptive projections only. The portable JSON retains source hashes and observed supplements; original PDFs are not redistributed.

[Review of all 66 maps by edition, page and hash](circuitos_revisados.csv).
