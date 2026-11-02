# Pitwall Lab evolution

## 0.8.15 — 2026-11-02

- Fixes the podium covering collection notices, portraits covering statistics and photo credits blocking links. Driver blocks and controls reserve space in normal flow; the scroll viewport ends above the fixed navigation, including after window-height changes.
- Header and selectors reflow with enlarged text. Links, search and language changes retain season, GP, profile and filters; drivers missing historical coverage get an explicit message without substitution by another driver.
- Extends acceptance to intermediate scroll positions, actual clickable targets, PT/EN, desktop/mobile and text reflow. Earlier tests missed the collisions shown in the user screenshot. Emulated Chromium/WebKit do not replace physical iPhone testing. Scientific artifacts, registered forecasts and visual identity remain intact.

## 0.8.14 — 2026-11-02

Automatic Mexico City Grand Prix data update through GitHub Actions. Sessions with received data: 4/5. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.

## 0.8.13 — 2026-11-02

Fix automatic data publication when another commit reaches main during collection/validation. Detect branch advances before commit/tag creation and after an atomic push rejection. Dispatch a fresh run on current main, restore captures and regenerate version, package and tests instead of rebasing stale generated artifacts.

Original captures survive in bounded cache and a workflow artifact before publication. A lineage allows at most two recoveries; permission/transport failures and exhaustion remain explicit. Only actually published versions undergo Streamlit verification. No force push or forecast/model changes.

Eight tests with real temporary Git repositories cover both race windows, recalculated versions, preserved tags/commits, unrelated staging and permission errors. [PT/EN runbook](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/runbooks/automatic-publication.md).

## 0.8.12 — 2026-11-02

- Fixes the motion control accessibility semantics: its name announces the available action without a toggle state contradicting its text. System preferences and persistence remain preserved.
- Completes smooth-navigation publication with portable tests, public PT/EN acceptance and reduced-motion support on desktop and emulated mobile. Earlier tags remain intact.
- Learning: a button whose name changes with its action should use action semantics without aria-pressed. Data, predictions and visual composition are unchanged.

## 0.8.11 — 2026-11-02

- Publishes the smooth navigation implemented and validated in 0.8.10 while preserving its original local tag. Focus-aware anchors, subtle feedback and a single methodology entrance respect motion preferences.
- Package prepared from the validated commit without incorporating the ongoing 0.9.0 research. PT/EN UI, data and visual identity remain preserved.
- Validation: isolated portable tests and public PT/EN desktop/emulated mobile acceptance, including reduced motion and keyboard/touch navigation. Learning: publication must bind source, package and served build.

## 0.8.10 — 2026-11-02

- Focus-aware page navigation and smooth scrolling in the Streamlit container preserve URLs and filters.
- Subtle control feedback and brief methodology step entrance, once per page session, honor system and user motion preferences.
- PT/EN desktop and emulated mobile acceptance; data, models and visual identity preserved. Local acceptance does not establish publication.

## 0.8.9 — 2026-11-02

Preventive São Paulo collection fix: an explicit configuration and a cached discovery may describe the same GP. The collector reuses the explicit configuration when identities, sessions and schedules agree; genuine identity or schedule conflicts still stop collection.

The public weekend acceptance now waits for weather metrics and completed rendering before comparing values. An earlier English mobile attempt reached the heading before the measurements; its receipt is retained. All content assertions and 22-driver result checks remain enabled.

Operational validation: 27 tests, including identical duplicate configurations and a conflicting schedule. Model, forecasts and original captures remain unchanged. [Sources and evidence](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_avaliacao_saopaulo_20261102/README.md).

## 0.8.8 — 2026-11-02

- Fixes public-checkout acceptance: legacy tests requiring local scientific captures remain part of local validation. CI retains evaluation-binding tests, UI/reader tests and the isolated portable package without private sources.
- Tag0.8.7 is preserved. This correction completes delivery of the Mexico evaluation and tyre presentation improvements; probabilities, rankings and posterior targets do not change.
- Validation: package reproduction, portable tests and public PT/EN desktop/mobile checks. Learning: public-checkout tests must declare dependencies actually available in that checkout.

