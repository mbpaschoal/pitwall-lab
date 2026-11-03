# Rafael Câmara and São Paulo preparation

English · [Português](README.md)

Created by: MBPaschoal
Status: implementation under validation; canonical driver identity pending
Type: delivery evidence

F1 announced Rafael Câmara at Haas for São Paulo on 3 November 2026 at 20:30 UTC. Subsequent identity lookups returned 35 season drivers from Jolpica and 22 drivers for São Paulo qualifying from OpenF1, without Câmara; the latter still listed Ocon and Bearman at Haas. These preparation queries are neither a homologated entry list nor a predictive snapshot. His canonical ID and race number remain unknown; a desired 2027 number and another driver's ID were not adopted.

## Operational changes

- The reviewed São Paulo policy requires an exact Rafael Camara/Câmara record at Haas and rejects Ocon before inference. The canonical ID comes unchanged from received qualifying. Names are assertions, never fuzzy ID joins. A conflict blocks the attempt and preserves diagnostics and originals.
- The OpenF1 route retains its literal mapping requirement. No ID or number is invented to unlock it. The canonical route can admit the original ID supplied by validated qualifying.
- Tarot is optional: `artwork_coverage` records missing driver/team/pose illustrations without withholding a valid forecast or removing participants. Scientific validation still requires 22 unique IDs. The existing interface can show unavailable artwork without borrowing another face.
- Frozen v1 already handles rookies through support flags. A new test confirms missing means, zero own-history counts and no inherited Ocon history. Team history remains team history. No weights, inputs or registered probabilities were changed.

## Official photograph and three staged illustrations

The [original official portrait](sources/camara-f1-3392.webp) actually contains **1920 × 1080 pixels** despite the URL's 3392 parameter. Original bytes are preserved without upscaling or local cropping. Rights remain with their holders; no open licence is asserted.

Three **1024 × 1536** illustrations use the photograph for likeness, including clear glasses, and approved cards for style. Haas red, white and black are prominent. No probabilities or unconfirmed number appear. Visual inspection checked the name/accent, full border, natural hands and distinct poses.

| Variant | Composition | File |
|---|---|---|
| 1 | Standing, helmet under arm | [Card 1](drafts/rafael-camara-haas-pose-0.png) |
| 2 | Seated on tyres, hands on thighs | [Card 2](drafts/rafael-camara-haas-pose-1.png) |
| 3 | Leaning on tyres, one hand in pocket | [Card 3](drafts/rafael-camara-haas-pose-2.png) |

Generated with the built-in `image_gen` tool. [Prompts and references](prompts.json), [hashes and dimensions](artwork-receipt.json). These presentation drafts remain outside the active catalogue pending review and a verified canonical ID. Artwork neither picks favourites nor constitutes a forecast.

## Sources and validation

- [F1 announcement](https://www.formula1.com/en/latest/article/f2-racer-camara-to-make-f1-debut-at-sao-paulo-grand-prix-as-haas-confirm-ocon-will-not-return.12Qa0tpaMZ9kgnEuGJBKFp), [original capture](sources/f1-camara-announcement.html), [URL, UTC and SHA](sources/announcement-receipt.json).
- [Serial identity queries](sources/identity-receipts.json), [original Jolpica](sources/jolpica-drivers-2026.json), [original OpenF1](sources/openf1-saopaulo-q-drivers.json). No future results or predictive use.
- [Photograph origin and rights](sources/portrait-receipt.json).

Operational tests cover the replaced driver, wrong team, rejected similar names, foreign GP, altered source, missing artwork, incomplete population, byte-preserving recovery and a rookie without borrowed history. Local tests, GitHub publication and served deployment require separate receipts; CI and public approval are not anticipated here.

## What this delivery taught us

Three artworks for every catalogue driver do not certify coverage of an event's actual entrants. The announced replacement exposed two separate responsibilities: validate the real qualifying population and measure visual coverage. The former remains mandatory; the latter accompanies a forecast without preventing publication. This avoids both forecasts for replaced drivers and an optional decoration blocking valid probabilities.

## Local validation of this revision

**401 source tests passed**, including 27 post-Q operational cases. Byte comparisons found **533 protected scientific files and prior sources unchanged**. No real forecast was emitted. [Test receipt](source-tests.json), [full output](source-tests.txt), [integrity](protected-integrity.json). Package, CI and served deployment require separate checks after committing.
