# São Paulo automation and preparation — 3 November 2026

English · [Português](README.md)

Created by: MBPaschoal
Status: published v0.8.26; public loading limits recorded
Type: delivery evidence

Delivery 0.8.26: [automation inventory, controls and review responsibilities](../../docs/en/AUTOMATION.md). No future forecast has been emitted: São Paulo still requires an observed Q finish. Controlled-clock/transport tests exercise the gates without inventing a real emission.

The original official detailed 2026 F1 maps for Interlagos, Las Vegas, Lusail and Yas Marina are retained in `sources/`, with real capture UTCs, URLs, sizes and SHA-256. Direction and numbered turns were visually checked. Lengths were checked against the official race pages. These are not FIA homologation certificates or claims about future revisions. Open-Meteo point elevations use canonical calendar coordinates; they are neither circuit elevation ranges nor asphalt temperatures.

| Circuit | Turns | Direction | km | Point elevation |
|---|---:|---|---:|---:|
| Interlagos | 15 | Anticlockwise | 4.309 | 779 m |
| Las Vegas | 17 | Anticlockwise | 6.201 | 644 m |
| Lusail | 16 | Clockwise | 5.419 | 12 m |
| Yas Marina | 16 | Anticlockwise | 5.281 | 7 m |

Official pages: [São Paulo](https://www.formula1.com/en/racing/2026/brazil), [Las Vegas](https://www.formula1.com/en/racing/2026/las-vegas), [Qatar](https://www.formula1.com/en/racing/2026/qatar), [Abu Dhabi](https://www.formula1.com/en/racing/2026/united-arab-emirates). [Elevation API](https://open-meteo.com/en/docs/elevation-api).

Downloads use the documented `on_click="ignore"` mode. The browser test saves and checks file content/language, monitors `rerun_script` messages and verifies that the selected driver remains unchanged. Local success alone does not certify hosted downloads; public evidence is recorded separately. [Streamlit 1.50 documentation](https://docs.streamlit.io/1.50.0/develop/api-reference/widgets/st.download_button).

Calendar discovery now creates its directory before constructing the real capture client. A test uses that client with local transport and checks preservation of the first response without HTTP.

Work took place in an isolated checkout based on `a31b006`, preserving local drafts. Frozen v1 model, probabilities and existing emissions must stay byte-identical; the final receipt will record verification. No additional local automation was created: the old Mexico routine remains paused; the new operation is hosted on GitHub.


## Local validation before publication

144 package tests passed. Complete navigation and four PT/EN desktop/emulated-Android download cases passed: CSV/SVG saved with correct language, no download-triggered reruns and preserved filters. The extended suite passed 390 tests before the final additional cases; the final focused suite passed 47. A total of 344 original copies (106,220,808 bytes) were added without conflicts, making all 19 registered emissions valid. The frozen model loaded with its original hashes/fingerprint without inference. [Local receipt](local-validation.json), [offline readiness](offline-readiness.json), [preservation](protected-integrity.json), [original inventory](restoration-plan.json). CI, release and deployment remain pending at this stage.


## Publication and public-verification limits

Version **0.8.26 is published and Latest**, with successful main/tag CIs, 394 source tests, 144 package tests and 11 browser suites. Hosted collection completed healthily: 67 GPs, no pending entries, and no extra version for identical receipts. The uploaded ZIP is 665,855,915 bytes with SHA-256 `8a7d60cb69b17d0977d9650bc909a9b39323ab08de671b10939c43e148b35ceb`, matching the local package. A clean public session served build `f60379c599caaaddb05c4d66340713e0e0227914a874cd42049361abd8c03c0a`.

English SVG and CSV exports completed in emulated Android through a complete direct share link and after entering through How it works, with no download-triggered reruns. The direct case needed no reload; the second needed one. Desktop/PT also passed. Other public attempts failed during bootstrap, Streamlit-module loading or download completion. An initial desktop matrix incorrectly used touch; that harness failure is recorded separately. A fully passing public matrix and physical-device certification are not claimed. All attempts, including failures, remain available.

[Release](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.26) · [Final receipt](delivery-final.json) · [CI, release and ZIP](github-final.json) · [Final tests](source-tests-final.json) · [Direct English mobile](public-mobile-focused/direct.json) · [English mobile after How it works](public-mobile-focused/welcome.json).

## What this delivery taught us

The interface could run from its assets while the scientific producer still needed originals absent from the GitHub checkout. Extended validation exposed the gap before post-Q automation. Adding 344 identical copies completed all 19 registered emissions; CI now validates that registry and loads the model's original fingerprint without inference. Today's restoration does not establish retroactive pre-race publication evidence. Existing model and probabilities remain unchanged.

Preventing download-triggered reruns addressed one issue; public attempts also exposed a separate component-loading instability. Keeping both outcomes makes the delivery's actual limits reviewable.