## 0.8.7 — 2026-11-02

- The collector applies Mexico's final FIA classification, including post-penalty positions, times and points while preserving the earlier response in its audit. São Paulo has an explicit configuration for five sessions on 6–8 November; race start is 14:00 local time. [Operational sources and validation](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_avaliacao_saopaulo_20261102/README.md).

### Changed

- Mexico: posterior evaluation of the registered prospective prediction, bound to the emission hashes and the final FIA classification. The Lab selected 2 of 3 podium drivers; qualifying selected 1 of 3. All 22 participants are covered, with no exclusions.
- Five retirements retain an unknown finishing position and a confirmed non-podium target. Later results do not alter the recorded probabilities or rankings.
- Exclusion reasons and pending states remain readable in Portuguese and English, without an invented score.
- Validation: UI/reader and evaluation-binding tests, isolated portable package and six-screen acceptance in PT/EN, desktop/mobile. Limitation: two evaluable prospective races do not establish superiority.


[Português](CHANGELOG.md) · English

Versions describe product deliveries. Scientific model v1 remains frozen. Earlier commits have not been assigned retrospective versions.

## 0.8.6 — 2026-11-02

- Focused tyre review: missing or `UNKNOWN` compounds appear as “Not reported” in the table, CSV and legend. Known codes retain their identities with a textual legend; original data is not normalised or overwritten.
- Initial age is explained as laps already accumulated by the tyre set before the stint. Zero remains a published value without proving new tyres; missing age stays empty. Hover shows the same age as the table, including single-lap markers, without changing boundaries or bar widths.
- Comparable boundaries uses Yes/No/Not reported in EN and Sim/Não/Não informado in PT, with its driver-sequence scope explained. Stints without valid boundaries remain in the table without invented bars.
- Local validation and delivery limits are recorded in `reports/revisao_pneus_p02_20261102/`. The frozen v1 model, 262-stint complement, snapshots and registered forecasts are preserved. Local evidence does not establish a new public deployment.
- Learning: tyre age, compound and boundary validity are separate facts; legends and units must explain the distinction without inferring new tyres from zero.

## 0.8.5 — 2026-11-01

- Fixed weekend acceptance to select FP3 in English and TL3 in Portuguese. The canonical session identifier and checks of all 22 drivers, Lawson timings, disqualification and CSV content remain unchanged.
- Version 0.8.4 reached main and the dashboard, but its automated release was blocked by the test's old selector. Its commit and tag are preserved. This correction completes delivery of the 22 UI/UX improvements through bilingual publication checks.
- Interface behaviour, descriptive sources, frozen v1 and recorded probabilities remain as implemented in 0.8.4. Validation covers the corrected acceptance, isolated-package tests and the public served build in PT/EN, desktop and emulated mobile; receipts live in `reports/ui_ux_pro_max_implementacao_20261101/publicacao/`.
- Learning: UI tests must locate the selected language's display label while preserving scientific IDs and independent content checks.

## 0.8.4 — 2026-11-01

- Implemented all 22 proposals from the six-screen review, preserving composition C, palette, Abril Fatface/Lato, documented photos and approved cards. A compact UTC schedule, mobile driver-team labels, one GP ribbon and localised session/date labels improve PT/EN parity.
- Profiles expose an equivalent table of chart conditions, series, values and sample sizes; favourite selection sits near driver identity. Head-to-head and teammate rules are explained separately. Profile visits retain the origin forecast GP, including after changing criteria.
- Lab results distinguish historical forecasts excluded from evaluation from missing forecasts, label the latest six GPs and season summaries, and use descriptive detail disclosures. How it works separates the 15 frozen-v1 inputs from dashboard context; selected documents open directly, identifying current sources and the historical protocol.
- Programmatic language follows PT/EN; flag buttons expose accessible names and selection. A keyboard skip link reaches the content; language controls scroll with the header without obscuring data. The How it works photograph uses local viewport/DPR variants, preserving its original, framing and attribution.
- Focused checks and local six-screen browser evidence are recorded in `reports/ui_ux_pro_max_implementacao_20261101/`. The v1 model, probabilities and scientific artefacts are preserved; local implementation does not prove public deployment.
- Learning: navigation context, missing versus unevaluated states and chart alternatives require interaction checks; translating visible text alone does not declare programmatic language.

