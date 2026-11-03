# Drivers: Mexico and scheduled updates

Created by: MBPaschoal
Status: local implementation; publication checks pending
Type: delivery report

[Português](README.md) · English

The descriptive baseline through Austin remains preserved. This supplement adds Mexico 2026: 67 GPs, 1,376 results, 1,362 starts and 14 DNS overall. Eight races retain rain recorded within actual racing intervals. Mexico's five NC positions are not replaced by native ranks; duels count those starts without inventing position scores.

The reference is the FIA 2026 map, Doc. 7, page 2: 17 corners, clockwise, 4.304 km. [Acquisition and hash](acquisition.json). Altitude is the previously documented point approximation of 2,234 m, not an elevation range. The earlier canonical Jolpica capture and native release 0.8.20 captures were reused after identity and hash checks. [Capture reuse](captures-acquisition.json). No predictive source, probabilities or model were rewritten.

## Behaviour and limits

Scheduled collection updates the supplement even if the weekend panel is unchanged. Identical refreshed data do not generate another version. Quality failures retain the last valid contribution; the screen shows pending states and monitoring reports delays over six hours. Retry-After persists in the cache. Updates require an edition-specific circuit reference: this registry admits Mexico 2026; future maps still need review. Future unrestricted completeness is not promised.

Ryo Hirakawa's profile exposed a mismatch between the catalogue's `file` field and a reader assuming PNG. The high-resolution original JPEG now uses its actual framing and Haas/Simon Galloway credit; profiles without approved photographs have a fallback without borrowing another face. Coverage dates and shared cards follow the validated projection.

[PT/EN contract](../../docs/en/DRIVER_UPDATES.md). Validation, packaging, CI and public observations will be recorded separately after actual execution.
