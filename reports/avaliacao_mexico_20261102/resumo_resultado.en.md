# Posterior result audit — Mexico 2026/19

Created by: MBPaschoal
Status: audited with source discrepancy
Type: posterior result audit
Date: 2026-11-02

**The binary podium evaluation can be completed for all 22 participants using the FIA final classification as the authority. The current Jolpica capture has complete coverage but outdated finishing order and points.** This audit did not recalculate probabilities or metrics, or modify existing sources.

[FIA final document 86](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_race_classification.pdf), visually checked on page 2, and the [current F1 result table](https://www.formula1.com/en/results/2026/races/1298/mexico/race-result) agree on the Verstappen–Hamilton–Antonelli podium, 17 classified finishers and five DNFs. There are no race DNS or DSQ records. Lawson's qualifying disqualification must not be transferred to the race.

All 22 car numbers, `driverId` and `constructorId` values in Jolpica exactly match the qualifying capture frozen before the race. Hirakawa is car 50, `ryo_hirakawa`/`haas`: missing ID/team fields in the OpenF1 presentation asset do not justify excluding him.

The FIA final result includes post-race penalties for Piastri (+10 s), Colapinto (+10 s) and Gasly (+30 s). Compared with that final result, the [Jolpica capture](jolpica_2026_19_results_20261102T034127Z.json) and local OpenF1 data differ in 11 positions and seven points values. The podium and all 22 binary podium targets remain unchanged. Jolpica was captured at `2026-11-02T03:41:27.286720Z`, SHA-256 `c3ff9401f39f58edc621731371c9d7e45c3fbe03e6bf0be738fc6fa7a60565f8`.

The final document was published on the FIA index at `2026-11-02T01:50:00Z` (02:50 CET) and captured at `03:42:24.143473Z`, SHA-256 `681fc44eb9dd8e73096dcafb63d18257d344ead5617aab6fc0b1a3f2f4591cd3`. Result sources postdate both the reference issuance (`2026-11-01T04:32:23Z`) and observed race end (`22:23:54.505Z`). Capture times and hashes document the current snapshot, not historical availability.

The [final normalization](resultado_final_normalizado.json) preserves null official positions for DNFs. The PDF has no literal status text for classified finishers: `status_oficial_literal` stays null, while `status_normalizado` explicitly records the interpretation. Empty PDF points cells stay null in `pontos_oficiais`; explicit F1 zeros appear in `pontos_f1`. No missing record was converted to target zero: all 22 result records are present.

The [structured audit](auditoria_resultado.json) records the eight verified OpenF1 hashes, differences, sources and limits. The [page 2 image](fia_final_race_classification_page2.png), [official receipts](fontes_oficiais_recibos.json) and [Jolpica receipt](jolpica_resultado_fonte.json) preserve the evidence. Local verification is reproducible with `python3 -B reports/avaliacao_mexico_20261102/conferir_resultado.py`, without network access.

At the examined state, `race_weekend.json` still marks the result unavailable because its canonical snapshot contains results only through Austin/18. This does not contradict the public posterior result. Integration should create a separate posterior artifact without replacing the previous snapshot or frozen issuance. No collector, remote telemetry, training, export or publication was run during this audit.
