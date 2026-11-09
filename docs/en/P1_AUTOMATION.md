# Automatic P1 prospective operation

Created by: MBPaschoal
Status: implemented; activation and live receipts tracked separately
Type: operational documentation

[Português](../AUTOMACAO_P1.md) · [General automation](AUTOMATION.md)

The new `prospective` job follows serial collection in the existing hosted workflow. It checks out updated trusted `main` and uses only the temporary Actions token with `contents: write`. No personal computer, PAT, additional key or new cron is required. The existing schedule requests runs every 30 minutes; GitHub can delay them.

Before qualifying, it records a waiting state without P1 API writes. After observed qualifying and a validated registered prospective v1, it runs the original frozen P1 companion, rechecks native evidence and the model/calendar/population bindings, then publishes one immutable public paired-probability asset in an event release such as `p1-2026-20-interlagos`. Existing assets are never replaced and this release does not become `Latest`. The original keyless verifier checks server digest, size and timestamps strictly before race minus 60 minutes.

Served v1 probabilities receive separate acceptance in eight fresh contexts: Chromium/WebKit, PT/EN and 390/1440 px. It checks version, native controls/language, selected season/GP, canonical favorites and all 22 chart values against the original pair. Screenshots, page errors and failed attempts remain preserved; mobile widths are emulated. Q is public in the pair asset, not a new dashboard model. Successful host evidence must itself be publicly preserved before actual race start. Later runs reuse the same pair and prior acceptance rather than fabricating a new observation.

After the race, it reads the result supplement already validated by the Drivers collection, without depending on a manual forecast-projection refresh. Exact event/session, driver/team identities, observed finish and later canonical/native acquisition timestamps are required. Separate hash-addressed assets preserve targets and descriptive Brier/log-loss GP scores. Unknown targets stay unknown, and known DNF/DNS/DSQ targets use the native reader. Later source revisions preserve previous receipts; no probabilities, eligibility or coefficients are revised.

The adapter pins the original public manifest and verifies all registered files. It is the operational integration anticipated by the [unchanged P1 protocol](https://github.com/mbpaschoal/pitwall-lab/blob/6206fd4c82012e60a0bcad3ebe935efc6406ffeb/reports/prospectivo_p1_20261105/protocol.en.md), with no statistical recipe, 20-GP window or decision-rule change. The admitted policy remains **2026/20/interlagos only**. New events/seasons require prior calendar, roster, source and policy review. Unresolved Camara IDs, source conflicts, changed start times, partial rosters or altered models block publication.

The original manual runbook is a snapshot from before integration; this document describes operation after activation in `main`, without rewriting that snapshot. Host receipts record the automation commit, verifier SHA-256 and presentation input hash.

Preparation/publication and host verification have separate durable attempt assets: at most four per phase, at least two hours apart. A browser case permits two attempts and the job has a 20-minute bound. Individual API operations have a 30-second timeout. Only 404 means an absent release. Responses 403/429/5xx fail visibly. Recovery downloads and validates existing public bytes against native evidence. Missing pairs at their deadline and missing host evidence at race start remain permanently excluded. The workflow warns and keeps the durable receipt. Operational failures still fail the job. Run evidence is retained for 90 days. Public assets outlive evictable caches.

Per-GP scores are descriptive. The complete 20-GP coverage ledger, prespecified block bootstrap and formal comparative conclusion still follow the protocol; a single-GP receipt does not replace that analysis or select a model. Tests, green CI and a pre-Q waiting run do not prove future acquisition/publication. Before Q, `waiting_for_observed_qualifying` is the correct result. Once merged into `main`, the existing scheduler runs routine operations while preserving explicit review gates.

[Adapter](../../pitwall/operations/prospective.py) · [Workflow](../../.github/workflows/coletar-dados.yml) · [Host verifier](../../tests/browser/verificar_p1.cjs) · [Counterexamples](../../tests/test_prospective_automation.py) · [GitHub release API](https://docs.github.com/en/rest/releases/releases)
