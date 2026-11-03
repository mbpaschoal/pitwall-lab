# Pitwall Lab automation

English · [Português](../AUTOMACAO.md)

The main routine runs on GitHub Actions and does not need the personal computer to stay on. Cron requests a run every 30 minutes; GitHub may delay its start. Free sources, serial collection, caching and `Retry-After` remain mandatory. The interface only reads published files.

| Stage | State and control |
|---|---|
| Discover the next GP and join calendars | Automatic exact identity/date join, never another provider's round number. |
| Collect practice, Q, race, laps, tyres and stops | Automatic after an observed finish and the free-access wait. |
| Weather during the race | Sensors over actual racing intervals, with coverage/quality checks. Open-Meteo forecasts stay separate. |
| Complete championships | Exact-round endpoint; no partial-sum reconstruction. |
| Update Drivers comparisons | Automatic after results, population, weather and circuit validation. |
| References for the four remaining 2026 circuits | Admitted in this delivery using visually reviewed official 2026 F1 maps and hashes. Open-Meteo elevation is a point approximation. |
| Check upcoming references | Offline seven-day lookahead; a missing reference raises an incident. |
| Prepare São Paulo forecast | New hosted routine gated on observed Q finish. This delivery contains no São Paulo forecast. |
| Emit and register v1 | Automatic only for **2026/20/interlagos**, through the existing scientific CLI. Requires a validated snapshot, 22 drivers, admitted sources/UTCs, committed code and a roster consistent with reviewed replacements. No training or tuning. |
| Retry forecast preparation | At most four attempts, at least two hours apart, then stop and alert. |
| Recover a concurrent publication | Restore identical emission bytes and reproject on current `main`; never recalculate probabilities or force-push. |
| Version and publish data | Real changes only; PT/EN notes, package, tests, original sources and atomic push. |
| Publish a forecast on time | Recheck before push with a minimum one-hour margin before race start. Preserve an unpublished emission if the window closes. |
| Verify package, languages and navigation | Code/version CI runs both full browser suites (11 checks). Automatic data publication runs four focused browser checks plus package validation. |
| CSV/SVG downloads | PT/EN desktop/mobile tests check file bytes, language and absence of an app rerun. |
| Alert on failures or stale runs | One bilingual GitHub issue; unchanged conditions produce no comments. Healthy recovery closes the issue. |
| Select `Latest` | Highest stable release with a complete, hashed ZIP, bounded by `main`'s version. |

## Replacement drivers and optional artwork

The São Paulo review requires Rafael Câmara at Haas and rejects qualifying that still lists Ocon. Names are literal assertions on source records, never joins or manufactured IDs. The canonical qualifying `driverId` is retained unchanged. The OpenF1 route still requires a reviewed literal mapping for a new driver. The 3 November preparation lookup did not yet identify Câmara in the APIs; it is not a qualifying snapshot.

Artwork availability is reported in `artwork_coverage`. Missing or unverified art displays an unavailable state without borrowing another face or withholding a valid forecast. Scientific gates, the 22-driver population and publication timing remain mandatory. A rookie without F1 history retains zero observation counts, missing means and existing v1 support flags; the replaced driver’s history is not transferred. [Sources, staged illustrations and validation](../../reports/camara_preparacao_20261103/README.en.md).

## Review remains necessary

Source conflicts, unmapped driver/team changes, anomalous readings and layout revisions are not resolved by averaging or guessing. The system retains valid information and flags pending work. New artworks, image usage/licences and editorial changes need visual review. Training, recalibration and model promotion remain separate research with no automatic promotion.

Other GPs can receive automatic collection and descriptive comparisons. This delivery's emission policy admits São Paulo only; it does not silently enable other events.

## Operation and evidence

- [Collection and forecast workflow](../../.github/workflows/coletar-dados.yml), [admitted policy](../../operacao2026/forecast_policy.json), [orchestrator](../../operacao2026/post_qualifying.py).
- [São Paulo preparation](SAO_PAULO_PREPARATION.md), [Drivers updates](DRIVER_UPDATES.md).
- [Delivery report](../../reports/automacao_saopaulo_20261103/README.en.md).

Forecast failures do not block valid descriptive publication. Attempts retain diagnostics and files in persisted state; a new attempt's original captures also receive a 30-day workflow artifact. Published emissions/raws enter Git and the release source archive. Cache is not external publication evidence: CI, releases and the served version are checked separately.


Public 0.8.26 verification completed English CSV/SVG downloads on emulated Android without app reruns. Other attempts failed during bootstrap, Streamlit-module loading or download completion. Those limits remain recorded; a fully passing public matrix is not claimed. [Receipts and attempts](../../reports/automacao_saopaulo_20261103/README.en.md).
