# Driver-analysis updates

[Português](../PILOTOS_ATUALIZACAO.md) · English

Version 0.8.22 adds Mexico 2026 to comparisons: 67 GPs, 1,376 results and 1,362 starts. The original baseline through Austin stays identical. The descriptive supplement never enters the 15 inputs or changes v1 probabilities or recorded predictions.

## Workflow

GitHub Actions collects serially every 30 minutes within the operational window, respecting free access and provider waits. After observed race completion, `operacao2026/driver_archive.py` checks identity, complete population, starts, laps, points and disqualifications between canonical Jolpica results and already captured native OpenF1 data. Officially reviewed positions are used: NC does not become an assumed placing. Only then is the GP appended to `frontend_assets/pilotos_condicoes_operacao.json`, bound to the baseline hash.

Rain and sensors use actual racing intervals, excluding red-flag pauses and Mexico's previously adjudicated anomalous reading. Corners, length and direction require an edition-specific reference in `operacao2026/driver_circuit_reviews.json`. **This delivery's registry admits Mexico 2026.** Admitting upcoming circuit maps remains a documented human review; otherwise automation holds the GP pending. Earlier maps are not silently certified for 2026.

Identical refreshed receipts do not create releases; substantive changes produce a version, PT/EN notes, package and publication after validation. This also works when only Drivers changes. Browsing reads local files without API calls. The screen and shared cards show the latest validated race.

## Failures and limits

A disagreement retains the last valid contribution and an explicit on-screen pending state. Six hours after race finish the check fails, and the existing collection monitor opens or updates an issue; repeated unchanged failures stay quiet. Invalid sources or changed hashes stop execution. Retry-After persists across runners. Unpublished prerequisites can require review without periodic user reminders.

Retirements count as starts. Position means and duel scores use known official positions, excluding DSQ. Conditions overlap and do not isolate car effects. A missing portrait does not block a profile or justify another driver's photograph.

## Evidence

- [Delivery report](../../reports/pilotos_atualizacao_20261103/README.en.md).
- [Captured canonical result](../../reports/saopaulo_readiness_20261103/admitted-sources/mexico-results.json).
- [FIA 2026 edition map](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_competition_notes_-_circuit_map_pit_lane_drawing_and_emergency_exits_map.pdf), page 2, Doc. 7: 17 corners, clockwise, 4.304 km. Altitude of 2,234 m is an Open-Meteo point approximation, not the circuit elevation range.
- Update tests: `tests.test_driver_updates`; collection integration: `tests.test_weekend_cloud`; portable projection: `tests.test_driver_projection`; profiles and languages: `tests.test_pilot_views`.
