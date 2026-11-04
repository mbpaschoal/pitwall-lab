# Complementary sources

[Português](../FONTES_COMPLEMENTARES.md)

The archive uses an approved descriptive F1DB/FIA/Pirelli supplement. Its original base stays intact: the reader validates the original snapshot and 262 previously approved tyre-age revisions first, then applies `frontend_assets/complemento_fontes_v1.json` in memory. The supplement is also hash-pinned. Navigation performs no collection, training or inference and does not alter the 15 inputs, frozen v1 or recorded probabilities.

## Sources and admission

[F1DB v2026.19.0](https://github.com/f1db/f1db/releases/tag/v2026.19.0) is a complementary candidate attributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Its sample contains 61 qualifying records across São Paulo 2024/2025 and Mexico 2026. Identity combines season, round, date, circuit coordinates, event car number and birth date; provider IDs remain separate. Canonical values, candidates and admitted fields retain distinct roles.

Only reviewed FIA PDF transcriptions can change fields in a new projection. Three admitted São Paulo 2024 Q2 times were already correct in the interface: this delivery adds provenance. Mexico 2026 is absent from the 66-GP/330-session base; its DSQ review remains in the supplement instead of fabricating an event. DSQ/DNS/NC retain raw observations while removing valid display positions/times. FIA documents retain their own terms.

[Pirelli — São Paulo 2026](https://press.pirelli.com/pirelli-brings-the-softer-trio-back-to-interlagos/), published on 3 November 2026, supplies HARD C3/MEDIUM C4/SOFT C5 allocation and circuit context. Facts and expectations remain separate from observed sessions. The article does not establish an executed strategy or causal effect. F1DB/Jolpica licences are not extended to Pirelli/FIA. See [package attribution](../../publicacao/templates/FONTES_E_DADOS.md).

## Reproduction and limits

`pitwall.data.complementary_sources` builds supplements offline from local plans and retained raw evidence. Those authoring inputs remain in the local research archive and are not published with the application. Public CI validates the approved bundle and actual composition with tyre-age revisions; controlled fixtures exercise the builder and admission rejections. CI does not replace the original documentary review.

To reproduce the source projection without modifying the base, use `python -B -m pitwall.data.complementary_sources project --asset frontend_assets/acervo_dashboard.json --bundle frontend_assets/complemento_fontes_v1.json --output /private/tmp/acervo-complementado.json`. This independent output contains the source supplement; `pitwall.data.archive.carregar` performs the full composition including tyre ages. The authoring producer `preparar_acervo_dashboard.py` also accepts `--complemento-fontes`. Divergent outputs require a new destination; the same supplement is idempotent.

Local deliveries 0.9.0 and 0.9.1 remain preserved separately. Version 0.9.2 integrates admission onto public base 0.8.31, retaining its security, touch and navigation corrections. Capture on 4 November 2026 does not prove availability at historical cutoffs. No predictive gain has been established. Local tests, CI, release and the Streamlit-served version are separate evidence layers.
