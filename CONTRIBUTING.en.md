# Contributing

[Português](CONTRIBUTING.md) · English

Start with [architecture](docs/en/ARCHITECTURE.md) and the [blueprint](docs/BLUEPRINT.md). Preserve existing changes, source data, IDs and temporal cutoff. The interface does not run collectors/models. Do not turn missingness into zero or use the current race's outcomes as prediction inputs.

Use a `codex/description` or task branch. Keep changes small; review the diff, including new files. Never add the entire vault with `git add .` or `git add -A`: select in-scope paths. Raw data, personal material, sessions, caches, environments and reference repositories do not belong in the public package.

Edit implementations in `pitwall/`; equivalent root files provide compatibility. Update PT/EN text together. Canonical IDs/scientific CSVs are not translated; definitions belong in the dictionary. Document source limits and prior behaviour without inventing causes.

For presentation changes, run focused modules, for example:

```bash
./.venv/bin/python -B -m unittest tests.test_i18n tests.test_dashboard_app tests.test_dashboard_acervo_app
./.venv/bin/python -B -m pitwall.publishing.releases check
```

Export to a new destination and verify using `verificar_pacote.py --pacote ABSOLUTE_PATH`. Check PT/EN desktop/mobile when UI changes. The complete scientific suite can fit models; do not use it as an automatic copy/CSS gate.

Each delivered data update/improvement requires a version and bilingual notes under the [policy](docs/en/VERSIONS.md). Use concrete commit subjects and PT/EN bodies covering problem, correction, verification and limits. Do not rewrite historical commits to standardise language or hide mistakes. Code licensing remains the author's separate decision; source conditions remain distinct.

Original code is available under the [MIT License](LICENSE). Third-party data and assets retain their own terms.
