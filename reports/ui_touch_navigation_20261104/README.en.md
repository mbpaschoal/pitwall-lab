# Language controls and mobile navigation — 0.8.31

[Português](README.md)

Created by: MBPaschoal

Status: local validation complete; CI and public deployment pending

Type: delivery evidence

The preceding public audit recommended larger flag targets and an unambiguous selection marker in the two-row mobile menu. This delivery retains the Fan journey: the same colours, fonts, photographs and icons. Buttons now measure 44 × 50 CSS px, retaining small flag symbols and an 8 px cell gap. Menu labels are centred with their icons; on mobile, an underline inside the selected cell replaces the top border. Desktop retains its previous marker. Fallback links receive the same mobile indication.

## Local evidence

- 42 focused tests; 144 portable tests across 17 modules: passed.
- Chromium: 24/24 scenarios. WebKit: 24/24. Each engine covers six pages × PT/EN × 390/1440 px, two language changes per scenario, edge taps/clicks, 44 × 50 px targets and marker placement. [Chromium](local-chromium-final/controls.json), [WebKit](local-webkit-final/controls.json).
- Resilience: four contexts, six keyboard destinations in each, language switching and delayed native-control recovery with focus preserved: passed. [Evidence](local-resilience-final/resilience.json).
- Version, 18 document pairs and workflow trust boundaries: passed. Security dependencies from 0.8.30 retained.
- Canonical package: 481 ZIP members verified byte for byte. [Build, digest and size](package-final.json). The served tree was synchronised only with files changed by the exporter.
- [Protected-file verification](preservation.json): comparison against the source commit. No collection, training or recorded prediction executed.

## Retained failures and learning

The initial mobile test found that a tap very close to one flag's edge activated its neighbour. Increasing width alone was insufficient; the same failure persisted with `touch-action: manipulation` and an 8 px gap. The probe compared larger gaps and targeting the whole button; the compact solution applies `pointer-events: none` to button descendants while keeping the button interactive and its accessible name intact. Both engines subsequently passed the original sequence of edge taps. Initial evidence and probes remain in this folder. This records observed behaviour without asserting an unproven hosting cause.

The first local package synchronisation allowlist omitted the two navigation documents and correctly stopped before copying anything. It was corrected to the eight expected canonical files; no exporter protection was removed.

Mobile browsers are simulated; no physical-device test or WCAG certification occurred. Local tests, CI, release and public hosting are separate evidence layers. Local acceptance does not demonstrate continuous Streamlit availability.

## Publication

Pending CI and confirmation of the version/build actually served.
