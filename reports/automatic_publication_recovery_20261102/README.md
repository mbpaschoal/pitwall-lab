# Recuperação da publicação automática / Automatic publication recovery

Created by: MBPaschoal
Status: published and independently verified
Type: delivery report

## Português

A [execução original](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41388497516) coletou e validou os dados, mas seu push atômico foi rejeitado porque outro commit avançou `main` durante os testes. A falha estava na entrega concorrente; as capturas continuaram preservadas.

A [versão 0.8.13](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.13) separa coleta e publicação. O publicador confere o ramo remoto antes de criar commit/tag e depois de uma rejeição de push. Com concorrência comprovada, agenda nova execução no `main` atual, restaura as capturas e refaz versão, pacote e validações. A recuperação é limitada a duas tentativas; autenticação, transporte e esgotamento continuam erros explícitos. [Implementação e procedimento](../../docs/runbooks/automatic-publication.md).

O teste hospedado foi deliberado e ficou registrado em [hosted-test-start.json](hosted-test-start.json). Um commit apenas de evidência avançou `main` durante a execução. A [execução 41392763522](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41392763522) terminou com `retry_scheduled`; a própria automação disparou a [recuperação 41394062050](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41394062050), usando o cache da anterior. A recuperação terminou com sucesso e publicou a [versão 0.8.14](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.14), commit `135212dacaddb7b02dd7a01a05dc23cde248ec71`. Não houve push forçado nem reescrita do histórico publicado.

Evidências:

- [Validação da correção](validation.json): 297 testes de fonte, 141 do pacote, incluindo oito testes de concorrência com repositórios Git reais; 614 arquivos científicos preservados. O campo público desse recibo descreve a etapa ainda pendente naquele momento; a conclusão posterior está nos recibos abaixo.
- [Disparo automático](recovery-dispatch.json) e [conclusão hospedada](hosted-completion.json): revisão antiga, revisão atual, cache, tentativa, publicação, release e verificação pública do workflow.
- [Build público independente](public/public-build.json): sessão nova servindo `0.8.14`, com o hash completo `8f37cc93b5bc5a491f64fd428e25e83812205ad854665fad5386bc12c67c0133`, igual ao manifesto. [Captura](public/public-build.png), [verificador](public-build.cjs).
- [Integridade das fontes](capture-integrity.json): arquivo da release baixado e conferido pelo SHA-256; 776 arquivos, 86 manifestos e 603 registros de fontes com bytes correspondentes aos hashes originais. Recibos desde 30/10 preservados, incluindo as execuções anteriores à recuperação; 614 arquivos científicos novamente idênticos.
- [Aceite público](public-browser/acceptance.json): PT/EN, computador/celular, pódio, clima observado, TL3, desclassificação em Q, penalidades finais, NC, previsão registrada e 35 linhas de campeonato. Os CSVs baixados ficam na mesma pasta.
- [Diferença da projeção](data-delta.json): os 22 tempos de cada uma das cinco sessões mantêm seus valores. O cache legado de TL1/TL2 não contém a chave opcional `piloto_id` nos tempos; nomes e números continuam presentes. Projeções novas já produzem essa chave. Esta publicação não representa preenchimento das lacunas de pneus.

Limites: publicação concluída não significa cobertura integral das fontes. O México continua com quatro das cinco sessões no estado `dados_recebidos`; TL3 permanece parcial por lacuna do composto inicial de Lawson e cadastro original com 21 pilotos. A revisão documentada mantém os tempos de todos os 22 pilotos. Probabilidades, modelo v1 e registros prospectivos permanecem congelados. O agendamento serial existente segue ativo; o dashboard não coleta dados durante a navegação.

## English

The original run collected and validated data, but another commit advanced main before its atomic push. The fix in 0.8.13 checks remote main before publication and after a rejected atomic push. A proven race dispatches a fresh workflow on current main, restores captures and repeats versioning, packaging and validation. Recovery is bounded to two attempts; unrelated permission/transport failures remain visible. Published history is preserved.

A deliberately recorded evidence commit exercised this behavior on GitHub. Run 41392763522 reported `retry_scheduled`; its automatically dispatched child 41394062050 restored the parent's cache, passed validation, published 0.8.14 and verified Streamlit. An independent fresh browser also matched the full served build to the manifest. The linked receipts retain the complete lineage and release asset digests.

Verification includes 297 source tests, 141 portable tests and eight focused Git concurrency tests. All 614 protected scientific files remain unchanged. The downloaded capture archive contains 776 files and 86 manifests; 603 source receipts match original content hashes, retaining captures since October 30. Public acceptance covers Portuguese/English on desktop/mobile, observed weather, FP3, qualifying disqualification, final penalties and NC drivers, frozen forecasts and complete round standings, with actual CSV downloads.

The linked projection diff confirms unchanged published timing values for all 22 drivers in each session. Legacy FP1/FP2 cached timings lack the optional `piloto_id` key, while names and numbers remain available; fresh projections already emit this field. This release does not claim new tyre-gap observations.

Coverage remains explicit: four of five Mexico sessions have received-data status. FP3 is still partial because Lawson's initial tyre compound is unavailable and the original roster contains 21 drivers; the documented review retains all 22 published timing results. This operational recovery does not retrain v1 or change recorded probabilities. Existing serial scheduling stays active; browsing does not trigger collection.