## 0.8.3 — 2026-11-01

- FIA/F1 cross-checks recover all 22 FP3 times and Lawson's profile without borrowing from another GP. One pre-FP3 row and 84 pre-qualifying pit rows are excluded from the projection; original bytes and indices remain audited. The validated scope contains 88 FP3 and 89 qualifying pit records.
- FIA decision 57 and final classification 59 confirm Lawson as DSQ. The UI leaves numeric position and voided times empty; the final table's zero is not interpreted as no physical laps. This descriptive change does not reissue the forecast.
- The FIA weather report also records the isolated zero. A specific documentary exclusion recalculates the track mean over 100 valid readings: 40.7 °C, 98.0% coverage, without interpolating the missing minute. Other sensors and active windows stay unchanged. Unreviewed readings remain withheld.
- Lawson's FP3 compound for laps 1–8 remains unavailable and is not inferred from the next stint. The official timing archive returned 401 and Formula1Dashboard lap requests returned empty data; this does not establish universal absence. Reviews also reach completed caches and future collection, with regressions for session identity, coverage gates and DSQ handling.
- A versioned complement revises only initial tyre age for 262 observed archive stints across 55 sessions/47 Grands Prix: 210 zero-to-positive changes, 36 positive-to-zero and 16 between positive values. All other fields stay unchanged.
- The reader applies the revision offline to a copy of the original projection, checking hashes, session, driver, compound, lap bounds and previous age. A missing, corrupt or incompatible required complement stops loading rather than silently presenting known old ages.
- Original snapshots and the base projection retain their bytes. The v1 model, its 15 inputs and recorded forecasts stay unchanged. Structurally revised or ambiguously linked cases remain outside this complement.
- Validation covers table and CSV values, PT/EN, desktop/mobile, integrity counterchecks and the isolated portable package. Evidence is kept in `reports/complemento_idade_pneus_20261101/`; this local delivery does not establish a new public deployment.
- Learning: upstream revisions require a traceable complement and verification of each physical stint; a published zero does not prove a fresh tyre set.

## 0.8.1 — 2026-11-01

- Lab results presents both model and qualifying counts as text for each GP, with dots as decorative visual support. Unevaluated races remain unscored and ties stay explicit.
- Drivers exposes the start count for each condition and other ranked drivers without relying on hover. Missing values remain distinct from zero and comparisons use real sample sizes.
- Text blue is separated from decorative blue to improve contrast in small rank labels and result cards. Mobile navigation labels are larger and wrap, with scroll clearance for focus above the fixed menu. Leader cards reflow with larger text; mobile navigation uses two rows.
- Focused validation covers PT/EN, counts, sample sizes and scientific states. Local acceptance checks contrast, reflow and keyboard use; receipts are kept in `reports/ui_ux_pro_max_20261101/implementacao/`. Public verification remains a separate step.
- Learning: legends and tooltips do not replace accessible counts and denominators. The skill guides review while implementation preserves visual identity, sources, the model and recorded probabilities.

- Published observed Mexico data: 22-driver result, 1360 lap records, tyres and stops, plus round-19 standings (24 drivers and 11 constructors). The observed podium stays separate from recorded probabilities; observing a result does not automatically admit it to model evaluation.
- Weather is summarised only during active racing: mean air temperature 24.2 °C. The track mean is withheld because an isolated 0 °C reading sits between 37.4 and 37.5 °C; the original record and raw diagnostic remain preserved. Twelve messages preceding the declared session start are audited outside the window; the suspension is excluded and actual transitions still come from race control. Original files and excluded indices remain preserved.
- Automation respects OpenF1's free-access window, waiting through the 30 minutes before/after sessions. The published extension of the race schedule was reviewed and recorded for collection without rewriting the prediction. FP3 and qualifying pit data remain partially withheld due to missing profiles 30/236; missing identities are never guessed.
- Corrected the diagnosis of “Bahrain Grand Prix in Malaysia”: Formula 1 confirms the event at Sepang. The UI shows Malaysia/Sepang and the host-country flag while preserving the original name and identity. Barcelona also gets an explicit label.
- Austin's cover gains a clickable credit and adjusted map spacing. The real 5822 × 3275 photograph remains preserved with CSS framing. Palette, fonts, approved cards and probabilities remain preserved. Visual acceptance now also accompanies automatic data publication.
- Learning: unusual names need primary-source verification; live-window unavailability, revised scheduling and stale session messages are different issues. Specific regressions cover these distinctions and prevent matching drivers by number alone.

