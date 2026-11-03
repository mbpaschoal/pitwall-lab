# Drivers: Mexico, automatic updates and acceptance

Created by: MBPaschoal
Status: released and public build verified; mobile export limits documented
Type: delivery report

[Português](README.md) · English

Mexico 2026 joins Drivers analysis: **67 GPs, 1,376 results and 1,362 starts**. Profiles, filters, duels, search and shared cards use the validated supplement while preserving the 66-GP baseline through Austin. Mexico's five NC positions remain missing: starts enter denominators, but unknown positions do not enter duel scores.

The confirmed live version is **0.8.25**, build `5e6f3c3be744311d0ecda31df1dcf640923e0f4351ed9b33221147b7c67ed7e7`. [Served build](public-build-025/public-build.json) · [Package and comparison](package.json). Runtime code and data are identical to 0.8.24; 0.8.25 fixes acceptance and its CI grouping. Frozen v1, recorded probabilities and predictive inputs remain preserved.

## Automatic behaviour

Serial GitHub Actions collection appends completed GPs after checking identity, population, starts, results, actual racing weather and an edition-specific circuit reference. This works even if only Drivers changes. Identical refreshes create no release. Disagreements retain the last valid contribution, show pending states and trigger monitoring after six hours. Retry-After persists across runs.

Actual recovery was verified in [41705250105](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41705250105): Jolpica HTTP 200, 67 GPs, no pending state or substantive change. Run [41706516200](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41706516200) reconfirmed it. Monitoring closed [issue 1](https://github.com/mbpaschoal/pitwall-lab/issues/1) automatically. [Receipt](collector-recovery.json) · [PT/EN contract](../../docs/en/DRIVER_UPDATES.md).

## Sources and preservation

- Previously [captured canonical Jolpica results](../saopaulo_readiness_20261103/admitted-sources/mexico-results.json) and native 0.8.20 captures were reused without rewriting originals. [Reuse and digest](captures-acquisition.json).
- FIA 2026 map, Doc. 7, page 2: 17 corners, clockwise, 4.304 km. [Capture URL, UTC and SHA](acquisition.json). Altitude of 2,234 m is an Open-Meteo point approximation, not the circuit elevation range.
- Weather uses actual racing intervals, excluding red-flag suspensions and the previously adjudicated anomalous reading. The supplement invents no cloud cover or WMO code for Mexico.
- Baseline SHA remains `dfc760dfb9a78e2cf087c89b7175ab671070bc2b6eed3dab70297a2df7ae2535`; 231 protected files were checked unchanged. [Integrity](protected-integrity-final.json). Original-root drafts were excluded; work used an isolated checkout.

## Verification and learning

352 source and 144 portable-package tests passed locally. All 11 Chromium/WebKit suites remain, split into two groups that must both pass before release. [Matrix](browser-matrix.json) · [Source tests](source-tests.json) · [Package tests](package-tests.json).

| Discovered problem | Verifiable correction |
|---|---|
| An uncached query failed before writing its manifest | Version 0.8.23 creates its directory and tests the real constructor, HTTP handling and 429. Hosted collection recovered. |
| Legacy profiles lost portraits without explicit `driver_id` | Version 0.8.24 retains literal file identities and verifies all 29 portraits; Hirakawa uses the original JPEG with correct credit. |
| A test required Audi round 18 after Mexico | Version 0.8.25 requires the team's latest validated race. [Reproduced failure](search-context-stale-reproduction/interactions.json), [four corrected cases](search-context-corrected/interactions.json), no removed checks. |

Tags, earlier failures and receipts remain preserved. The lesson is to check each data consumer and actual states, exercise uncached clients and avoid UI expectations pinned to a historical round.

## Public proof and limits

[Public acceptance](public-acceptance.json): data, real portraits and duels checked in PT/EN, desktop and phone-width views. Native CSV/SVG exports were saved in both desktop languages and Portuguese Pixel 7 emulation. English at 390px used desktop bootstrap and read-only checks; native English mobile SVG saving was not certified. Some sessions had intermittent loading and cancelled downloads; earlier attempts remain in the local vault, with published [bootstrap](browser-public-025-mobile-en-r3/mobile-en-failure.json) and [cancelled-download](browser-public-025-responsive-en/mobile-en-failure.json) examples. No physical phone was tested. Receipts distinguish these cases and 0.8.24/0.8.25, whose runtime is identical.

The current registry admits Mexico 2026. **Upcoming circuit editions still require reviewed references**; otherwise the GP stays pending and monitoring reports it. The baseline's 17 tyre-compound gaps remain declared and excluded from rankings. São Paulo forecasting still awaits Q and an admitted predictive snapshot; no new prediction or training occurred.

## Final publication

[Release 0.8.25](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.25) is published and highlighted as Latest. All [tag CI](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41710817366) gates passed: 352 source tests, 144 portable tests and 11 browser suites. ZIP: 665,854,558 bytes, SHA-256 `d927d471984e0c42d1306f7282c646ce14465f8546904ea9134f33cc5eaf11cd`, matching the local package. [Final receipt](delivery-final.json). The independent [main CI](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41710817082) also passed verification; publication there is intentionally skipped because it is tag-only.
