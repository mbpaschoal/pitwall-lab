# Fan Journey

[Português](../JORNADA_DO_FA.md)

Approved composition C, refined in revision C3, guides the entire product: Races, Drivers, Championship, Podium chances, Lab score and How it works. The blue/white/navy/red palette and Abril Fatface/Lato fonts remain. Implementation uses existing data, not the illustrative numbers in the concept board.

## Composition C across all six screens

The logo, season, GP and search share one compact header. Language flags remain at the top right. A nearby-race ribbon and six-item bottom navigation follow the approved composition.

1. **Races:** title and date over the circuit image, map on the right, observed portrait podium in visual 2–1–3 order next to circuit facts and weather.
2. **Drivers:** an identified Daniel Ricciardo helmet-and-cockpit photograph in a right-side panel, with Oscar Piastri on a wet track in the backdrop. These are separate photographs: Ricciardo at Miami in May/2024 and Piastri at Silverstone in July/2024; they do not represent the same person, event or weather. A direct question, condition shortcuts and portrait rankings complete the screen. Each leader has four bars: rain, no recorded rain, heat and anticlockwise circuits. Every tied leader remains visible; complete rankings, criteria, profiles and duels stay accessible. Period, metric and minimum starts live in compact filter controls.
3. **Championship:** Lewis Hamilton cockpit photograph, season progress and complete standings with portraits and team identifiers. No source rows are removed.
4. **Podium chances:** a historical Sergio Pérez at Miami photograph and before/after timeline with explicit emission-time context. The earlier stage contains individual probability bars; the later stage gives more space to the observed podium when available. Cards remain optional, and the historical photograph does not depict the forecast's GP.
5. **Lab results:** Max Verstappen at Silverstone photograph, per-GP visual comparisons with qualifying and two insight cards. Missing forecasts are not scored zero and future races have no observed result. One evaluated race is never presented as six evaluated races to imitate the mockup.
6. **How it works:** identified Andrea Kimi Antonelli cockpit photograph, three illustrated steps and two document links. Technical detail stays in an expander which opens when following a document link.

All 26 circuit photographs and five hero photographs are naturally at least 2488 pixels wide. The 29 portraits exceed the minimum of 512 pixels on each axis; 28 are 1336 pixels wide. The app uses these original sources: enlarging the former 93 × 93 portraits would not add detail. Portraits do not establish a driver's historical uniform or team. [Image credits](../../dashboard_assets/fan/ATTRIBUTION.md) and [resolution checks](../../tests/test_high_resolution_assets.py) record sources and dimensions. The mockup guides composition and navigation; displayed figures come from real artifacts, without copying its fictional values. No recorded rain does not prove a dry track, and the four condition samples can overlap.

## Navigation

Six destinations appear in the bottom navigation, with icons, labels and visible selection. The native control supports keyboard interaction. The page reserves bottom space so the menu does not remove content. Season and GP selectors appear at the top of context-dependent areas. The selector includes every event; the visual ribbon shows nearby events and identifies the selected one. Mobile emphasizes the selected GP and its neighbors.

Races retains six chapters through tabs: Summary, Sessions and laps, Tyres and pit stops, Weather, At this track and Teams. The image and outline precede the podium. Tabs preserve existing routes and avoid opening every table in a single long page. Drivers retains highlights, profiles and duels with independent filters. Championship retains every published driver and constructor row, now in sequence. Sources, limitations and documents remain accessible throughout the product.

## Optional cards

In Podium chances, **Open the GP cards** opens an optional dialog. Direct links can use `?tela=Previsões&temporada=2026&gp=19&cartas=1&lang=en`. Close with X, Escape or the table link. Closing or changing GP clears the opening state. Normal navigation never opens the dialog automatically.

Drivers come from the selected GP's stored favorites, including ties. Cards show only artwork, name and team; percentages remain in the forecast table. There is no random draw, recalculation or P1/P2/P3 prediction. The GP record determines the team; its colours appear inside the illustration — on the racing suit, helmet and ornaments — as well as on the frame. Hamilton in Mercedes/2024 never receives Ferrari artwork from a later period. Missing forecasts do not produce cards. Retrospective studies are labeled accordingly. Missing verified artwork remains explicitly unavailable, without borrowing another driver or a generic helmet. Mobile stacks cards in a scrollable dialog.

The team catalogue contains 126 AI-generated illustrations: three poses for each of the 42 recognised driver/team combinations in the archive, covering 29 drivers. Poses show a helmet under one arm, crossed arms with a helmet resting alongside, and a helmet held in both hands in front. Each trio receives three distinct poses. Additional tied favourites remain included without changing their ranking. Selection is deterministic for the GP context. The three approved original Verstappen, Hamilton and Russell cards remain byte-identical and take priority when the team matches. The 87 neutral bases are a separate historical archive and never substitute for missing coloured artwork. An unrecognised team, missing image, invalid hash or incompatible period remains explicitly unavailable.

The [HTML card gallery](../galeria-cartas.html) displays variants by driver and team outside the app. Paths are relative: open it alongside the image directory from the repository or exported package. The dashboard loads only the requested favourites' cards. Illustrations are decorative, not photographs, endorsements or outcomes. Credits: [card artwork](../../dashboard_assets/tarot/ATTRIBUTION.md). Probabilities remain individual and never predict finishing order.

## Filters and samples

A shared link retains driver, period, metric and minimum starts even when the saved browser favorite differs. Updating a favorite does not silently change the analysis period. Clearing the period or conditions is intentional: controls stay editable, and the corresponding chart remains absent with a prompt to select data. A driver without starts in the period remains selected without an unobserved chart. Counts appear as integers; percentage formatting is reserved for rates.

## Language and rendering

From 0.7.1, English translation parses HTML before translating its text and accessibility labels. Base64 images and fonts, CSS, URLs and identifiers remain intact, keeping message rules away from megabytes of embedded media. Language review must also open populated standings, such as Championship/2026/18: an event without standings does not exercise the same volume. Images retain their natural resolution. [Translation regressions](../../tests/test_i18n.py); local timings and public availability remain separate checks.

## Preserved limits

Navigation remains offline: it neither collects data, trains nor runs inference. Registered forecasts, retrospective analysis and later observations retain their meanings. Frozen v1, its 15 inputs and previous emissions remain preserved. A new interface does not fill provider gaps; those remain explicit.
