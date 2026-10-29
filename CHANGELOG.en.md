# Pitwall Lab evolution

[Português](CHANGELOG.md) · English

Versions describe product deliveries. Scientific model v1 remains frozen. Earlier commits have not been assigned retrospective versions.

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
