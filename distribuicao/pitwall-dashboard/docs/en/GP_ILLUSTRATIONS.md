# GP illustrations

`frontend_assets/destination_illustrations.json` records 26 editorial gouache scenes. Sepang is the approved visual reference. Each companion was generated separately using local references and reviewed as a complete image. These are artistic interpretations, not documentary photographs or technical maps. Credits disclose AI generation and destination references.

Original 1536 × 1024 PNGs live in `static/pitwall-art/gouache`. Immutable names include the circuit ID and SHA-256 prefix; the catalogue records the full hash, dimensions, PT/EN alternatives and reference URLs. The runtime verifies identity, path, bytes and dimensions. Missing or corrupt art produces an unavailable state rather than a substitute circuit.

Images preserve their 3:2 ratio with `object-fit: contain`, 12 px corners and a subtle shadow. Text, date and credits sit outside the painting. Mobile layouts use one column. Documented circuit photographs remain in their dedicated section.

Preserve generation evidence outside the runtime package, review each complete image, record its selection, then run `scripts/build_gouache_art.py --selection-dir PATH`. Incomplete mode is for local previews only and is rejected by publication checks. Distribution members are explicitly listed in `exportar_dashboard.py`.

Browser acceptance checks all 26 identities and complete image geometry on wide and narrow screens. Screenshots and visual review supplement metrics. CI, package integrity and public-host confirmation remain separate steps.