## 0.7.3 — 2026-11-01

- Refined the Fan Journey composition: better-balanced photograph and podium proportions, weather before optional circuit details and a more compact before/after comparison without a repeated podium heading.
- Lab results adds flags, short GP labels and a visual legend alongside the explanation. Unevaluated rounds remain labelled and never become hits or zeros. How it works brings steps and document links closer without reducing readability.
- Mobile explanation text increased to 13 px. The heat shortcut uses a dry-track photograph; the wet scene stays associated with rain. Colours, fonts, original photographs and approved cards remain preserved.
- New CI visual acceptance measures all six screens in PT/EN on desktop/mobile: natural resolution for 2× display, overlaps, complete standings, targets of at least 44 px and podium/document visibility above fixed navigation. Screenshots and measurements accompany the CI artifact.
- Learning: the presence of headings and containers does not establish good composition. Acceptance now checks relationships between blocks and the space occupied by navigation; real photographs, data and Streamlit reservations remain distinct from the concept image. Model, probabilities and 614 scientific files preserved.

## 0.7.2 — 2026-11-01

- Fixed the cards' team identity: team colours now appear on the racing suit, helmet and ornaments inside each illustration. Norris and Piastri use McLaren papaya orange; the frame is no longer the only colour cue.
- The catalogue contains 126 team illustrations, with three poses for each of the 42 driver/team combinations known to the archive. Selection follows the GP row's team and compatible period; Hamilton/Mercedes and Hamilton/Ferrari have distinct artwork. Records without a recognised team do not receive a guessed team illustration.
- The 87 neutral originals remain archived and never silently substitute for missing team artwork. The three approved Mexico cards remain preserved. The catalogue includes a PT/EN gallery, separate coverage, integrity checks and an explicit export allowlist.
- The dialog remains optional without percentages; distinct poses, favourites, ties, probabilities and scientific artifacts are preserved.

## 0.7.1 — 2026-11-01

- Fixed an English translation bottleneck that passed entire HTML documents, including base64 images and fonts, through message translation rules. HTML is now parsed first; only text and accessibility labels are translated.
- URLs, CSS, identifiers, embedded media and code blocks remain preserved, as do exact catalogue hover templates. Regression checks cover HTML with large embedded media without reducing image resolution or changing data and probabilities.
- The delivery marker in the dependency file requests a fresh Community Cloud build while retaining the same package versions. Public confirmation of the fix requires its own verification.

## 0.7.0 — 2026-11-01

- All six screens refine composition C in revision C3: compact shared controls, a prominent circuit photograph, five distinct principal hero photographs and bottom navigation. Drivers combines Piastri at Silverstone in the backdrop with Ricciardo at Miami in close-up, identifying separate people and events, and shows four comparisons per leader with ties preserved. Podium chances strengthens the before/after timeline and emission-time context.
- The 28 original 93 × 93 portraits were replaced with larger natural-resolution sources, adding Ryo Hirakawa: 29 portraits, all above the minimum of 512 pixels on each axis; 28 are 1336 pixels wide. All 26 circuit photographs and five hero photographs are naturally at least 2488 pixels wide, with sources, rights, dimensions and hashes recorded. Presentation uses the original sources instead of treating enlarged thumbnails as higher-quality images.
- A catalog of 87 generated cards provides three distinct body poses for each of 29 drivers. Neutral artwork supports GP-specific team names and frame colours across historical periods. The three approved original cards remain byte-identical and restricted to matching teams.
- Cards remain in an optional dialog without percentages or P1/P2/P3 order. Deterministic selection preserves favorites and probabilities while assigning distinct poses to each trio, including additional tied favorites. [Gallery of all 87 cards](docs/galeria-cartas.html).
- Fixed a UI container shared across sessions, a shared URL scope being overwritten after a favorite update, and empty charts or counts formatted as percentages. Period, metric and minimum sample remain canonical; intentional empty selections stay editable. Regression coverage includes concurrent profiles and persisted favorites.
- Tests check natural resolution, provenance, identities, poses, hashes and the explicit package allowlist. Frozen v1, its 15 inputs, stored forecasts and 614 protected scientific files remain unchanged. These notes describe the local delivery; public deployment requires its own verification evidence.

