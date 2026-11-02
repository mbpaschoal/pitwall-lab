# Leitor e UI — alvos confirmados sem imputar posições

Created by: MBPaschoal
Status: complete — 91 testes aprovados
Type: implementation handoff

## Interface entregue

`avaliar_previsao_registrada()` mantém a assinatura. O campo opcional `podio_resultado_confirmado` admite somente inteiro 0/1, recusando bool, float, string ou outro valor. Posição positiva deve concordar com esse alvo. Posição ausente só permite alvo conhecido 0 quando o resultado está validado/observado e o status é explicitamente não pódio: DNF/Retired/NC/Not classified ou DNS/DSQ e equivalentes ingleses admitidos. DNF sem alvo confirmado continua desconhecido. Status não pódio com posição de pódio é contradição.

As posições reais 1/2/3 continuam obrigatórias e únicas. IDs/população completa, elegibilidade, probabilidades e rankings publicados conservam as guardas; um quarto favorito por ranking repetido no top 3 é recusado. Nenhuma posição de abandono é criada e nenhuma probabilidade é alterada.

`alvo_podio_posterior(participante, resultado_validado=False)` fornece 0/1/None para a projeção de leitura. `pacote_2026()` separa alvo conhecido de posição conhecida: a projeção real de México mantém 22 alvos e cinco posições None. `carregar_asset()` chama `validate_projected_asset(Path(raiz), asset)` do módulo integrado pelo coordenador, preservando a validação de anexo/hash/emissão/observados. Não há mock dessa validação nos testes finais.

## Apresentação

Acertos exibe exclusões prospectivas mesmo quando nenhum GP é pontuável, sem notas zero e sem somar exclusões ao denominador. “Fora da avaliação” exige estado observado e selo verdadeiro; resultado ainda não validado continua separado. Chances deixa de chamar uma emissão prospectiva de retrospectiva no ramo N/A e apresenta motivos traduzidos. Identidade visual e estrutura permaneceram iguais.

Arquivos deste agente: `pitwall/data/race_weekend.py`, `pitwall/dashboard/fan_views.py`, `pitwall/dashboard/model_views.py` e somente blocos N/A/motivos em `pitwall/dashboard/app.py`. As 13 traduções foram entregues em `traducoes_ui.json` e integradas ao catálogo real pelo coordenador. Produtor, anexo, exportação, registro, versão e publicação ficaram com o coordenador.

## Validação

- **58 testes focais aprovados**, incluindo os 11 novos em `tests/test_mexico_evaluation_ui.py`, além de `test_race_weekend_assets`, `test_fan_composition` e `test_uiux_method`: [log](ui-tests.log).
- **33 testes de dashboard aprovados** após o helper comum passar a copiar o anexo real e a expectativa do GP padrão acompanhar México/19: [log final](ui-dashboard-tests-final.log). Os ajustes foram feitos nos testes, sem afrouxar o leitor.
- Os testes novos verificam traduções de `en.json` real. Cobrem DNF conhecido/desconhecido, tipos/contradições, pódio, cobertura, rankings, imutabilidade em memória, selo inconsistente e apresentação N/A PT/EN. A regressão sobre o asset produzido confirma 22 participantes, 17 posições classificadas, 5 DNF nulos, 22 alvos e acertos 2/3 versus 1/3.

Uma execução anterior dos testes de dashboard falhou por ausência do anexo no diretório temporário do fixture; o log foi preservado em `ui-existing-tests.log`. Isso foi corrigido sem desativar o validador. Também houve uma tentativa que não iniciou por ENOSPC; após liberação de espaço, o módulo inteiro passou. Nenhum coletor, inferência, alteração da emissão, versionamento ou publicação foi executado por este agente.

English: the reader accepts validated binary podium membership without inventing unclassified finishing positions. Unknown targets remain unknown; contradictory targets/statuses and invalid coverage/rankings prevent scoring. Prospective exclusions and N/A wording remain distinct from retrospective studies. All 91 focused/dashboard checks passed with the real translation catalogue and posterior-annex validator. Release and public acceptance are owned by the coordinator.
