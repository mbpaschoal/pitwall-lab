# Language controls and mobile navigation — 0.8.31

[Português](README.md)

Created by: MBPaschoal

Status: 0.8.31 published; CI and public acceptance passed

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

The second CI passed all four driver-update cases and navigation, but stopped on a tyre-CSV download timeout in English on desktop. The process exited without a failure screenshot: the event promise was created before awaiting the click and could reject unhandled while that action still waited. The test now centres the button, verifies actionability without forcing and handles click/download with `Promise.all`; failures are explicit in its receipt. The specific cause blocking that click remains unproven. [Second CI evidence](ci-second/analysis.json).

The first branch CI failed in `aceite_pilotos_atualizacao.cjs`, reporting “Stale Max starts” in the English profile. The original routine passed all four local contexts; the remote failure did not record the value read. Reading during a DOM update remains an inference. Acceptance now waits for the exact source start count without admitting any other value, and records metrics/identity on failure. Partial receipts now distinguish an in-progress run, failure and success of all four cases. [Initial failure and evidence](ci-first/analysis.json). The adjusted routine passed all four local contexts. A [counterexample](starts-counterexample.json) required 68 starts when both source and page contain 67: the incorrect value was rejected and a failed receipt was recorded.

The initial mobile test found that a tap very close to one flag's edge activated its neighbour. Increasing width alone was insufficient; the same failure persisted with `touch-action: manipulation` and an 8 px gap. The probe compared larger gaps and targeting the whole button; the compact solution applies `pointer-events: none` to button descendants while keeping the button interactive and its accessible name intact. Both engines subsequently passed the original sequence of edge taps. Initial evidence and probes remain in this folder. This records observed behaviour without asserting an unproven hosting cause.

The first local package synchronisation allowlist omitted the two navigation documents and correctly stopped before copying anything. It was corrected to the eight expected canonical files; no exporter protection was removed.

Mobile browsers are simulated; no physical-device test or WCAG certification occurred. Local tests, CI, release and public hosting are separate evidence layers. Local acceptance does not demonstrate continuous Streamlit availability.

## Publication and acceptance complete

[Release 0.8.31](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.31) is published and [Pitwall Lab](https://pitwall-lab.streamlit.app/) served build `06f98e667d64f02b64bc56c587aeaf7c31c19606e1c7431a92574c74e92f3a24` in all four deployment contexts. [Structured summary](summary.json).

| Layer | Result and evidence |
|---|---|
| Branch CI | 405 source tests, 144 portable tests, ten verifier counterexamples and 13 browser suites: passed. [Run](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41837228872), [receipt](ci-branch-final.json). |
| Main and tag CI | Both passed at commit `80cef1760a12ad2e46e5083b482b5b9c79e9ae8a`. [Main](ci-main-final.json), [tag/release](ci-tag-final.json). |
| Public version, build and photographs | Four PT/EN × 390/1440 px contexts, decoded photographs and matching hashes, all on the first attempt. [Receipt](publication-final/publication.json). |
| Public pages and language flags | 24/24 scenarios in [Chromium](public-controls-chromium/controls.json) and 24/24 in [WebKit](public-controls-webkit/controls.json). Six pages; 96 edge language switches; measured minimum targets of 44 × 50 px; mobile marker inside its own cell. |
| Public menus | Eight flows with six destinations each: 48 actual clicks/taps, retaining GP, season and outer-address synchronisation. [Chromium](public-menu-chromium/interactions.json), [WebKit](public-menu-webkit/interactions.json). |
| Official ZIP | 481 members verified in CI; 665,860,833 bytes. The GitHub attachment digest matches the CI ZIP and local package. [CI proof](release-proof.json), [release metadata](release.json). |

All 60 public scenarios completed without case retries in this version. Mobile devices were simulated. Results describe the test window and do not establish continuous hosting availability. Both initial CI failures remain documented above; a CSS preview on 0.8.30 is explicitly temporary in `live-css-preview.json` and was not counted as publication.

[Public mobile PT capture](publication-final/390-pt-0-Metodologia.jpg) · [public desktop EN capture](publication-final/1440-en-0-Corridas.jpg). The [rejected-wait counterexample](download-counterexample.json) confirmed a failed receipt and screenshot; its initial observation limit remains explicit.
