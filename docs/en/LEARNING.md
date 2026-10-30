# Learning and product refinement

[Português](../APRENDIZADOS.md) · English

Created by: MBPaschoal
Status: active
Type: learning journal

This journal explains technical decisions; it is not a list of uniformly positive results. Historical commit messages retain their original language and date. This bilingual account adds context without rewriting history.

| Evidence | Problem noticed | Correction and lesson |
|---|---|---|
| [Stage 3](protocolo_temporal.md) | Date-ordered data can still contain later source revisions. | Separate conceptual cutoff, conservative release rule and actual acquisition. A hash proves bytes, not historical availability. |
| [2025 evaluation](relatorio_2025.md) | A model advantage can look larger without a common comparison population. | Explicit denominators and cohort: 51 versus 50 podium drivers; both 8/22 complete podiums. Do not claim significance. |
| [8beae28](https://github.com/mbpaschoal/pitwall-lab/commit/8beae28) | The sidebar became difficult to reopen. | Restore native controls and verify mobile. Appearance does not replace usable navigation. |
| [128e272](https://github.com/mbpaschoal/pitwall-lab/commit/128e272) | The main source did not cover Austin session times. | Add an identity/provenance-checked alternative, separate from the recorded prediction. |
| [0e97fbc](https://github.com/mbpaschoal/pitwall-lab/commit/0e97fbc) | Duplicate panels and incomplete standings obscured information. | Give each datum a canonical screen and display every published standings row. |
| [edca988](https://github.com/mbpaschoal/pitwall-lab/commit/edca988) | Locally working links failed in Cloud. | Test real iframe/new-tab clicks. A push is not deployment proof. |
| [Data review](CURRENT_DATA.md) | History answered a current-race question; stint warnings were treated as gaps. | Filter by literal circuit identity and earlier date; distinguish quality warnings from unknown boundaries. Preserve actual missingness. |
| [Version 0.1.0](../../CHANGELOG.en.md) | Scattered code and one language hindered maintenance and portfolio accessibility. | Organise responsibilities, centralise offline translation and retain compatibility. Product and model versions mean different things. |

## Recording the next improvement

Explain prior behaviour with a concrete example, known cause or uncertainty, delivered change, executed verification and remaining limitations. A hypothesis is not a confirmed finding. Dates and versions must match actual deliveries: no fabricated old commits or edited results to improve the narrative.

## 0.2.0: comparisons require a verified denominator

The brainstorm counted rain across whole sessions and could select a Sprint through the Race session type. The audit now requires the literal main-race name, start/end status and exclusion of suspensions. This changed the result to eight races with rain during active racing. I also learned to preserve feed differences: Australia/2026 lap numbers must not be corrected by shifting unmatched rows. Rates now show starts and ties; incomplete sources remain incomplete. [Evidence and limits](../../reports/pilotos_condicoes_20261029/README.en.md).

## 0.3.0 — Fair comparisons and enjoyable reading

I learned that a correctly typed field can still be semantically wrong: wind direction needs a circular mean. Comparing one driver with the entire grid also requires aligned races and denominators. Both decisions now have regression checks. Each kind of information has a clear home: results in Races, standings in Championship, estimates in Podium chances. Duels use shared starts and cards include period, sample and source. A green source-tree test does not prove the published package matches the code; delivery now checks both.