## 0.6.3 — 2026-11-01

- Fictional driver banners replaced with identified high-resolution photographs of Lando Norris and Max Verstappen, with clickable image credits.
- Car banner uses a real photograph of Sergio Pérez at Miami 2022, with author, date and license. Former anonymous illustrations leave the distribution.
- Approved tarot art of real drivers is preserved. Layout, data and probabilities stay unchanged; a regression prevents fallback to a fictional driver.

## 0.6.2 — 2026-11-01

- Evaluation cards for 2024/2025 identify retrospective analysis; the recorded-forecast notice is restricted to prospective 2026 evaluation.
- An additional regression preserves this distinction across periods. No result or probability changed.

## 0.6.1 — 2026-11-01

- Raised bottom navigation to keep every button clear of the external Streamlit Community Cloud badge discovered during public verification.
- Main-heading acceptance uses its semantic level to avoid ambiguity with the championship table heading.

## 0.6.0 — 2026-11-01

- Rebuilt all six screens around the approved composition C: prominent imagery, a shared compact header, a calendar with flags and bottom navigation.
- Portrait podium for observed results, circuit facts, visual condition rankings, full championship standings, before/after timeline and visual evaluation cards.
- Three steps explain the Lab; sources and detailed documentation remain accessible. Approved tarot art stays in an optional dialog.
- Local portraits with provenance, PT/EN translations and mobile adaptations. Ties and missing data stay explicit; no forecast or recorded emission is recalculated.
- Visual and functional acceptance covers all six screens, shared links, languages, complete standings and optional cards.

## 0.5.2 — 2026-11-01

Fixes Mexico collection stopping when an OpenF1 driver profile is missing. The affected session remains partial, with a visible reason and its projections withheld; collection continues for other sessions. Duplicates, conflicting laps and mixed session identities remain rejected. Original captures, recorded forecasts and frozen v1 remain unchanged.

## 0.5.1 — 2026-11-01

Approved Mexico tarot artwork with team colours, distinct poses and likenesses refined from owner-provided references. The dialog remains optional; percentages appear only in the forecast table. Portraits are shown only when the record's team matches the artwork, preserving historical context. No probabilities, registered forecasts or model were changed.

## 0.5.0 — 2026-11-01

Fan Journey replaces the sidebar with a six-destination bottom navigation using native keyboard controls. Season/GP controls move to the top, with nearby calendar events and a prominent circuit image, outline and facts. Drivers has a leading discovery; championship standings remain complete in sequential tables. Optional cards open by button or direct forecast link, using actual recorded probabilities, period-specific teams and a helmet fallback. PT/EN and mobile are supported. Artwork is decorative and never changes inference, the model, forecasts or data.

## 0.4.7 — 2026-11-01

The Mexico forecast remains unchanged. The missing-data test now selects a genuinely unissued GP instead of assuming Mexico will always lack probabilities. This preserves the check against borrowing predictions between races.

## 0.4.6 — 2026-11-01

Mexico 2026 prospective forecast recorded on Nov 1 at 04:32 UTC, before the scheduled 20:00 UTC start. Canonical qualifying with 22 drivers, verified Q3 finish and frozen v1 model. Individual podium probabilities do not predict finishing order. Later race outcomes were excluded from inputs. Sources, manifest and probabilities preserved for audit.

## 0.4.5 — 2026-10-31

Automatic Mexico City Grand Prix data update through GitHub Actions. Sessions with received data: 2/5. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.

