# Critical review delivery — 0.3.0

[Português](../REVISAO_030.md)

2026-10-29

All 45 approved items are mapped below. Final acceptance includes source tests, isolated package and real-browser journeys. Model v1, its 15 inputs and recorded predictions remain preserved.

| ID | Implementation |
|---|---|
| A01 | Links preserve filters, with a return to the driver overview. |
| A02 | Wind uses a circular mean; zero remains valid. |
| A03 | Individual reference uses races the driver started. |
| A04 | Counts are not compared with everyone else pooled; duels use pairs. |
| A05 | Overview uses race temperature and a neutral icon with its source. |
| A06 | Standings identify their reference round without claiming a future race happened. |
| A07 | Declared available fields are checked against values, including a null-wind counterexample. |
| A08 | CI verifies the served package manifest, hashes and tests. |
| A09 | The English report’s Portuguese link resolves inside the package. |
| B01 | Entry opens the latest observed 2026 race; the Austin cutoff is explicit. |
| B02 | Podium and results first; championship has its own screen. |
| B03 | Podium chances, How the Lab did and How it works. |
| B04 | Local search covers seasons, circuits, drivers and teams, including on Drivers. |
| B05 | Global filters are in the sidebar; GP is hidden when irrelevant. |
| B06 | Preferences use a settings icon. |
| B07 | Missing data, minimum samples, zero successes, future races and not applicable have distinct states. |
| B08 | Short questions and glossary; technical method in an expander. |
| C01 | Shared serif hierarchy and mobile scale. |
| C02 | Paragraphs limited to about 75 characters with reading spacing. |
| C03 | Darker secondary text fixes the identified contrast issue. |
| C04 | Podium precedes the image; smaller mobile title and circuit panel. |
| C05 | All six tabs fit at 390 px without horizontal clipping. |
| C06 | Complete standings; team shown alongside the name on mobile. |
| C07 | Map filter, gaps distinct from zero and percentage hover values. |
| C08 | Named flag controls, touch targets and locale-aware decimals. |
| D01 | Breadcrumb avoids repeating the GP; emission note stays in Podium chances. |
| D02 | Cards avoid repeated phrases; every tied driver has a link and sample. |
| D03 | Identical selections become one list and a short note. |
| D04 | Race weather first; weekend context collapsed. |
| D05 | Exports are secondary actions; sources and CSV remain available. |
| E01 | Profile offers all 16 selectable conditions. |
| E02 | Wins/podiums in races; thresholds and car/era context are explicit. |
| E03 | Computed highlights, previous winners and recent/circuit trajectories. |
| E04 | Duel uses shared starts; retirement and DSQ rules are explicit; teammate scope is all conditions. |
| E05 | Favourite persists in the browser and is highlighted in rankings. |
| E06 | Context-preserving URL and SVG card with period, sample and source. |
| E07 | Short glossary, circuit history and a team points chart. |
| F01 | Evaluation extracted into model_views; calculations, search, favourite and export separated. |
| F02 | One source, generated distribution; ZIP as a release asset. |
| F03 | Targeted tests, isolated package and real browser journey. |
| F04 | Public Python 3.12 installation; blueprint identified as a local tool. |
| F05 | PT/EN journeys checked, expanded catalogue and preserved scientific downloads. |
| F06 | README includes questions, PT/EN screenshots and an honest correction diary. |
| F07 | 26 photo derivatives: 27.0 MB to 6.5 MB; URI caching. Streamlit still builds tabs; no latency improvement is claimed. |
| F08 | MIT for original code; third-party terms remain separate. |

## Limits

Favourites depend on browser storage and do not sync across devices. Associations isolate neither skill nor causality. 17 practice/qualifying tyre compounds remain unavailable; they are neither imputed nor used in rankings. Contrast verification covers the reported issue, not full accessibility certification.

## Reproducible verification

`python -B verificar_pacote.py --pacote distribuicao/pitwall-dashboard`

`node tests/browser/aceite_exploracao.cjs http://127.0.0.1:8501 /tmp/pitwall-acceptance`

The second command needs Playwright 1.62.1 and Chromium in a separate development environment. CI runs the journey against the served distribution. These commands do not run scientific workflows.
