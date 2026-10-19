> Nota de adaptação pública: este documento deriva de `reports/modelo_v1/relatorio.md`; preserva os resultados textuais. Somente os quatro links locais foram ajustados para a demonstração mínima.
> SHA-256 da origem: d8f222555f086b967735bdcba976b83e6944681a9911772450a2d6a509ca7c0e.

# Etapa 4 — modelo v1 de probabilidade de pódio

Este é um estudo retrospectivo. O protocolo em `docs/experimento_modelo_v1.md` foi fixado antes do ajuste. O treino usa somente 2021–2023; a validação usa somente 2024, que já havia sido explorada. O teste de 2025 não foi aberto nem avaliado.

## Cobertura

- Linhas de validação: 479; elegíveis para previsão: 479; inelegíveis: 0; com alvo conhecido: 479; alvo desconhecido: 0.
- Linhas usadas nas métricas probabilísticas: 479.
- GPs presentes em 2024: 24; GPs avaliáveis para os rankings comuns: 24.
- Treino: 1319 linhas elegíveis e rotuladas ajustaram o pipeline; 1 linha ficou inelegível; a referência constante foi 0.15011372251705837 nessas mesmas linhas.
- Exclusão de treino: 2021/5 — mick_schumacher — Monaco Grand Prix: classificacao_ausente. A auditoria completa está em cobertura_treino.csv (artefato de auditoria fora desta demonstração).
- Classificação ambígua em validação: 8 linha(s). Os desempates e o impacto na fronteira estão registrados por piloto em [previsoes_validacao.csv](../reports/modelo_v1/previsoes_validacao.csv), nas colunas `empates_classificacao` e `empates_modelo`.

## Métricas probabilísticas

| Método | Log loss | Brier |
| --- | ---: | ---: |
| Modelo logístico | 0.22955624759095355 | 0.070917930921086059 |
| Constante de treino | 0.42325205376037162 | 0.12771914838843695 |

Menor é melhor nas duas métricas. O CSV e o SVG de calibração usam dez faixas fixas e mostram contagens; faixa vazia não é interpretada como frequência zero.

Gráfico SVG de calibração (artefato de auditoria fora desta demonstração).

## Rankings top 3

| Método | GPs avaliáveis | Média de integrantes corretos | Proporção de 3 corretos |
| --- | ---: | ---: | ---: |
| Modelo por probabilidade | 24 | 1.9583333333333333 | 0.25 |
| Classificação | 24 | 1.875 | 0.16666666666666666 |

Distribuição de GPs com 0 / 1 / 2 / 3 integrantes corretos: modelo = **1 / 5 / 12 / 6**; classificação = **1 / 5 / 14 / 4**.

Os rankings só são pontuados quando todos os participantes preparados são elegíveis, todos têm alvo conhecido e existem exatamente três pódios. GP incompleto não recebe zero artificial. A referência de classificação é ranking, não probabilidade; posição ausente fica ao final e empates usam `piloto_id` em ordem lexicográfica. O modelo usa probabilidade decrescente e o mesmo desempate somente em empate exato.

## Leitura e limites

Os coeficientes padronizados completos estão em coeficientes.csv (artefato de auditoria fora desta demonstração). Os três maiores valores absolutos nesta execução foram: posicao_classificacao (-1.9757); media_pontos_equipe_5 (+0.5147); historico_piloto_insuficiente (-0.2835). Sinal positivo/negativo descreve associação condicionada às demais entradas, ao treino e à regularização; não é efeito causal. As probabilidades individuais não precisam somar três em um GP e não foram renormalizadas. Há poucas temporadas, pilotos do mesmo GP são correlacionados, 2024 já foi explorada e as fontes históricas podem conter revisões posteriores. Este resultado não alega generalização para 2025.

O modelo salvo é um arquivo joblib local confiável; não carregue arquivo joblib/pickle recebido de terceiros.