## 0.4.4 — 2026-10-30

Automatic Mexico City Grand Prix data update through GitHub Actions. Sessions with received data: 2/5. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.

## 0.4.3 — 2026-10-30

Automatic Mexico City Grand Prix data update through GitHub Actions. Sessions with received data: 1/5. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.

## 0.4.2 — 2026-10-30

Automatic Mexico City Grand Prix data update through GitHub Actions. Sessions with received data: 0/5. Sources, timestamps and original captures preserved. Forecasts remain separate from observations. Existing probabilities and frozen v1 remain unchanged.

## 0.4.1 — 2026-10-30

Automatic GitHub Actions collection and publication, scheduled every half-hour. The calendar identifies upcoming 2026 races, including Sprint sessions, without approximate identity matching. Persisted cache and cooldowns, original captures archived as release assets, and versions only for substantive changes. Publication requires tests, navigation checks and public deployment verification. Collection automation never trains or emits predictions; frozen v1 safeguards remain intact.

## 0.4.0 — 2026-10-30

In Summary, the circuit image and track outline now precede the podium, giving the venue visual priority.

Mexico preparation with five identified sessions, serial collection after observed finishes, auditable cache and persisted API cooldowns. Times, laps, tyres, pits, forecast separated from race sensors and round-specific official standings. Explicit Mexico OpenF1 qualifying admission; committed code and publication before lights out remain mandatory. The 2026 score includes only registered predictions and validated later outcomes. Qualifying and the race have not happened yet; this delivery contains no prospective Mexico forecast.

## 0.3.1 — 2026-10-30

Fix favourite-test synchronisation: acceptance now resolves the current iframe after reload and waits for the persisted value, rather than holding a Frame that Streamlit may detach. The issue appeared in the main-branch CI; the 0.3.0 release and public app had passed. Data, comparison rules and scientific model are unchanged. CI also regenerates the distribution and compares it with the published copy. Validation covers the full browser journey against the served package and package integrity.

## 0.3.0 — 2026-10-29

- Fan navigation: complete championship in its own screen, race results first and technical explanations in a second layer.
- Drivers: duels at shared races, a browser-local favourite, recent results, persistent filters and shareable SVG cards.
- Corrections: circular mean wind direction; individual reference uses the same races; overview weather describes the race when available.
- Reading and mobile: contrast, paragraph rhythm, visible tabs and smaller presentation images with originals preserved.
- Delivery: MIT for original code, actual package validation in CI and PT/EN documentation.
- Limits: historical associations do not isolate driver skill. 17 practice/qualifying tyre compounds remain unavailable. Model v1 and recorded predictions are preserved.

## 0.2.0 — 2026-10-29

### Drivers: comparing results with actual race conditions

New helmet menu, condition overview and individual profiles in Portuguese and English. Six highlights cover recorded rain, track temperatures, direction, corners and altitude. Filters select seasons, metric and minimum starts. Rankings cover the complete eligible cohort; the heatmap includes all drivers. Teammate comparisons and downloadable evidence link to individual GPs. Ties stay explicit; insufficient samples do not become zero performance.

The descriptive dataset contains 66 main races, 1,354 results and 1,340 starts. Race control defines actual racing intervals and excludes suspensions: eight races recorded rain. Open-Meteo supplies 70 hourly atmospheric samples within these intervals, labelled as grid reconstruction. All 66 edition-specific FIA maps were reviewed: Suzuka is a figure-eight layout; Spielberg and Marina Bay retain their year-specific lengths.

The [audit](reports/pilotos_condicoes_20261029/README.en.md) records 295 checks. Of 50 invalid stint bounds, 30 were reconstructed using observed laps; the rest have zero completed laps or DNS. Nine compounds were recovered. The 17 still unavailable belong to practice/qualifying and remain missing, outside these comparisons. Races received 11 observed strategy sequences and eight individual compound fills; the ninth recovered compound is already within one of those sequences.

