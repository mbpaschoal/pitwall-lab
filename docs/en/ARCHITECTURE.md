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

Start from the relevant blueprint role contract. Prefer small functions, descriptive names, explicit dependencies and behavioural tests. Avoid copying implementations among package, root and distribution: the portable package is generated. Record a new version for each delivery and test the isolated package and affected language. Do not run unrestricted test discovery for a presentation change: it can execute scientific work.

## Release 0.3.0

`pitwall/dashboard/model_views.py` owns Lab evaluation; `pilot_views.py` composes exploration, profiles and duels. `driver_duel.py` calculates shared-start comparisons without UI dependencies. `search.py` searches local entities; `share_cards.py` exports SVG without external resources. Favourites use the local component in `frontend_assets/favorite/` and browser storage.

`distribuicao/pitwall-dashboard/` is generated from an allowlist and must not be edited directly. ZIP files are release assets rather than large duplicated Git binaries. CI validates the actual served tree. `validar_blueprint.py` belongs to the local vault and is not required by the public installation.
