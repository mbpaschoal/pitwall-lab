# Stroll identity — Spain 2025

Created by: MBPaschoal  
Status: corrected locally; portable package verified; not published  
Type: implementation report  
Updated: 2026-11-04

[Português](README.md)

**Resolved in isolated local version 0.10.1:** car 18 in Spain 2025 FP1/FP2/FP3/qualifying receives canonical ID `stroll`. Qualifying remains P14, Q1 1:13.038, Q2 1:13.058. No race entrant or sporting value was added or changed.

The canonical mapping previously used race results alone, excluding a driver who took part in qualifying but was absent from that race classification. Event identity, car number, four OpenF1 registries (meeting 1262, sessions 9964–9967), Jolpica ID and F1DB birth date `1998-10-29` were reconciled without fuzzy name joins. [Identity evidence](identity-evidence.json), [native captures](openf1-capture.json), [approved revision](approved-bundle.json).

Future descriptive qualifying exports retain car numbers. Normalization accepts qualifying-only participants and rejects conflicting driver/team associations. Old number-less CSVs remain unmapped. The existing immutable archive receives a hash-pinned in-memory revision after the tyre/source supplements; exact event, session, car and prior-row hash preconditions restrict the change to four identity leaves. Missing or corrupt revisions fail closed for the known base.

The updated F1DB comparison has **2,967 matching phase times**, 1,032 jointly absent cells and **zero unresolved qualifying identities** in the comparable subset. Stroll's two already-correct times are now included. [Comparison](comparison-after-identity.json).

**44 focused tests and 150 portable tests passed; 733 scientific paths were unchanged.** The first run exposed one outdated composition expectation, subsequently extended to the identity layer; the tyre acceptance still requires exactly the original 262 age changes plus separately checked identity leaves. Logs and preservation evidence remain in this directory.

Checkout `/private/tmp/pitwall-stroll-identity-20261104`, branch `codex/stroll-spain-2025-identity`, remote base `4d42c5263caabfff24be2fdcbf1e78fa82e09b01`; package `/private/tmp/pitwall-stroll-0101-final/pitwall-dashboard`. Commit and delivered copy are recorded in `delivery.json`. Research reports and original archive bytes remain preserved.

Posterior descriptive correction only: no training, recalibration, forecasts, snapshot/emission changes or inferred historical availability. Local implementation and package verification are complete; no remote publication or public-host acceptance occurred in this correction.
