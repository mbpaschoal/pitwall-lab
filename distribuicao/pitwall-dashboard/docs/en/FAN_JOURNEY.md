# Fan journey

[Português](../JORNADA_DO_FA.md)

Version 0.14.0 keeps the sidebar selected by users, Abril Fatface/Lato, Pitwall blue and the editorial identity. A compact sticky header keeps language controls available while scrolling. Analytical pages start with their title and content, without an extra location label or a repeated GP subtitle.

Race result and Predictions covers combine documented photographs with original editorial drawings for all 26 circuits: Miami Art Deco, Suzuka’s Ferris wheel, Mexico’s stadium and Interlagos bends, among other local references. Photos are visibly illustrative and have expandable credits, separate from the GP date. Artwork is decorative interpretation, not a map or scientific input. Immutable static copies keep the original photo bytes, with SHA-256-derived names, avoiding repeated photo payloads during navigation.

## Navigation

Fifteen direct destinations cover predictions and accuracy; race result, sessions and laps, tyres and stops, weather, circuit history and teams at this GP; driver profiles and duels; driver and constructor standings; method, sources and F1 terms. Mobile uses the “Explore Pitwall” disclosure and closes it after a selection. A red left border identifies the current destination.

One labelled GP dropdown uses short localized names and replaces the redundant event ribbon; the bottom menu is removed. Search and selectors share a common height and axis. Narrow-menu expansion settles immediately to keep native click targets stable. Irrelevant context selectors are hidden on Drivers and About the Lab while retaining their values for return. Search recognises task words as well as drivers, teams and races. Internal links use the same tab; native sidebar buttons have equivalent keyboard links while loading. GP and language are retained. Only the selected race chapter renders.

Race result keeps the observed podium in visual order 2–1–3. “Circuit photo and map” retains original media, sources and licences. Operational state is grouped under “Updates and coverage”. Missing data remain explicit. Each full standings table is directly accessible; older links without a panel still show both.

## Cards

Predictions initially shows the cover, temporal status and **See the cards for this GP**. Favourites, percentages and observed comparison remain outside the initial reading and accessibility tree. The button opens a pop-up with identical backs, without names, numbers or letter labels. Each click reveals one face with artwork, driver, team at that GP, recorded individual podium probability and explanation. Cards can be turned down; there is no reveal-all control.

Reveal state is stored in this browser session, scoped to season, event, emission and probabilities. Closing and reopening the pop-up, leaving and returning, or changing language preserves it. Close with X, Escape or “Back to predictions”. Another GP or emission has independent state. `cartas=1` opens backs without revealing new faces. After all available cards are revealed, comparison, distribution, coverage and technical details become accessible. Missing emissions create no cards. Retrospective studies remain identified.

Cards illustrate existing favourites, including ties, without random draws, inference or P1/P2/P3. Team identity belongs to that GP. Original artwork and catalogue remain preserved, with explicit unavailability when necessary. Individual probabilities do not establish finishing order. Mobile stacks the cards. Keyboard operation, visible focus, and reduced motion are supported.

The [HTML gallery](../galeria-cartas.html) and [art credits](../../dashboard_assets/tarot/ATTRIBUTION.md) remain available. Photographs, portraits, originals and licences are preserved.

## Validation

Acceptance covers all fifteen destinations, both languages, desktop/mobile widths, individual reveal, accessible content, return, language changes, keyboard alternatives, scrolling and downloads. The v1 model and recorded probabilities remain preserved. Local checks, CI, package and public-domain acceptance are separate. Emulated sizes and simulated enlarged text are not physical-device or native-zoom evidence.

## Composition history

The notes below describe earlier deliveries. In 0.13.0 the sidebar and sealed cards replaced the bottom navigation, event ribbon and former card dialog. Version 0.13.2 restores the dialog while keeping individual reveals.

## Continuity and access — 0.8.4

Flags retain their header position and scroll with it; accessible names, selection and programmatic language follow PT/EN. A keyboard skip link reaches the content. The schedule uses compact UTC rows; session/date labels follow the locale, preserving canonical IDs and timestamps.

