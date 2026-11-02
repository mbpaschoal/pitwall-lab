# México 2026 — rechecagem das duas lacunas restantes

Created by: MBPaschoal
Status: verified; no new admissible data
Type: data verification

Rechecagem em 2 de novembro de 2026, 01:49–01:51 UTC (1 de novembro no fuso de São Paulo). Evento 2026/19/rodriguez; TL3 11399; corrida 11404.

| Pendência | Resultado atual | Decisão |
|---|---|---|
| Composto de Lawson nas voltas 1–8 do TL3 | OpenF1 HTTP 200: somente os stints 2–5, a partir da volta 9 | Manter ausência e estratégia não comparável. A idade do pneu seguinte não comprova o composto anterior. |
| Temperatura do asfalto às 22:01:42.606 UTC | OpenF1 HTTP 200: permanece zero; vizinhos 37,4 e 37,5 °C | Manter exclusão documentada somente desta célula; sem substituição ou interpolação. |
| Revisão do boletim FIA de clima | HTTP 200; SHA-256 idêntico ao documento da adjudicação publicada | Não existe correção nesse documento desde a captura anterior. |

O [relato oficial das equipes](https://www.formula1.com/en/latest/article/what-the-teams-said-qualifying-in-mexico-city-2026.OeV40dsukK0h4mpxdkqoj) contém uma fotografia de Lawson no TL3, mas a legenda não informa o horário do stint. Ela não é prova suficiente para preencher as voltas 1–8.

Uma primeira consulta meteorológica usou chaves de comparação codificadas incorretamente e recebeu 404. A consulta corrigida, conforme a [documentação OpenF1](https://openf1.org/docs/), retornou as três leituras esperadas. O 404 é preservado para auditoria e não comprova ausência de registros meteorológicos.

As duas lacunas ficam classificadas como **indisponíveis nas fontes verificadas**, com recebimento futuro sujeito à validação. Não houve nova alteração no produto nem nova versão apenas para renovar a data de consulta. Permanecem a média de 40,72 °C em 100 leituras válidas e as correções publicadas em 0.8.3. A coleta hospedada está configurada para os minutos 7 e 37 de cada hora, condicionada às janelas operacionais e aos limites do provedor; isso não garante que a origem complete campos ausentes.

Validação: recibos e hashes das quatro respostas conferidos; boletim FIA idêntico; 614 arquivos científicos protegidos preservados; 20 testes de reconciliação e automação aprovados. [Verificação](verification.json), [captura e URLs](acquisition.json) e [adjudicação anterior](../mexico_fontes_alternativas_20261101/README.md).

## English

The bounded recheck found no verified replacement. OpenF1 still exposes Lawson's FP3 stints 2–5 only, leaving laps 1–8 without a known compound. The race track-temperature sample at 22:01:42.606 UTC remains zero between 37.4 and 37.5 °C. The FIA weather PDF is byte-identical to the previously reviewed source. A practice photograph lacks a stint timestamp and cannot resolve the gap.

The first weather request had incorrectly encoded comparison keys; its 404 is retained for audit only. The corrected documented filter returned all three expected samples. Missing values remain explicit, without imputation. No product release was created solely for a new acquisition timestamp. The published valid-sample mean remains 40.72 °C. Scheduled collection is configured twice hourly within operational windows and provider limits; it cannot guarantee that the source supplies missing fields.

Four receipt hashes verified; unchanged FIA PDF; 614 protected scientific files unchanged; 20 reconciliation and automation tests passed. Raw captures remain separate from frozen model inputs and recorded forecasts.