Learning: session type alone does not separate Sprint from the main race; scheduled time does not define actual racing time; agreement between feeds does not imply independence. Australia/2026 lap selection uses driver, UTC and duration while preserving a numbering discrepancy between sources. Rates use starts as opportunities, including retirements and DSQ; non-starts are excluded. Comparisons show historical associations rather than isolated skill. All 614 protected files, model v1 and registered probabilities remain unchanged.

## 0.1.4 — 2026-10-29

### São Paulo and Madrid images

The Interlagos image was only 349 × 197 pixels. It is replaced with a 5000 × 3333 photograph of the Senna S during the 2022 São Paulo Grand Prix, showing Formula 1 cars and the track. Credit: Beto Issa/Formula 1 and Governo do Estado de São Paulo, CC BY 2.0.

In Madrid, a portrait photograph was cropped to show mostly sky. The new official photograph shows the main straight, pit lane and grandstands in September 2026. The interface frames its left side to focus on the circuit and keep the portrait subject outside the visible area. Credit: Comunidad de Madrid, CC BY-NC-SA 4.0; this file-specific noncommercial condition remains recorded in the catalog.

Review checks original resolution and the subject visible at actual card size on desktop and mobile. Original image bytes remain unedited; presentation cropping, sources, attribution and PT/EN alt text are documented. Maps, data and predictions are unchanged.

## 0.1.3 — 2026-10-29

### Miami photograph

Replaces a Porsche Sprint Challenge photograph, selected because it was taken at the same circuit, with a real photograph of Sergio Pérez driving the Red Bull RB18 Formula 1 car at the 2022 Miami Grand Prix. Public feedback exposed the selection error: the correct venue does not guarantee the correct racing category. Visual selection now checks the circuit, category and car identity.

Credit: Dcmaradiaga (David Castro), Wikimedia Commons, CC BY-SA 4.0. Original image preserved; PT/EN alt text, source and catalog hash updated. The photograph illustrates the venue and dates from 2022; it does not depict the selected season. Data and predictions remain unchanged.

## 0.1.2 — 2026-10-29

### Interface

Move BR/GB flags to the upper-right corner after public use revealed overlap with Streamlit/GitHub branding and controls in the footer. A reserved row below the native toolbar prevents covering search, preferences or the GP title on desktop and mobile. Language, GP, tab and filters remain retained.

Acceptance checks the upper position, side-by-side flags and no intersection with application controls. Data, model and probabilities are unchanged.

## 0.1.1 — 2026-10-29

### Publication and verification

GitHub and CI were up to date for 0.1.0, but a clean public session still received the previous interface. A normal rerun did not synchronise the code. The presentation dependency file received a delivery marker to request a fresh Community Cloud build, retaining exactly the same package versions. Public confirmation remains separate from push and CI.

Version-policy tests now use synthetic changelogs, independent of versions already present in actual history. No data, model, probability or scientific artefact changed.

Lesson: a release and passing tests do not prove the hosting service runs that code. [Documented Streamlit mechanism](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-streamlit).

## 0.1.0 — 2026-10-29

First version under the explicit product-versioning policy.

### Data and corrections

- Resolved 75 queue items: 71 documented qualifying conflicts, FIA Baku/Q supplement, two corrected quality states and identified archive origin. Six absences confirmed; 31 tyre limitations remain.
- History changed from the current race to up to five previous editions at the same circuit, including future GPs without their own archive.
- Profiles for 26 circuits with approximate altitude, lap records and season/reference-aware DRS context.

### Product and maintenance

- BR/GB controls with PT/EN navigation, tables, charts, messages and documents; language retained in links.
- Responsibility-based `pitwall/` package, compatible entry points and preserved frozen sources.
- Bilingual README, learning journal, architecture, contribution and version policy.
- Each subsequent delivered data update or improvement requires a version increment and a record of the problem, change, verification and lesson.

### Lessons and limitations

The History correction showed that possessing data does not guarantee answering the user's question. Stint review distinguished a quality warning from an actual gap. Identifying the archive source does not invent its original acquisition time. Translation changes presentation, not scientific evidence. A local delivery is considered public only after checking the served build.

## Before the version policy

Earlier milestones use actual commit references in the [learning journal](docs/en/LEARNING.md). Original dates and messages are preserved.
