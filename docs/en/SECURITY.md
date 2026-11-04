# Pitwall Lab security

[Português](../SEGURANCA.md) · English

## Surface and limits

The public dashboard reads local artifacts. Browsing needs no secrets and does not trigger data acquisition, training or inference. Libraries, HTML components, hosting, accounts and automation can still be vulnerable. Product tests, hashes and scanners provide complementary evidence, not proof that vulnerabilities or incidents do not exist.

The exporter uses explicit file lists, rejects invalid paths and symlinks, and creates an inventory/manifest with SHA-256 hashes. The verifier checks the actual tree, hashes and scientific baseline. These controls help prevent accidental publication and divergence; someone with sufficient write access could change both files and manifest.

## Code and automation

- Actions are pinned to reviewed full commit SHAs. Checkout does not persist Git credentials.
- Tokens default to read access. Release, collection and maintenance jobs explicitly request necessary additional permissions. Collection still needs content writes and recovery dispatch: this residual privilege has not been eliminated.
- Collection accepts only the official repository's `main`. Workflow-triggered maintenance always checks out trusted `main`, never the triggering event's code. PR code does not receive these jobs' write tokens.
- Git authentication is configured through the CLI only during publication, without saving a token in the checkout. Publication remains atomic, without force pushes; recovery uses fresh source and preserved captures.
- Product CI calls the security workflow. Release requires product, browser and security checks. Daily audits can fail and need maintainer action.
- `scripts/security/check_workflows.py` and counterexamples reject mutable Action references, persisted credentials, unexpected permissions and untrusted code in privileged jobs.

## Dependencies and secrets

Presentation runs in a separate Python 3.12 environment. Release 0.8.30 updates Streamlit, Protobuf, PyArrow and Pillow to versions without the advisories identified by this delivery's audit. The frozen scientific requirements, scientific `.venv`, model and recorded forecasts are preserved.

`pip-audit --strict` resolves and audits direct/transitive presentation and scientific dependencies. Failed queries do not count as clean results; new findings fail checks. Dependabot proposes weekly presentation/Actions PRs without auto-merge. A proposal still needs a product version, changelog, regenerated package and passing checks. The scientific recipe is audited without automatic updates.

Gitleaks comes from a pinned official release with a verified checksum and scans history with redacted values. `.gitleaksignore` contains only five reviewed historical fingerprints: control identifiers in tests and artifact checksums. There are no directory-wide or rule-wide exclusions. Investigate new findings; revoke/rotate real exposed credentials first, then assess impact and historical cleanup. Never publish credentials or unredacted findings.

## Administrative settings and accounts

Secret scanning, push protection, Dependabot, CodeQL, private reporting and branch rules live in GitHub settings. Verify them through the API/UI: this document does not establish that they are active. Versioned policies in `scripts/security/` describe intended rules; the delivery receipt records API-confirmed state.

`gh-secure` is a configuration aid installed at a pinned revision. Inspect status and dry-run before making changes. Separate rulesets without bypasses prevent deletion/force pushes of `main` and changes/deletion of `v*` tags. GitHub rejected the native Actions bot as a PR-rule exception on this personal repository. To preserve atomic publication without an additional credential, platform-enforced PRs are not enabled on main. The maintainer uses PRs for code changes and workflows block releases without required validation. Automatic publication audits policy, dependencies, history and new staged changes before pushing; failure preserves captures. Enforcing PR-only main with a narrow bypass requires a separately authorized, installed GitHub App. `main` rules must accommodate automatic publication; do not blindly apply the generic one-approval policy. Never broaden credential permissions merely to obtain a green indicator.

The owner should maintain 2FA/passkeys, keep recovery codes outside the repository, and review GitHub/Streamlit sessions, apps, keys and access. Password, 2FA and passkey setup require the owner. Never record codes, tokens, cookies or callbacks. Remote Git, Dropbox and Actions caches do not replace an independent backup with a tested restore.

## Reporting and response

Use [private reporting](https://github.com/mbpaschoal/pitwall-lab/security/advisories/new), following [SECURITY.md](../../SECURITY.md). Suspected compromise requires preserving evidence without secrets, revoking affected credentials, stopping compromised automation if necessary, restoring a verified version and checking data/releases before resuming. Never rewrite forecasts or scientific evidence to hide divergence.
