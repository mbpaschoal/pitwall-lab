# Public image and deployment verification

English · [Português](README.md)

Created by: MBPaschoal
Status: v0.8.28 released; public acceptance still failed after owner-reported reboot
Type: delivery evidence

## Verification after the reported reboot

The owner confirmed the reboot. Fresh public verification on 4 November UTC still failed all four contexts. Diagnosis captured 500/HTML responses for native Streamlit JavaScript/font resources and dynamic-import errors. Two files later returned normally and matched the local installation; the HTTP/1 comparison also failed. Root cause remains open without administrative logs. No code/data changed during this verification. [Subsequent results, screenshots and limits](post-reboot-20261104T011855Z/README.en.md). The records below describe the release and pre-reboot situation.

The owner also confirmed that flags/navigation fail in normal use. Authenticated hosting error logs were requested. Another probe captured no new errors without executing full acceptance or proving recovery. [Confirmation and next diagnostic PT/EN](post-reboot-20261104T011855Z/FOLLOWUP.md).

The diagnostic rechecked the How it works cover. The browser decoded the app-served WebP with the catalogued MIME, dimensions and SHA. Relative `app/static/` works inside the Streamlit iframe; the photograph and layout did not need replacement. [Official documentation](https://docs.streamlit.io/develop/concepts/configuration/serving-static-files) describes this local-file delivery. [Observed image](before-r2/observed.png), [decoded pixels and responses](before-r2/diagnostic.json), [HTTP checks](static-http.json).

Initial attempts also encountered 404/HTML responses for native Streamlit JS/CSS and incomplete bootstrap. HTTP 200 for a photograph or a visible version cannot certify a fully loaded page. A single root cause for these intermittent failures has not been established. Earlier pending-image/icon captures remain preserved rather than being called visual acceptance.

## Implemented improvement

The [deployment verifier](../../tests/browser/verificar_publicacao.cjs) checks four fresh contexts: PT/EN at 390/1440 px, visiting Races and How it works in each. It requires:

- the publication event in both the package calendar **and collected state**, without relabelling a future event as received data;
- version, language, native controls, icon font and absence of app exceptions/overflow;
- decoded photographs, positive dimensions, admitted origin, image MIME and the documented original/variant SHA;
- exact package build, opened through the documentation control.

Each case gets one loading retry within a six-minute overall deadline. Origin/hash/identity mismatches are not retried as instability. JSON is written atomically with the verifier SHA; attempts and screenshots remain preserved. Hosted collection keeps evidence for 30 days even on failure. This verifies a data publication; it is not continuous uptime monitoring.

## Counterexamples and validation

[Seven counterexamples](../../tests/browser/test_verificar_publicacao.cjs) combine five real-browser cases and two metadata/preflight checks. They cover approved pixels, wrong hash, broken image, language/readiness, foreign origin and mismatched event/version. They enter core CI alongside a complete local verifier rehearsal: 12 acceptance checks, retaining the previous 11. The complete verifier passed all four local flows, both languages and widths, using real images and build from the previous package. [Local cases](local-027-r2/publication.json), [401 Python tests](source-tests.json).

The first new-readiness rehearsal exposed incorrect Playwright argument handling in the test itself. It was corrected and received a specific counterexample. An exploratory run used future round 20; the contract now rejects an event without matching collected state. These attempts remain preserved; publication validation uses collected round 19. São Paulo's calendar and future expectations are unchanged.

Pre-delivery public attempts remain in [public-027](public-027/publication.json) and [public-027-r2](public-027-r2/publication.json). Real bootstrap/resource failures do not become acceptance through screenshots or unbounded retries. The new release requires its own public receipt.

## Rafael Câmara

A new serial identity lookup at 23:21 UTC on 3 November returned 35 Jolpica drivers and 22 OpenF1 drivers, still without Câmara. [URLs, UTCs, hashes and original responses](sources/20261103T232125Z/receipts.json). These are neither Q results nor model inputs. His three approved illustrations remain preserved and await a verified canonical identity before catalogue binding. No ID/number or driver history was manufactured.

## What this delivery taught us

Verification needs to show whether fans can use served content. A version label identifies the responding delivery; decoded photographs, ready controls and matching bytes add evidence of what actually arrived. A test failure and a hosting failure must remain distinguishable.

## Final local package

Distribution 0.8.28 passed 144 tests and all four complete verifier flows without retries. Counterexamples total seven: the initial six plus failure-receipt retention when preflight rejects a package before network access. [Package and ZIP](package-validation.json), [final local receipt](local-028/publication.json), [seven counterexamples](browser-counterexamples-final.txt). All 533 checked scientific files and the original photograph remain unchanged. [Integrity](protected-integrity.json).

## Release and public-verification limitation

**0.8.28 is published and Latest**, with passing main/tag CIs. The uploaded ZIP has 665,856,793 bytes and SHA `b0f9061dbb2a8f0f2aa6fe7d4044cb06b548b7e1beedaaeecfd3149cc633e2d9`, matching the local package. All 481 files matched the canonical recipe. [Release](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.28), [final receipt](delivery-final.json), [recipe comparison](source-package-comparison.json), [hosted validation](ci-validation.json).

Full public acceptance **did not pass**: all four contexts from this machine and four from an independent GitHub runner failed to finish bootstrap/native controls within bounded attempts. The independent screenshot shows the loader rather than a complete page. The same code passed four complete local flows and 12 CI acceptance checks. This separates tested code/package from public operation; it does not establish the failure's root cause.

[Local public check](public-028/publication.json), [independent diagnosis](hosted-public-028/publication.json), [artifact chain of custody](hosted-artifact.json), [independent run](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41745235515). The diagnostic remained isolated on `codex/public-probe-network-20261104`, without changing main or the product; its evidence is preserved here beyond temporary artifact retention.

At initial delivery, the owner was asked to use **Manage app → Reboot app**, because the available public session has no authenticated administrative control. No confirmation or subsequent test was available then. The later confirmation and verification are recorded above, preserving these earlier failures. Câmara's canonical identity remains a separate pending item; his three illustrations are already approved.
