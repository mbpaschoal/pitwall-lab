# Navigation and languages during loading failure

English · [Português](README.md)

Created by: MBPaschoal
Status: local interaction verified; complete branch CI pending
Type: implementation and deployment evidence

## Problem and change

The owner confirmed frozen menus and flags after reboot. [Earlier verification](../midia_publica_20261103/post-reboot-20261104T011855Z/README.en.md) preserves native 500 and dynamic-import failures. Navigation and flags now also offer ordinary links while their components remain unavailable, retaining destination, GP, language, applicable filters and keyboard access. Links disappear when native controls arrive, without duplicate navigation or stealing focus.

Approved colours, fonts and six icons remain. Final comparison found **zero difference** in header/flags/menu/cover positions and dimensions, for native/link modes at 390/1440 px. [Geometry and screenshots](geometry-proof/geometry.json). Initial comparisons incorrectly counted hidden button copies; retained final proof uses usable controls only.

## What the logs establish

The owner-provided excerpt shows Python 3.12.16, completed installation and main updates without a traceback in that excerpt; it does not prove no runtime errors. [Selected log facts](owner-log-extract.json). Ten compared runtime dependencies match passing 0.8.28 CI; Cloud adds rich for logging. Neither full host equality nor a dependency change by guesswork is claimed. [Comparison](dependency-comparison.json), [original CI line](ci-package-lines.json).

A fresh public opening completed Python with two selectors but incomplete navigation. Internal hosting routes returned 404, without a new 500 in that interval. These observations do not establish the earlier 500 cause. [Responses, bounded bodies and DOM](browser-transport.json). The official repository's legacy reference link did not open a comparable app; [inconclusive reference check](reference-app.json), not evidence of a platform-wide outage.

## Correction verification

- [Four blocked Radio/Button contexts](local-resilience-hydration/resilience.json): keyboard visits to all six destinations and language switching in each case, preserved GP/year, >=44 px targets and no overflow. The same receipt verifies late module arrival, native-control restoration and retained focus.
- [24 native-control checks](local-native-controls/controls.json), before the final hydration adjustment; final geometry and the following rehearsal record final controls separately.
- [Complete local publication rehearsal](local-publication-final/publication.json): four passing flows, decoded photos/hashes/build, documentation and actual language switching. The tested build is in its receipt; CI must independently rebuild the final recipe.
- Nine verifier counterexamples include hidden links, foreign destinations and duplicate locales. An initial fixture lacked UTF-8 charset and was corrected without adapting production to it.

Public verifier v2 records native/link/mixed modes, requires usable controls, clicks alternatives and actually switches language while comparing outer/iframe URLs. Unrecovered visible errors still fail acceptance. Two attempts per case, up to 120 seconds each and eight minutes overall. This neither certifies that every native resource will always work nor establishes hosting root cause.

## Local limit and delivery

First branch CI passed 405 source tests, 144 rebuilt-package tests, nine counterexamples, four blocked contexts and the complete new-verifier rehearsal. Core then stopped in an older test whose text selector matched both a visible native control and a hidden alternative link. Both affected tests now target the visible control without removing click/GP checks. Focus handling also keeps the replaced control outside assistive reading during handoff. [Preserved first CI failure](ci-first-attempt.json). The branch must pass again before main.

The broader local suite hit ENOSPC while copying temporary fixtures: 94 tests ran with 39 environment errors. The portable suite also stopped on disk capacity. Neither suite is claimed passing locally. [Limitation](local-limitations.json), [portable output](package-validation.txt). Earlier packages and original artifacts remain preserved. The local candidate uses copy-on-write storage and the unchanged canonical recipe without another local ZIP. [Materialization](candidate-materialization.json), [final recipe](candidate-final.json).

Complete CI now runs on `codex/**` before main, retaining all previous 12 acceptance suites and adding resilience. It must reconstruct the package with the canonical exporter, compare all 481 files and run source/portable/browser suites in Python 3.12 before publication. Release and fresh public acceptance require separate receipts. Data, frozen v1, probabilities and original sources remain unchanged.
