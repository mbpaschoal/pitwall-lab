# México final e preparação de São Paulo

Created by: MBPaschoal
Status: locally verified; publication pending
Type: operational data delivery

## Fontes e correções

A [classificação final FIA, documento 86](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_race_classification.pdf), foi conferida visualmente e contra os 22 registros do [resultado oficial F1](https://www.formula1.com/en/results/2026/races/1298/mexico/race-result). A resposta atual da Jolpica ainda contém posições e pontos anteriores às punições. Há 11 linhas canônicas com posição/pontos divergentes; [comparação completa](differences.json). Não se altera a resposta original.

- Piastri: 13º, com 10 segundos de punição; Colapinto: 15º, com 10 segundos; Gasly: 17º, com 30 segundos convertidos de stop-and-go.
- Os demais classificados são reposicionados conforme o documento final. Voltas, tempo total, diferença e pontos vêm da mesma tabela oficial; nenhum tempo é interpolado.
- Os cinco NC mantêm posição oficial e tempo final ausentes. Sua ordem na tabela de auditoria não é uma posição de chegada.
- O pódio final é Verstappen, Hamilton e Antonelli. A avaliação das probabilidades registradas identifica dois integrantes no top 3 do Lab e um no top 3 da classificação, sem estimar ordem de pódio. O cálculo editorial e seu recibo são mantidos pela entrega de avaliação em `pitwall/data/post_race_evaluation.py`; o módulo operacional desta entrega não pontua nem reemite previsões.

`operacao2026/final_results.py` valida população, números, perfis, campos finais e proveniência posterior da FIA. A integração em `weekend_reconciliation.py` altera somente uma cópia dos dados, registra o estado anterior e acompanha o hash da adjudicação. Assim, uma consulta automática futura não restaura a classificação anterior às penalidades. O bruto, o v1 e as probabilidades permanecem preservados.

O cadastro nativo de Ryo Hirakawa tem nome completo e número 50, mas não informa nome/sobrenome separados nem equipe. Sua identidade nesta revisão é documentada pelo número/nome exatos da FIA/F1 e pelo driverId literal da Jolpica. A equipe é exibida como Haas F1 Team somente na cópia revisada, com o campo anterior ausente registrado na auditoria. O cadastro bruto e o mapa global de inscritos de outras sessões permanecem preservados.

O composto das voltas 1–8 de Lawson no TL3 e a leitura verdadeira do asfalto registrada como zero continuam indisponíveis. As correções de resultado final não removem essas limitações.

## São Paulo

[Configuração explícita](../../operacao2026/eventos/saopaulo2026.json): 2026/20/interlagos, meeting 1299, sessões 11405/11406/11407/11408/11412. Datas/horários conferidos entre calendário canônico local, catálogo OpenF1 e [programação oficial F1](https://www.formula1.com/en/racing/2026/brazil).

| Sessão | Horário local (UTC−3) | UTC |
|---|---|---|
| TL1 | 06/11, 12h30 | 15h30 |
| TL2 | 06/11, 16h | 19h |
| TL3 | 07/11, 11h30 | 14h30 |
| Classificação | 07/11, 15h | 18h |
| Corrida | 08/11, 14h | 17h |

A coleta permanece serial, limitada e condicionada à janela do evento; nenhuma sessão futura é tratada como encerrada. A previsão de São Paulo depende da classificação principal e da conferência do histórico final do México. A revisão descritiva não é admissão automática de features.

## Evidências

[Recibos de aquisição](acquisition.json) guardam URL, UTC, status, tamanho e SHA-256 de cinco respostas. A primeira tentativa parou por falta de espaço e continua preservada; a retomada usa diretório novo. Dois ZIPs temporários anteriores foram removidos após conferência de todos os membros contra árvores completas preservadas; [recibo de espaço](storage.json).

Testes operacionais: `tests.test_final_results`, `tests.test_weekend_reconciliation` e `tests.test_weekend_cloud`. A matriz do blueprint inclui o novo módulo; o [validador](blueprint.json) não encontrou erros. O recibo final de validação/publicação deve distinguir testes de origem, pacote isolado, GitHub e dashboard servido. Não se publica uma prova visual de fonte como licença de redistribuição do PDF; arquivos FIA brutos permanecem locais.

## English

FIA final classification document 86 and all 22 official F1 result rows agree. The newly captured Jolpica response still predates post-race penalties; eleven canonical rows differ in position or points. Piastri is 13th, Colapinto 15th and Gasly 17th. Native reconciliation applies the reviewed final values to a copy, retains the previous state in its audit and prevents automatic collection from restoring stale positions. Five unclassified drivers retain unknown official position/finish time. Original captures and forecasts remain unchanged.

The final podium contains Verstappen, Hamilton and Antonelli. Editorial scoring is owned by the separate post-race evaluation module; this operational module neither scores nor emits forecasts. Missing FP3 compounds and the excluded track-temperature sample remain explicit.

São Paulo is configured as 2026/20/interlagos, meeting 1299, with five traditional sessions and a 17:00 UTC / 14:00 local race start on 8 November. The existing scheduled collector observes its event window, free-tier restrictions and actual session completion. A new forecast must wait for main qualifying and verified canonical history; descriptive final-result repairs are not automatically model inputs. Raw source PDFs remain local. Validation and public deployment have separate receipts.
