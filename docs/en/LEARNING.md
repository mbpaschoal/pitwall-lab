# Learning and product refinement

[Português](../APRENDIZADOS.md) · English

Created by: MBPaschoal
Status: active
Type: learning journal

This journal explains technical decisions; it is not a list of uniformly positive results. Historical commit messages retain their original language and date. This bilingual account adds context without rewriting history.

| Evidence | Problem noticed | Correction and lesson |
|---|---|---|
| [Stage 3](protocolo_temporal.md) | Date-ordered data can still contain later source revisions. | Separate conceptual cutoff, conservative release rule and actual acquisition. A hash proves bytes, not historical availability. |
| [2025 evaluation](relatorio_2025.md) | A model advantage can look larger without a common comparison population. | Explicit denominators and cohort: 51 versus 50 podium drivers; both 8/22 complete podiums. Do not claim significance. |
| [8beae28](https://github.com/mbpaschoal/pitwall-lab/commit/8beae28) | The sidebar became difficult to reopen. | Restore native controls and verify mobile. Appearance does not replace usable navigation. |
| [128e272](https://github.com/mbpaschoal/pitwall-lab/commit/128e272) | The main source did not cover Austin session times. | Add an identity/provenance-checked alternative, separate from the recorded prediction. |
| [0e97fbc](https://github.com/mbpaschoal/pitwall-lab/commit/0e97fbc) | Duplicate panels and incomplete standings obscured information. | Give each datum a canonical screen and display every published standings row. |
| [edca988](https://github.com/mbpaschoal/pitwall-lab/commit/edca988) | Locally working links failed in Cloud. | Test real iframe/new-tab clicks. A push is not deployment proof. |
| [Data review](CURRENT_DATA.md) | History answered a current-race question; stint warnings were treated as gaps. | Filter by literal circuit identity and earlier date; distinguish quality warnings from unknown boundaries. Preserve actual missingness. |
| [Version 0.1.0](../../CHANGELOG.en.md) | Scattered code and one language hindered maintenance and portfolio accessibility. | Organise responsibilities, centralise offline translation and retain compatibility. Product and model versions mean different things. |

## 3 November 2026 — Completion order is not version order

An older release finished after the new one and displaced its GitHub highlight. I learned to separate creation, package upload and current-version selection: the highest complete stable version now wins. I also separated normal data deferral from actual provider-access failures. The monitor opens an incident only for a problem and records recovery; repeated notifications do not make a product more reliable. São Paulo now has an offline preparation check without treating a future calendar or ready artwork as an emitted forecast.

## Recording the next improvement

Explain prior behaviour with a concrete example, known cause or uncertainty, delivered change, executed verification and remaining limitations. A hypothesis is not a confirmed finding. Dates and versions must match actual deliveries: no fabricated old commits or edited results to improve the narrative.

## 0.2.0: comparisons require a verified denominator

The brainstorm counted rain across whole sessions and could select a Sprint through the Race session type. The audit now requires the literal main-race name, start/end status and exclusion of suspensions. This changed the result to eight races with rain during active racing. I also learned to preserve feed differences: Australia/2026 lap numbers must not be corrected by shifting unmatched rows. Rates now show starts and ties; incomplete sources remain incomplete. [Evidence and limits](../../reports/pilotos_condicoes_20261029/README.en.md).

## 0.3.0 — Fair comparisons and enjoyable reading

I learned that a correctly typed field can still be semantically wrong: wind direction needs a circular mean. Comparing one driver with the entire grid also requires aligned races and denominators. Both decisions now have regression checks. Each kind of information has a clear home: results in Races, standings in Championship, estimates in Podium chances. Duels use shared starts and cards include period, sample and source. A green source-tree test does not prove the published package matches the code; delivery now checks both.

## 0.7.0 — Natural resolution, identity and context

The previous 28 portraits contained only 93 × 93 pixels. Increasing their CSS display area made them larger on screen while retaining the same lack of detail. The correction started with the source: all 29 current portraits, including Ryo Hirakawa, exceed the minimum of 512 pixels on each axis; 28 are naturally 1336 pixels wide. The 26 circuit photographs and five distinct hero photographs are at least 2488 pixels wide, covering a presentation width of up to 1244 pixels at 2× density. Dimensions, depicted identity, source, rights and SHA-256 are recorded. Resolution checks open the actual files; a catalog claim or an upscaled file would not establish source detail. [Hero catalog](../../dashboard_assets/fan/hero_catalog.json), [portraits](../../dashboard_assets/fan/sources.json) and [checks](../../tests/test_high_resolution_assets.py).

Composition C required treating six screens as one system: shared header, compact controls, image, main content and bottom navigation. Drivers' four leader bars compare rain, no recorded rain, heat and anticlockwise circuits within the selected period and metric. Every tied leader remains visible. Conditions can overlap, denominators stay explicit and no recorded rain does not prove a dry surface. Composition changes do not invent values to imitate the mockup or establish complete visual fidelity; desktop, mobile, language and interaction require browser inspection. [Journey and limits](FAN_JOURNEY.md).

Cards exposed another context problem: one Ferrari-suit illustration for Hamilton could lend that team to a Mercedes/2024 record. The 87 new artworks use neutral suits and three distinct body poses for each of 29 drivers; team names and frame colours come from the selected GP. The three approved original cards remain byte-identical and restricted to matching teams. Deterministic selection distributes three poses per trio without recalculating probabilities, reordering favorites or discarding ties. The gallery supports checking faces, hands, text and pose; the app dialog remains optional and contains no percentages. [Gallery](../galeria-cartas.html) and [tested contract](../../tests/test_tarot_catalog.py).

I also learned to distinguish a planned path, generated image, visual review and publication. The package allowlist enumerates the 87 variants and 29 portraits without scanning private folders. Hashes, resolution and local tests support the local delivery; the version served by Cloud requires its own public check. Frozen v1, its 15 inputs, probabilities and scientific evidence are not changed by presentation work.

### Three errors found in final review

A header container kept in a global variable appeared to work in one isolated session. With concurrent pages, the UI object could belong to another execution's tree and cause `Bad setIn` or a blank screen. Each execution now creates its own container and passes it explicitly to the screens. Sequential unit tests do not exercise that scenario; review now includes simultaneous real-browser pages and browser-error capture.

A shared Norris profile for 2026 could return to 2024–2026 when a saved-favorite component, for example Verstappen, triggered a rerun. The widget's serialized default differed from the URL scope. Filters now have their own canonical state, changed by explicit user choices, and widget defaults follow that state. An intentionally empty period stays empty and editable; missing starts do not replace the requested driver.

There was also a difference between an empty chart and actual absence: clearing every condition still created an unobserved chart. Counts such as 2 to 6 could appear as 200% to 600% through rate formatting. Empty condition selections or insufficient samples now disclose their absence, counts use integers and only rates use percentages. Scientific values are unchanged; scope persistence and representation were corrected. [Profile regressions](../../tests/test_pilot_views.py).

Drivers' C3 composition combines Piastri at Silverstone in the backdrop with Ricciardo at Miami in close-up: separate people, events and conditions. The visual combination cannot attribute the other photograph's wet track to Ricciardo. The catalog records both credits and makes that distinction explicit.

## 0.7.1 — Translate text after parsing HTML

English public review prompted a local measurement of Championship/2026/18: the AppTest harness took 32.178 s in EN and 0.947 s in PT, including diagnostic accounting; the English HTML totaled 15,811,142 bytes. Profiling isolated the cost in translation regular expressions that received the entire document, including base64 images and fonts, before the parser. The fix parses HTML first and translates only text and accessibility labels while preserving CSS, URLs, identifiers, media, code and exact catalogue templates. The lesson is to measure a populated screen in each language and keep binary content outside message rules; an event without standings would not be an equivalent counterexample. These timings measure local execution before the fix, not memory or public hosting performance. [Implementation](../../pitwall/i18n/__init__.py) and [regressions](../../tests/test_i18n.py).

## 0.7.2 — Team colour belongs inside the artwork

Neutral bases avoided assigning a later racing suit to historical races, but failed the visual request: Norris still had no orange inside the illustration. A coloured frame did not convey McLaren identity. The correction binds each illustration to a driver, team and compatible period, with visible colours on the suit, helmet and ornaments. Drivers who changed teams receive separate variants, while neutral bases remain archived. File coverage, historical identity and visual colour review are different checks. Selection tests alone do not demonstrate artwork quality. [Gallery](../galeria-cartas.html) and [contract](../../tests/test_tarot_catalog.py).

## 0.7.3 — Check composition as well as presence

A screen could contain every expected component while repeating a heading or hiding the end of the podium behind navigation. Visual comparison led to a compact podium with accessible full names, weather before optional details and a clear split between comparison copy and its legend. Acceptance now measures relationships between blocks in both languages and natural image density at 2×. English needs its own review: a longer sentence can change a card's height. [Contract and limits](FAN_JOURNEY.md).

## 0.8.1 — Verify the source before diagnosing

I treated “Bahrain Grand Prix in Malaysia” as an anomaly because the name appeared inconsistent. Primary verification showed Formula 1 had officially announced Bahrain's GP at Sepang. The data was correct; it needed a localised label and separation between event name and host country. The earlier record stays preserved with this explicit correction.

Mexico collection exposed three distinct causes: HTTP 401 during the free tier's live window, a revised scheduled finish and stale messages carrying current IDs. The solution separates access waiting, an audited configuration revision and recorded temporal exclusions. None permits guessed driver identities, fabricated measurements or rewriting an already recorded prediction. [Operational review](WEEKEND_OPERATION.md).


## 3 November 2026 — Collecting data does not update every comparison

Mexico was already shown on the GP panel, while Drivers stopped at Austin. I learned to check each data consumer: a traceable supplement now updates independently, even when the GP panel is unchanged. A debutant profile test also showed that valid data must not depend on an available portrait. Missing official positions and photographs have explicit treatment. [Workflow and limits](DRIVER_UPDATES.md).
