# Code organisation

[Português](../ARQUITETURA.md) · English

The [blueprint](../BLUEPRINT.md) defines responsibilities. Implementation uses an importable Python package without additional installation. `app.py` remains Streamlit's entry point; small root modules forward existing commands.

| Area | Implementation | Responsibility |
|---|---|---|
| Dashboard | `pitwall/dashboard/` | Composition, navigation and archive views. |
| Data | `pitwall/data/` | Readers, validation, offline projection, serial acquisition and adjudication. |
| Languages | `pitwall/i18n/` | Offline PT/EN catalogue and presentation-only adaptation. |
| Research | `pitwall/research/` | Isolated retrospective v2 research without model promotion. |
| Operations | `operacao2026/` | Snapshots, cutoff, GP state and recorded predictions. |
| Publishing | `pitwall/publishing/`, `publicacao/`, `exportar_dashboard.py` | Allowlisted documents, templates and portable export. |
| Review | `tests/`, `validar_blueprint.py`, `verificar_pacote.py` | Contracts, regressions, integrity and browser acceptance. |
| Scientific evidence | `data/`, `models/`, `reports/`, original v1 producers | Frozen scripts/artefacts retained at their original paths. |

## Flow and boundaries

Acquisition is explicit and serial. Offline preparation produces assets. Readers validate schemas/identities. The interface displays local copies without collecting, training or inferring during navigation. The exporter uses an allowlist and distinguishes scientific baseline from presentation build.

Old root module names are compatibility entry points, not duplicate implementations. Make new changes in the package. Compatibility retains imports used by tests and existing commands. Frozen v1 scripts were not moved simply to make folders uniform: their paths and hashes are evidence.

## Translation

`pitwall/i18n/en.json` holds visible text. Portuguese is default. Language is session-specific and persists as `lang=pt|en` in links. Canonical widget values, IDs, paths and URLs are not translated. `streamlit.py` adapts display arguments and copies of tables/charts only; Streamlit is not globally monkey-patched.

English documents live in `docs/en/` and use an explicit allowlist. Scientific downloads retain original bytes/identifiers with an English explanation. Descriptive-table downloads follow the selected language. Translation never changes source data or historical-availability evidence.

## Making changes

`fan_views.GP_CHAPTERS` retains the order, canonical IDs and labels of the six GP chapters. Links and native tabs use this definition; translation happens in presentation. Local accessibility and motion bridges use `st.iframe` inside hidden containers, with a valid minimum height of 1 px and `tab_index=-1`; Plotly charts use `width="stretch"`, as supported by the pinned Streamlit.

The offline producer `pitwall/data/dashboard_projection.py` organises archive projection into domain functions. `preparar()` checks sources, resolves identities, coordinates sessions/laps/weather/tyres/standings, applies history and supplements and validates writing. The UI continues to consume the resulting JSON; this producer is not part of the portable runtime. Stage order is part of the preserved behaviour.

In Pilots, `pilot_views._restore_navigation_state` applies saved state and deep-link parameters before visual composition. An already processed link does not reset widgets again; shared criteria retain their state across component reruns. `PILOT_QUERY_KEYS` defines the same parameter order for reading and sharing the selection.

Start from the relevant blueprint role contract. Prefer small functions, descriptive names, explicit dependencies and behavioural tests. Avoid copying implementations among package, root and distribution: the portable package is generated. Record a new version for each delivery and test the isolated package and affected language. Do not run unrestricted test discovery for a presentation change: it can execute scientific work.

## Release 0.3.0

`pitwall/dashboard/model_views.py` owns Lab evaluation; `pilot_views.py` composes exploration, profiles and duels. `driver_duel.py` calculates shared-start comparisons without UI dependencies. `search.py` searches local entities; `share_cards.py` exports SVG without external resources. Favourites use the local component in `frontend_assets/favorite/` and browser storage.

`distribuicao/pitwall-dashboard/` is generated from an allowlist and must not be edited directly. ZIP files are release assets rather than large duplicated Git binaries. CI validates the actual served tree. `validar_blueprint.py` belongs to the local vault and is not required by the public installation.


Drivers retains the original baseline and incorporates later GPs through a supplement validated by `pitwall/data/driver_updates.py`. The descriptive producer `operacao2026/driver_archive.py` runs within scheduled collection and publishes through the atomic allowlist. Pending prerequisites retain validated data and trigger monitoring. [Contract and limits](DRIVER_UPDATES.md).

## Boundaries checked in review 0.12.6

`pitwall/data/standings_state.py` resolves standings publication: selected event, snapshot cutoff and refresh status are separate facts. Failed refresh retains a valid same-event snapshot with a notice and provenance; a different event or incomplete table cannot supply points. Views handle an unavailable operational reader without discarding already validated data.

JSON readers validate the root before accessing fields and expose domain errors to callers. Search reuses the editorial reader. Missing optional sources do not become provenance paths. Capture cooldown is persisted and checked before any new request. Image writes are exclusive and byte-idempotent; divergent existing files are preserved.

In isolated research, timestamps require explicit timezones, existing destinations are refused and empty tables retain their schema. Folds without known targets have insufficient coverage rather than artificial zero scores; duplicate identities are rejected before filtering available predictions. Synthetic tests check these contracts without promoting research into v1.

For the next review, trace an input-to-output flow, name a concrete failure, demonstrate it in a test and change the smallest responsible unit. Reading coverage and test execution are separate records. Syntax inspection, local tests, CI, packaging and public-browser acceptance answer different questions. Compatibility modules and generated distribution files must not be removed merely because they look duplicated.
