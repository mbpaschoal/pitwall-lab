# Mexico prospective evaluation — 2026

Created by: MBPaschoal
Status: implemented; publication pending verification
Type: posterior evaluation report

[Português](relatorio.md)

The recorded prospective prediction selected **2 of 3 podium finishers**, compared with **1 of 3 for qualifying**. The final podium is Verstappen, Hamilton and Antonelli. The frozen Lab selections remain Verstappen, Hamilton and Russell; qualifying selected Hamilton, Russell and Leclerc. Neither selection identified the complete podium.

Coverage is **22 participants, 22 known targets and zero exclusions**. Five documented retirements retain unknown official positions and confirmed negative podium targets. Missing rows, unknown statuses and invalid targets remain unevaluable. Administrative positions 18–22 from other providers do not replace the FIA's missing positions.

The [emission audit](auditoria_emissao.json) passed 32 checks, covering the exact emission timestamp `2026-11-01T04:32:23.054391Z`, public evidence before the race and the preserved original inventory. Original manifest and CSV hashes bind the [public annex](../../frontend_assets/avaliacao_posterior_mexico_2026.json) to the recorded probabilities, rankings, eligibility, driver and team identities. Admission requires observed race completion, official final publication and a later capture.

The admitted authority is **FIA document 86**, published at `2026-11-02T01:50:00Z` and captured at `03:42:24.143473Z`, SHA-256 `681fc44eb9dd8e73096dcafb63d18257d344ead5617aab6fc0b1a3f2f4591cd3`. Its [audited normalization](resultado_final_normalizado.json) was visually checked against the PDF and corroborated by F1. Preserved Jolpica and OpenF1 results differ in positions and points before final penalties; all sources agree on the podium. [Sources and limitations](resumo_resultado.en.md).

The [offline producer](../../preparar_dashboard_race_weekend.py) verifies original source bytes before applying targets. The [portable validator](../../pitwall/data/post_race_evaluation.py) requires only the explicit allowlisted annex. Modified forecasts, results, identity, chronology or audit bindings are rejected. Singapore's retrospective study and Austin's recorded prediction retain their separate contexts.

“How the Lab did” now shows 2/3 versus 1/3 for Mexico and two evaluable prospective races in 2026. This small sample does not establish superiority, calibration or future predictive ability. “Podium chances” retains the published favorites and probabilities. Excluded races show N/A and the reason without relabelling a prospective emission as retrospective.

Product version **0.8.7** integrates this evaluation while preserving the locally validated 0.8.6 tyre presentation work. Operational final classification reconciliation and São Paulo preparation were developed concurrently. This task did not train or re-emit a model; frozen scientific artifacts stay unchanged.

Local and public checks are recorded alongside this report. Mobile checks use emulated viewport/touch settings, not a physical handset or screen reader.

Final publication uses **0.8.8**: 0.8.7 CI included five legacy tests depending on unpublished local captures. The correction retains local validation and the public CI integrity/portable tests, preserving tag0.8.7. The final served build requires a fresh public-session check.
