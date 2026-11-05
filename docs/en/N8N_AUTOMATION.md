# Free supervision with n8n Community

Created by: MBPaschoal
Status: implemented; local execution and hosted publication are separate
Type: operational documentation

[Português](../AUTOMACAO_N8N.md) · [Hosted P1](P1_AUTOMATION.md)

The versioned [workflow](../../automation/n8n/supervisor.json) runs at minutes 17 and 47 in `America/Sao_Paulo`. Local n8n Community calls a Python bridge bound to `127.0.0.1:5681`. It provides state monitoring, review queues, deterministic PT/EN summaries, SHA-256-checked evidence copies in the existing Dropbox folder, and official-document change detection. It uses public keyless reads, without Codex credentials, paid LLM calls, extra collectors or external messages. Meaningful changes trigger native Mac notifications; reports remain available if the OS blocks notifications.

Workflow success does not prove observed qualifying, publication of probabilities or host acceptance. Only `2026/20/interlagos`, with the reviewed race start on 8 November at 17:00 UTC, is admitted. The supervisor checks immutable public P1 receipts using the original hash-pinned validators, exact identity, digest, size and server timestamps. Host acceptance remains separate. This audits saved receipts; it does not reconstruct native inputs or perform a new browser observation. GitHub writes, inference, fitting, model promotion and late predictions are never triggered.

After validated posterior receipts become available, fixed Brier/log loss metrics and denominators are checked and summarized. Unknown targets remain unknown. Before that, reports show waiting instead of invented scores. Per-GP summaries do not replace the formal 20-GP analysis.

## Evidence and source watching

`reports/supervisao_n8n/` contains `latest.pt.md`, `latest.en.md`, `queue.json`, content-addressed `objects/`, immutable `runs/` and `summaries/`. Mutable latest files are convenience pointers, not the original evidence. Public workflow metadata, descriptive JSONs and small P1 receipts are archived. Large release ZIPs are not automatically downloaded. Local copies do not prove Dropbox synchronization finished and are not independent backups.

The initial official-source watch covers the São Paulo Formula 1 schedule page and the FIA final Mexico classification PDF already used by the project. Checks occur at most once per 24 hours. Visible HTML text/document links and PDF bytes are compared; scripts alone do not trigger a review. Changed documents remain queued for human review without changing admitted data, calendars or forecasts.

Reads are serial and bounded: 30-second request timeout, 4 MiB response limit, inter-process lock, 20-minute cooldown and cached immutable assets. Rate limits and source failures remain indeterminate. Only the latest completed trusted-main workflow is inspected; an unsuccessful conclusion or stale collection is queued. Unavailable private log details are not inferred.

## Local installation

Runtime, database and internal keys stay outside Dropbox/Git under `~/Library/Application Support/Pitwall Lab/n8n/`. A selected deployment copy avoids dependency on temporary checkouts and Dropbox placeholders. n8n 2.46.6 and dependencies are locked. Existing Node 24/Python 3.12 are reused; the scientific environment is unchanged. Tokens are not inherited; telemetry, additional Community packages and shell execution are not enabled.

From a healthy checkout, use `python3 automation/n8n/local.py install`, then `deploy`, `agents` and `execute`. Installation is explicit; routine monitoring never installs or upgrades dependencies. Before updating, use `stop`, review and test changes, then `deploy` and `agents`. `export` exports only workflow JSON. CLI execution output is reduced to a safe receipt without internal resume tokens.

Two LaunchAgents named `com.mbpaschoal.pitwall.n8n.bridge` and `.engine` start on login and restart on failure. Logs are local under `logs/`; durable audit artifacts remain in Dropbox. The editor is at <http://localhost:5678>. Creating its local owner account, if requested, is free and independent of n8n Cloud; the CLI-published schedule does not depend on completing that UI step.

The Mac, user session and network must be available. Scheduling punctuality is not guaranteed; hosted P1 remains independent. No Cloud subscription, paid server, external messaging channel or Dropbox write credential is provisioned.

Validation: `python3 -B -m unittest tests.test_supervision tests.test_prospective_automation tests.test_releases -v`. Local installation, real CLI execution, observed scheduled execution and future post-GP scoring are separate evidence categories. Sources: [installation](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-npm.md), [CLI](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line.md), [Community](https://docs.n8n.io/deploy/host-n8n/community-edition-features.md).

## Dependency review before publication

The lockfile includes upstream overrides and subsequent advisory patches documented in [UPSTREAM.md](../../automation/n8n/UPSTREAM.md). The runtime loads exactly the three used nodes and caps incoming requests at 1 MiB. The first dependency audit identified critical findings not covered by functional tests; these were addressed before integration. CI now audits the lockfile and blocks critical or unreviewed high findings.

Zod 3.25.76 retains an open high advisory. The scoped decision records local mitigations and residual risk; it is not a Zod fix, a zero-vulnerability attestation or permission to expose this n8n profile publicly.

## Pending data releases after a healthy collection

The monitor reads main's version and retains data versions whose release/ZIP is not confirmed. A later successful no-change collection does not resolve an orphaned release. The check covers uploaded-asset metadata, digest, size and server timestamps only; ZIP-byte and served-host acceptance remain separate. At most five versions are checked per cycle and remaining pending entries are retained.
