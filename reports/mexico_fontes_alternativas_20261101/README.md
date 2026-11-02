# México 2026 — fontes alternativas / Alternative sources

Created by: MBPaschoal
Status: implemented; validation and publication receipts recorded separately
Type: data adjudication report

## Português

Escopo: resolver os cadastros e paradas do TL3/classificação e revisar a temperatura do asfalto durante a corrida, com os originais e as previsões preservados. A aquisição foi serial, com oito segundos entre requisições e respostas brutas guardadas fora da distribuição.

| Pendência | Evidência | Tratamento |
|---|---|---|
| Perfil 30 ausente no TL3 | Lista revisada FIA, doc. 37; classificação do TL3; tabela F1 | Perfil de Liam Lawson/Racing Bulls adjudicado somente para 2026/r19/11399 e resultado compatível. Recuperados 22 tempos. |
| Número 236 e paradas de outra sessão | Horários publicados e análises de pista FIA do TL3/Q | Excluídos da projeção somente um registro anterior ao TL3 e 84 anteriores a Q. Mantidas 88 e 89 paradas, respectivamente. Nenhum nome foi atribuído ao número 236. |
| Lawson sem posição em Q | Classificação final FIA, doc. 59; decisão 57 | DSQ; posição numérica e tempos válidos vazios. Valores anteriores preservados nos brutos e no recibo da adjudicação. O zero oficial não prova ausência de voltas físicas. |
| Zero isolado no asfalto | PDF meteorológico FIA registra a mesma queda; vizinhos OpenF1 37,4/37,5 °C | Célula específica excluída da média, sem substituição/interpolação. Média 40,72 °C em 100 leituras válidas, cobertura 98,029% e intervalo máximo 120,041 s. A janela efetiva e demais sensores permanecem iguais. |

A revisão usa identidade explícita de evento/sessão, horário, valores esperados e fontes com URL/SHA/UTC. Perfil conflitante ou resultado incompatível interrompe a aplicação. Um número desconhecido dentro da sessão continua bloqueado. A exclusão do zero exige o registro e seus vizinhos adjudicados; outros zeros isolados continuam retidos. O cálculo mantém o limiar de 95% de cobertura e o limite de 180 s, sem abrir exceção para obter um número.

O relatório FIA confirma que o zero também está na origem; ele não fornece o valor real daquele minuto. A média é das leituras válidas da OpenF1, não uma média publicada pela FIA nem prova de recuperação da leitura ausente. O resumo FIA abrange o período contínuo, enquanto o agregado do Lab exclui a suspensão; extremos e médias de fontes/janelas diferentes não foram forçados a concordar.

**Lacuna remanescente:** o primeiro composto de Lawson no TL3, voltas 1–8, não aparece no feed. O trecho não foi preenchido a partir da idade/composto do stint seguinte. A estratégia fica não comparável e o TL3 permanece parcial para pneus, com os tempos e paradas disponíveis. O arquivo oficial de cronometragem respondeu 401; as consultas públicas de voltas de TL3/Q do Formula1Dashboard retornaram listas vazias. Não houve autenticação paga, contorno de acesso ou repetição indefinida.

A revisão alcança novos dados e caches completos, verificando os hashes antes de reprojetar. Não executa coleta durante a navegação. Modelo v1, 15 entradas, probabilidades e emissões permanecem preservados. Esta entrega também preserva o complemento de idade dos pneus já concluído localmente; esse complemento não preenche o composto ausente do México.

## English

Scope: resolve Mexico FP3/qualifying profiles and pit records, and review observed race track temperature while preserving raw data and recorded forecasts. Acquisition was serial, with eight-second spacing and raw responses outside distribution.

FIA entry document 37 and the FP3 classification identify car 30 as Liam Lawson/Racing Bulls for this event. All 22 FP3 times are restored. Temporal review excludes one pre-FP3 record and 84 pre-qualifying pit records, retaining 88 and 89 respectively; unknown number 236 is never assigned a guessed identity. FIA final classification 59 and decision 57 establish Lawson as DSQ, without a numeric rank or valid times. The final table's zero is not presented as zero physical laps.

The FIA weather PDF also records the isolated zero. Only its reviewed cell is excluded, with no interpolation or replacement: the remaining 100 OpenF1 readings average 40.72 °C, with 98.029% coverage and a 120.041-second maximum gap. Actual racing windows and other sensors remain unchanged. Coverage must still exceed 95% and the maximum gap must remain at most 180 seconds. This is a mean of valid readings, not a FIA-published mean or recovery of the missing minute. The continuous FIA chart and active-race Lab aggregate have different scopes; source extrema are not forced into agreement.

The initial FP3 compound for Lawson's laps 1–8 remains missing. It is not inferred from the next stint; that strategy remains non-comparable and FP3 remains partial for tyres. The official archive returned 401 and Formula1Dashboard FP3/Q lap queries returned empty lists; no access bypass or paid authentication was used. Explicit identities, expected values and URL/SHA/UTC receipts constrain all repairs. Conflicts still fail. Completed caches receive a new reviewed projection without changing captured bytes. The existing tyre-age complement is preserved and does not supply the absent Mexico compound. Model v1, its 15 inputs and recorded probabilities remain unchanged.

## Fontes e recibos / Sources and receipts

- [Índice FIA de cronometragem / Timing index](https://www.fia.com/events/fia-formula-one-world-championship/season-2026/mexico-city-grand-prix/event-timing)
- [Lista revisada / Revised entry](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_revised_entry_list.pdf)
- [TL3 / FP3 classification](https://www.fia.com/sites/default/files/2026_19_mex_f1_p3_timing_thirdpracticesessionclassification_v01.pdf)
- [Classificação final / Final qualifying](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_qualifying_classification.pdf)
- [Decisão / Decision 57](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_infringement_-_car_30_-_technical_nonconformity.pdf)
- [Clima oficial / Official weather](https://www.fia.com/sites/default/files/2026_19_mex_f1_r0_timing_raceweatherreport_v01.pdf)
- [Recibos de aquisição / Acquisition receipts](sources.json) · [Resolução / Resolution](data-resolution.json)
- [Adjudicação / Adjudication](../../operacao2026/adjudicacoes/2026-19-rodriguez.json) · [Testes / Regressions](../../tests/test_weekend_reconciliation.py)

Os PDFs e respostas brutas ficam no acervo local, sem redistribuição por esta nota. Os hashes comprovam a captura, não a disponibilidade anterior ao corte de uma previsão. Validação local, GitHub e versão pública têm recibos distintos.

PDFs and raw responses remain in the local archive. Hashes establish capture integrity, not availability before a forecast cutoff. Local validation, GitHub and public deployment have separate receipts.
