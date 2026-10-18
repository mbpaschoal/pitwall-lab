# Etapa 5 — avaliação final retrospectiva do modelo v1 em 2025

Status: avaliado_para_modelo_v1

Esta avaliação usa o modelo v1 congelado e a fonte de teste de 2025. A previsão e a seleção dos favoritos ocorreram antes de extrair `podio`; o alvo vazio permaneceu desconhecido, nunca foi convertido em zero. Não houve ajuste, calibração, seleção de variáveis ou mudança de limiar.

## Cobertura

- Linhas de teste: 480; elegíveis para previsão: 479; inelegíveis: 1.
- Linhas com alvo conhecido: 479; alvo desconhecido: 1; linhas nas métricas probabilísticas: 478.
- GPs presentes: 24; GPs avaliáveis no ranking comum: 22.

## Métricas probabilísticas

| Método | Log loss | Brier |
| --- | ---: | ---: |
| Modelo | 0.20328013885785817 | 0.058518438214266853 |
| Constante de treino | 0.42379724063090557 | 0.12793920072881459 |

Para Brier, o modelo foi menor que a constante. Menor é melhor, mas um Brier menor sozinho não prova calibração melhor. A calibração descritiva tem dez faixas e mantém faixas vazias sem frequência artificial.

## Rankings top 3

| Método | GPs avaliáveis | Média de integrantes corretos | Proporção de 3 corretos |
| --- | ---: | ---: | ---: |
| Modelo | 22 | 2.3181818181818183 | 0.36363636363636365 |
| Classificação | 22 | 2.2727272727272729 | 0.36363636363636365 |

Os dois rankings compartilham a mesma coorte de GPs avaliáveis. GPs com menos de três elegíveis, participante inelegível, alvo desconhecido ou número de pódios diferente de três têm pontuação indefinida, não zero artificial. Empates seguem `piloto_id` lexicográfico; posições de classificação ausentes ficam após as conhecidas. Probabilidades individuais não foram renormalizadas para somar três por GP.

## Comparação descritiva com 2024 e limites

Os valores de 2024 em `comparacao_2024.json` têm denominadores próprios: 479 linhas probabilísticas e 24 GPs de ranking, contra 478 e 22 em 2025. São temporadas diferentes. Esta comparação não afirma significância estatística, causalidade ou desempenho futuro.

As fontes históricas podem conter revisões posteriores ao corte. Este estudo continua retrospectivo e não comprova que uma previsão foi emitida antes de cada corrida.
