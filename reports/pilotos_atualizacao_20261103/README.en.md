# Drivers: Mexico and scheduled updates

Created by: MBPaschoal
Status: local tests and package passed; public verification pending
Type: delivery report

[Português](README.md) · English

The descriptive baseline through Austin remains preserved. This supplement adds Mexico 2026: 67 GPs, 1,376 results, 1,362 starts and 14 DNS overall. Eight races retain rain recorded within actual racing intervals. Mexico's five NC positions are not replaced by native ranks; duels count those starts without inventing position scores.

The reference is the FIA 2026 map, Doc. 7, page 2: 17 corners, clockwise, 4.304 km. [Acquisition and hash](acquisition.json). Altitude is the previously documented point approximation of 2,234 m, not an elevation range. The earlier canonical Jolpica capture and native release 0.8.20 captures were reused after identity and hash checks. [Capture reuse](captures-acquisition.json). No predictive source, probabilities or model were rewritten.

## Behaviour and limits

Scheduled collection updates the supplement even if the weekend panel is unchanged. Identical refreshed data do not generate another version. Quality failures retain the last valid contribution; the screen shows pending states and monitoring reports delays over six hours. Retry-After persists in the cache. Updates require an edition-specific circuit reference: this registry admits Mexico 2026; future maps still need review. Future unrestricted completeness is not promised.

Ryo Hirakawa's profile exposed a mismatch between the catalogue's `file` field and a reader assuming PNG. The high-resolution original JPEG now uses its actual framing and Haas/Simon Galloway credit; profiles without approved photographs have a fallback without borrowing another face. Coverage dates and shared cards follow the validated projection.

[PT/EN contract](../../docs/en/DRIVER_UPDATES.md). Validation, packaging, CI and public observations will be recorded separately after actual execution.


## Local verification

349 source tests passed, with 31 follow-up checks after credit-label correction; 143 final portable-package tests passed. Four final-package PT/EN desktop/Android cases downloaded real CSV/SVG files and verified the original portrait SHA. The prior visual sweep passed 24 cases across six screens. 231 protected files checked against `bb83c75` remained unchanged. [Package and digest](package.json) · [Source](source-tests.json) · [Package](package-tests.json) · [Final browser](browser-final-local/acceptance.json) · [Integrity](protected-integrity.json). Work used an isolated checkout, preserving original-root drafts.


## Correction after the first hosted execution

Initial collection run `41704012731` failed because the real client constructor wrote its manifest before the query directory existed. Earlier tests used valid caches or replacement clients and missed that prerequisite. Version 0.8.23 creates the directory explicitly and tests the real client with controlled successful and 429 HTTP responses. Actual 429 interruption also persists Retry-After. Version 0.8.22 and its receipts remain preserved without rewriting its tag. The initial failure did not alter published data.


0.8.23: 351 source tests / testes de código, 143 portable tests / testes do pacote; four final-package browser cases / quatro casos de navegador finais em PT/EN e desktop/Android. [Package / Pacote](package.json) · [Browser / Navegador](browser-local-023/acceptance.json).


## Portrait correction and package 0.8.24

Version 0.8.22 navigation CI detected Norris' missing profile image: the legacy catalogue uses literal filenames as identity while the new reader required `driver_id`. The correction supports both formats and verifies all 29 portraits. Version 0.8.24 passed 352 source tests, 144 portable tests, four focused browser cases and the full journey that detected the regression. [Full journeys](exploration-local-024/evidence.json) · [Four final cases](browser-local-024/acceptance.json). Earlier versions and failures remain auditable without rewriting tags. Monitoring automatically opened issue 1 for initial collection failure; recovery still needs verification from a corrected hosted run.


## Verified automatic recovery

Corrected collection [41705250105](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41705250105) received Jolpica HTTP 200 at 19:45:21 UTC and confirmed 67 GPs with no pending states or substantive change. It created no extra version. Issue [1](https://github.com/mbpaschoal/pitwall-lab/issues/1), automatically opened after the earlier failure, was closed by monitoring at 19:45:41 UTC. [Receipt](collector-recovery.json).


## Corrected acceptance, 0.8.25

Version 0.8.24 CI passed the preceding suites, but four Audi search checks required round 18 while search correctly offered Mexico/19. Local reproduction records `19 !== 18` in all four contexts. The fix requires the team's latest validated race, preserves year/round/destination and passed those same four cases. All 11 suites remain; both independent groups must pass before release. [Reproduction](search-context-stale-reproduction/interactions.json) · [Correction](search-context-corrected/interactions.json) · [Retained matrix](browser-matrix.json).

The 0.8.25 package passed 352 source and 144 portable tests. Runtime code and data are byte-identical to 0.8.24; only version, changelogs, dependency comment and manifest differ. [Comparison](package.json). Final public/release receipts will follow actual completion.
