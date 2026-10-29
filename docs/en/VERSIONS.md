# Product version policy

[Português](../VERSOES.md) · English

`VERSION` is Pitwall Lab's product-version source. Model v1, research v2, snapshots and presentation builds have separate identifiers. The first formal version is **0.1.0**; earlier commits remain actual historical milestones without invented versions.

| Delivered change | Increment |
|---|---|
| New/corrected data, copy or compatible bug fix | PATCH: `0.1.0 → 0.1.1` |
| Compatible new functionality | MINOR: `0.1.0 → 0.2.0` |
| Breaking public contract or incompatible format | MAJOR: `0.1.0 → 1.0.0` |

During 0.x, incompatible changes still require explicit documentation/review; do not hide them in a patch. Several changes in one delivery can share a version; each subsequent delivery needs a new one. Updating data does not mean retraining. Do not schedule collection or automatically create empty releases.

Each delivery requires:

1. Update `VERSION`, `CHANGELOG.md` and `CHANGELOG.en.md`.
2. Explain prior problem, delivered behaviour, verification and lesson/limitation in both languages.
3. Verify frozen evidence, translation and relevant package.
4. Create clear commits with PT/EN bodies, preserving previous history.
5. Tag the actual delivery commit as `vX.Y.Z`. Release notes come from the corresponding changelog sections, without invented results.
6. Check the served version/build before recording public deployment. A tag does not prove deployment.

`python -m pitwall.publishing.releases check` validates version, notes and required language pairs. `notes --language pt|en` prints current notes. `check --base REF` requires a version increment when publishable code/data change relative to that reference. Documentation-only corrections may accompany a version; product/data changes cannot omit an increment.
