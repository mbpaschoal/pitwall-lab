# P1 — protocolo prospectivo e auditoria de preparação

Created by: MBPaschoal
Status: prepared for public review; no P1 event forecast issued
Type: prospective protocol and operational audit
Date: 2026-11-05

[Português](protocolo.md) · [English](protocol.en.md) · [Roteiro PT/EN](runbook.md) · [Hashes públicos](public-protocol-manifest.json) · [Resumo da auditoria](public-audit-summary.json)

O P1 fixa v1 versus referência probabilística de qualifying antes de novos eventos. A janela considera20 GPs realizados, registrando também falhas de cobertura; não substitui perdas de cobertura por provas posteriores. O protocolo descreve limites e decisão, sem reabrir a busca retrospectiva por um modelo favorável. A evidência de registro público é a revisão/PR com horário do servidor, vinculada aos hashes deste conjunto; o timestamp local isolado não basta.

## Auditoria atual

- Fonte operacional: árvore idêntica ao main `6a35f181fcd7669c317f299cb593ddc86724a417`, produto0.10.1. Nenhuma alteração no produtor científico, modelo, entradas, emissões ou interface.
- **106 testes existentes** e **20 testes P1** aprovados localmente. Registry nativo validou19 eventos:17 ensaios retrospectivos e2 prospectivos, sem emissão registrada de SãoPaulo. Os registros anteriores não são amostra P1.
- A execução hospedada [42011246914](https://github.com/mbpaschoal/pitwall-lab/actions/runs/42011246914) concluiu com `outside_race_weekend`; a manutenção subsequente concluiu com sucesso. Isso corresponde ao horário anterior à janela, não a uma previsão pronta. Readiness confirmou referência de pista, calendário e75 artes de25 pares de catálogo; inventário de artes não é lista de inscritos.
- Estado nativo de SãoPaulo: **waiting_for_observed_qualifying**. A classificação, encerramento, roster real, dados históricos finais e prova pública da previsão ainda dependem do evento. Testes/estado offline não provam futura coleta real.
- O anúncio de [Câmara na Haas](https://www.formula1.com/en/latest/article/f2-racer-camara-to-make-f1-debut-at-sao-paulo-grand-prix-as-haas-confirm-ocon-will-not-return.12Qa0tpaMZ9kgnEuGJBKFp) está revisado por hash. O fallback OpenF1 ainda não tem seu mapeamento literal. Se a fonte canônica faltar, bloquear até revisão com fontes reais; não inferir IDs/números. [Calendário oficial](https://www.formula1.com/en/racing/2026/brazil).
- **731 arquivos protegidos preservados**. Sem coleta manual, treino, emissão, agendamento ou mudança de produto nesta preparação. O PR registra protocolo/código de acompanhamento; não publica uma previsão futura.

## Acompanhante Q e prova pública

[ReferênciaQ](q-baseline-frozen.json): parâmetros já ajustados em2021–2023,1319linhas; nenhuma reestimação com2026. [Comparador](pair_predictions.py) usa a matriz da emissão prospectiva v1 já validada pelo registry, conserva suas probabilidades e prepara Q nas mesmas chaves. A reconstrução das479 referênciasQ de2024 concorda até arredondamento, sem ajustar modelo. [Fixture histórica de compatibilidade](q-reconstruction-fixture.json) é somente teste de formato/fórmula, não previsão prospectiva.

O comparador exige hashes/UTC/identidade/roster/prazo e retorna `prepared_not_published`. [Verificação pública](verify_published_pair.py) confere o digest/tamanho e os horários de criação/atualização de um asset público de release no repositório. Ambos os arquivos precisam estar disponíveis antes de largada−60min. A prova do dashboard servido é separada e precisa ocorrer antes da largada. Um upload tardio não é reparado por entrada antiga.

**A integração hospedada atual publica v1, não invoca o acompanhante P1.** O [runbook](runbook.md) fornece a execução/publicação manual pós-Q. Sem par público no prazo, registrar falta de cobertura. Integração automática seria mudança de produto separada; não foi criada aqui.

Para testar em checkout íntegro com ambiente existente:

```sh
cd reports/prospectivo_p1_20261105
python -B -m unittest -v test_pair_predictions test_public_receipt
```

O protocolo e os auxiliares são entregues para revisão. Nenhum par real P1 foi criado e não há demonstração de ganho futuro nesta preparação.

## English

P1 fixes originalv1 versus a frozen2021–2023 qualifying-logistic reference before future events, with a20-held-GP window and all coverage failures retained. Local audit:106 native tests and20 companion/public-receipt tests passed;19 native events validate (17rehearsals,2earlier prospective forecasts), none for SãoPaulo. The current forecast state waits for observedQ. Local source tree matches main0.10.1;731 protected files are unchanged. Public workflow success before the collection window does not mean forecast readiness.

Camara's announcement is reviewed, but canonicalQ IDs/roster are pending and the OpenF1 fallback lacks a literal mapping. Block rather than infer a replacement ID. Readiness artwork inventory is not an entry list. No new collection,fitting,event forecast,scheduling or product/UI change occurred.

The manual companion preserves validatedv1 probabilities, preparesQ on identical keys and never claims publication. The read-only receipt checker binds public release-asset server timestamps,digest and size to immutable pre-deadline pair bytes. Require both before race−60min and separate served-dashboard proof before race start. Existing hosted automation does not invoke this companion; follow the bilingual runbook after realQ, or record coverage failure. This PR/revision provides public protocol/code hashes for review, not an issued event forecast or evidence of future predictive gain.