Profiles offer an equivalent table of chart conditions, series, values and sample sizes, distinguishing insufficient samples from observed zero. Favourite selection sits near driver identity; head-to-head and teammate rules are explained separately. Links and criteria changes preserve a forecast's origin GP, independently of the profile's historical period.

Lab results labels its latest-six-GP window and season summary. Existing historical forecasts excluded from evaluation show a reason without a score; missing probabilities remain explicit. Documents distinguish current sources from the historical protocol and open directly in the reading area. The How it works photo uses three local viewport/DPR WebP variants; its original, credits and framing are preserved. The package delivers only explicitly allowlisted variants.

## Counts, samples and readability — 0.8.1

Lab results presents model and qualifying counts as text for every evaluated GP. Dots are decorative; unevaluated races remain unscored. Drivers displays start counts for the ranking and each condition comparison without relying on hover. Missing rates remain distinct from zero.

Small blue text uses its own higher-contrast token, while bars retain their decorative blue. Mobile navigation labels use 12 px and may wrap. Scroll clearance keeps focus above the fixed menu; on mobile, up to 600 px, ranking leaders use one column to accommodate ties and sample sizes, and navigation uses two rows. Identity, photographs and recorded probabilities remain unchanged.

On desktop, available width and text size determine the leader-card layout; larger text may move cards into a single column. Percentages retain space for their complete value.

The [local acceptance report](../../reports/ui_ux_pro_max_20261101/implementacao/relatorio.md) distinguishes automated tests, browser measurements and limitations. Simulated larger text and a 320 CSS px viewport are not presented as native browser zoom or full accessibility certification.

## Filters and samples

A shared link retains driver, period, metric and minimum starts even when the saved browser favorite differs. Updating a favorite does not silently change the analysis period. Clearing the period or conditions is intentional: controls stay editable, and the corresponding chart remains absent with a prompt to select data. A driver without starts in the period remains selected without an unobserved chart. Counts appear as integers; percentage formatting is reserved for rates.

## Language and rendering

From 0.7.1, English translation parses HTML before translating its text and accessibility labels. Base64 images and fonts, CSS, URLs and identifiers remain intact, keeping message rules away from megabytes of embedded media. Language review must also open populated standings, such as Championship/2026/18: an event without standings does not exercise the same volume. Images retain their natural resolution. [Translation regressions](../../tests/test_i18n.py); local timings and public availability remain separate checks.

## Preserved limits

Navigation remains offline: it neither collects data, trains nor runs inference. Registered forecasts, retrospective analysis and later observations retain their meanings. Frozen v1, its 15 inputs and previous emissions remain preserved. A new interface does not fill provider gaps; those remain explicit.

## Visual acceptance for delivery 0.7.3

[aceite_visual.cjs](https://github.com/mbpaschoal/pitwall-lab/blob/main/tests/browser/aceite_visual.cjs) visits all six screens in both languages, at 1040 × 992 pixels for C's upper three panels, 1040 × 875 for the lower panels and 390 × 844 on mobile, at 2× density. It records screenshots and measurements without adopting the previous CSS as an approved baseline. It checks reading order, overlaps, natural resolution, legend, full standings and controls; the observed podium and explanatory links must sit above navigation in desktop acceptance. CI retains this evidence for three days.

Comparison preserves legitimate differences: real photographs replace conceptual imagery, ties remain ties, every standings row stays available and unevaluated rounds receive no fictional scores. Space is reserved for Streamlit's external badge. The reference guides composition without a claim of pixel-for-pixel identity.
## Editorial finish and head to head — 0.10.0

The composition preserves the approved palette and typography, with restrained outlines, balanced headings, tabular numbers and grouped source tracking. Chapter, condition and expander feedback is brief and respects reduced motion.

Head to head keeps portraits and metrics side by side when space allows, including on mobile. Very narrow layouts or larger text reflow the panels into one column to preserve readability. The difference follows the selected metric, period and condition: rates are compared in percentage points and counts in integers. Ties and samples below the minimum remain explicit. The finishing-order score is independent of this metric difference. Shared starts, comparable results and evidence remain available, without changing data or recorded probabilities.
