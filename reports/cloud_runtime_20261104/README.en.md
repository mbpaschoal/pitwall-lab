# Navigation and languages during loading failure

English · [Português](README.md)

Created by: MBPaschoal
Status: v0.8.29 published; public reliability not accepted
Type: implementation and deployment evidence

## Result

The correction is on main at `8235954` and in [release 0.8.29](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.29). Complete branch, main and tag CI passed. GitHub rebuilt the release ZIP with the canonical exporter: **481 members individually verified**, 665,858,928 bytes and SHA-256 `5b792ecc42e991e3af99b70eb653707531669f8dbf7443e7b2c8f4369b765538`. Published API size/digest match the job receipt. [CI and release](published-ci-release.json).

Live build `03691f8190da92ec913a1868175ebf0e236b74f7106177010c7eed0f542dcfab` was observed with real decoded photos, controls and language switching. **Public reliability remains rejected**: complete acceptance passed only one of four contexts; failed attempts remain preserved. [Public acceptance](public-029/publication.json). Additional six-page and hosting-layer diagnostics have separate results and do not replace this acceptance.

## Problem and change

The owner confirmed frozen menus and flags after reboot. [Earlier verification](../midia_publica_20261103/post-reboot-20261104T011855Z/README.en.md) preserves native 500 and dynamic-import failures. Navigation and flags now offer ordinary links while their components remain unavailable, retaining destination, GP, language, applicable filters and keyboard access. Links disappear when native controls arrive, without duplicate navigation or stealing focus. This alternative requires the app HTML to have loaded; it cannot resolve the earlier empty hosting loader.

Approved colours, fonts and six icons remain. Final comparison found **zero difference** in header/flags/menu/cover positions and dimensions, for native/link modes at 390/1440 px. [Geometry and screenshots](geometry-proof/geometry.json). Initial comparisons incorrectly counted hidden button copies; retained final proof uses usable controls only.

## What the logs establish

The owner-provided excerpt shows Python 3.12.16, completed installation and main updates without a traceback in that excerpt; it does not prove no runtime errors. [Selected log facts](owner-log-extract.json). Ten compared runtime dependencies match passing 0.8.28 CI; Cloud adds rich for logging. Neither full host equality nor a dependency change by guesswork is claimed. [Comparison](dependency-comparison.json), [original CI line](ci-package-lines.json).

A fresh public opening before the correction completed Python with two selectors but incomplete navigation. Internal hosting routes returned 404, without a new 500 in that interval. These observations do not establish the earlier 500 cause. [Responses, bounded bodies and DOM](browser-transport.json). The official repository's legacy reference link did not open a comparable app; [inconclusive reference check](reference-app.json), not evidence of a platform-wide outage.

## Correction verification

- [Complete branch CI](branch-ci.json): 405 source tests, 144 rebuilt-package tests, nine counterexamples and 13 browser suites, including Chromium/WebKit PT/EN and mobile. Main and tag repeated verification successfully.
- [Four blocked Radio/Button contexts](local-resilience-hydration/resilience.json): keyboard visits to all six destinations and language switching, preserved GP/year, >=44 px targets and no overflow. The same receipt verifies late module arrival, native-control restoration and retained focus.
- [24 native-control checks](local-native-controls/controls.json), before the final hydration adjustment; final geometry and CI record final controls separately.
- [Complete local publication rehearsal](local-publication-final/publication.json): four passing flows, decoded photos/hashes/build, documentation and actual language switching. The receipt identifies its phase-specific build; CI independently rebuilt and tested the final build.
- Nine verifier counterexamples include hidden links, foreign destinations and duplicate locales. An initial fixture lacked UTF-8 charset and was corrected without adapting production to it.

Public verifier v2 records native/link/mixed modes, requires usable controls, clicks alternatives and actually switches language while comparing outer/iframe URLs. Unrecovered visible errors still fail acceptance. Two attempts per case, up to 120 seconds each and eight minutes overall. This neither certifies every native resource will always work nor establishes hosting root cause.

## Preserved failures and integrity

First branch CI passed the new checks but core later stopped in an older test whose text selector matched both a visible native control and a hidden alternative link. Both affected tests now target the visible control without removing click/GP checks. Focus handling also keeps the replaced control outside assistive reading during handoff. [Preserved first CI failure](ci-first-attempt.json). The branch passed again before publication to main.

The broader local suite hit ENOSPC while copying temporary fixtures: 94 tests ran with 39 environment errors. The portable suite also stopped on disk capacity. Neither local suite is claimed passing; full validation ran on GitHub. [Limitation](local-limitations.json), [portable output](package-validation.txt). Earlier packages and original artifacts remain preserved. Disk recovery replaced only identical temporary copies with APFS clones, preserving bytes, permissions and timestamps. [Receipt](storage-recovery.json). The local candidate used the unchanged canonical recipe without another local ZIP. [Materialization](candidate-materialization.json), [final recipe](candidate-final.json).

Complete CI now runs on `codex/**` before main, retaining all previous 12 acceptance suites and adding resilience. Per-member ZIP verification passed for the actual release, separately from the [read-only previous-ZIP rehearsal](zip-verifier-rehearsal.json). **681 protected files and all six icons remain identical**. [Integrity](protected-integrity.json). Data, frozen v1, probabilities and original sources remain unchanged.

## Next hosting comparison

If public loading remains incomplete, the proposed comparison is a second instance using the same approved code and Python 3.12 without replacing the current app. Creation requires the owner's authenticated dashboard, unavailable in this session. [Concrete PT/EN configuration](HOSTING-COMPARISON.md). This is a diagnostic proposal, not an executed migration or an established cause.

## Six-page public verification

The additional run ended with nine passing checks, ten failed attempts and five destinations not executed because the eight-minute global deadline expired. This is neither 24 passes nor 24 observed interface failures. Passing transitions used native clicks and preserved GP/year/language; several direct openings stopped at the loader or incomplete controls. [Full receipt and screenshots](public-navigation-029/navigation.json). One additional run per layer compares normal opening, the observed iframe and the [documented embed mode](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app/embed-your-app); this diagnoses loading without assuming functional acceptance or root cause. [Result](hosting-layers-029/hosting.json).

Final comparison result: normal opening, access to the observed iframe and embed mode all ended with incomplete loading. Iframe access completed Python with six alternative links present and no decoded photo pixels; normal opening did not mount the product during the observation window. This neither establishes one root cause nor demonstrates a Streamlit-wide outage. No further dependency changes, security disabling or reboot were performed.
