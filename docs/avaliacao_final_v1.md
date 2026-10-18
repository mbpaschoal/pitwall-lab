# Avaliação final retrospectiva do v1 — plano anterior à abertura de 2025

Created by: MBPaschoal
Status: plano congelado antes da avaliação
Type: final evaluation protocol
Registro UTC anterior à abertura: 2026-10-18T06:43:57.198266+00:00

## Compromisso e estado inicial

Este plano foi registrado antes de carregar o teste real de 2025. Os 100 testes existentes passaram com o teste real e bases mistas bloqueados, sem conexão à rede. Os testes legados ajustam modelos apenas em exemplos simulados; não foi reexecutado o ajuste do modelo v1 real. Os metadados foram conferidos. O commit de origem é `9a3b7b832334888af799e981cd173f26339c28d2`.

Avaliar exclusivamente a versão v1 já salva. Não executar `fit`, `fit_transform` ou `partial_fit` em nenhum estágio durante a avaliação final; não recalcular medianas, escalas, coeficientes, calibração, variáveis, hiperparâmetros ou limiares. Não treinar outra versão nem alterar regras em resposta aos resultados de 2025. Repetir a mesma avaliação congelada para conferência é permitido. Qualquer bug de implementação deve ser documentado e corrigido sem procurar uma combinação favorável.

## Identidade congelada — SHA-256

| Artefato | SHA-256 antes de abrir o teste |
|---|---|
| `models/modelo_v1/modelo.joblib` | `16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3` |
| `models/modelo_v1/metadados.json` | `77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6` |
| `docs/experimento_modelo_v1.md` | `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569` |
| `treinar_modelo_v1.py` | `cdf1c2ea005f36f032ebd1694786e9118ae343a282172fafb748cbf5c2294de3` |
| `reports/modelo_v1/metricas.json` | `e06613f5178fecdd06e7afdccb0503ab4f277e5712c61c5cf85f193ae240686f` |

O pipeline é local e confiável, não um joblib recebido de terceiros. Preservar o treinador, o plano original, os arquivos do modelo e todos os artefatos da etapa 4 byte a byte. O manifesto da avaliação registrará também o hash deste plano, do esquema, do script, da fonte de teste e de cada saída, sem autorreferência ao próprio manifesto. Não registrar caminhos pessoais ou credenciais.

## Fontes e execução permitidas

Depois do registro deste plano, somente `data/preparado/teste_final_reservado.csv` está autorizado como fonte de dados de teste. `data/preparado/colunas.json`, o modelo/metadados locais, os documentos e `reports/modelo_v1/metricas.json` são auxiliares permitidos. A rotina final não deve abrir treino, validação, base histórica completa, tabelas mistas, JSON históricos ou dados de 2026. Não consultar API, executar coletores ou regenerar bases.

Validar antes da previsão: CSV não vazio, divisão literal `teste_final_reservado`, temporada literal `2025`, chaves preenchidas e únicas, rodadas positivas, esquema e lista de entradas exatos. Recusar mistura de anos/divisões, números inválidos ou infinitos e colunas proibidas na seleção de entradas. Colunas de auditoria podem existir no CSV completo, mas nunca participar da matriz, elegibilidade ou seleção. Conversões de booleanos, NaN numérico e validações preservam as definições v1.

A preparação sequencial já existente pode usar resultados de GPs anteriores de 2025 nas janelas de GPs posteriores. Isso não é autorização para recalcular janelas nesta tarefa ou reestimar o modelo. Permanecem os limites do [protocolo temporal](protocolo_temporal.md).

## Entradas — lista e ordem v1, sem seleção nova

```text
posicao_classificacao
posicao_classificacao_repetida
classificacao_ausente
posicao_classificacao_ausente
media_posicao_final_5
taxa_podios_5
n_posicoes_5
n_podios_5
media_pontos_equipe_5
n_corridas_equipe_5
n_participacoes_equipe_5
historico_piloto_insuficiente
historico_equipe_insuficiente
equipe_pre_corrida_ausente
referencia_temporal_ausente
```

Imputação mediana, StandardScaler e regressão logística continuam com os parâmetros salvos, incluindo `C=1`. Transformar e prever não significa reaprender. As probabilidades individuais não serão renormalizadas para somar três por GP.

## Elegibilidade, previsão e alvos em fases separadas

Aplicar a mesma elegibilidade v1: registro de classificação presente e referência temporal disponível, com limite inferior preenchido. Não excluir por posição final, pontos, abandono, DNS, desclassificação ou `resultado_ausente`.

- Classificação completamente ausente: preservar linha de cobertura, sem previsão, com motivo.
- Classificação presente com posição ausente: elegível; o pipeline usa sua imputação já aprendida. O ranking da classificação coloca ausentes ao final.
- Posição repetida/ambígua e histórico insuficiente: preservar valores e indicadores, sem exclusão ou desempate esportivo inventado.
- Separar a projeção pré-corrida da extração/validação dos alvos. Produzir probabilidades e selecionar favoritos sem acessar `podio` ou desfechos de auditoria. Só depois juntar os alvos por chave para pontuar. O CSV contém ambos, mas valores de alvo não são usados na fase de previsão.
- Alvo vazio é desconhecido, não zero: não impede previsão de um elegível. Registrar `alvo_conhecido` apenas na fase de avaliação.

## Referências e desempates congelados

A. Constante de treino dos metadados: **`0.15011372251705837`**. Não recalcular em 2025 nem reabrir treino para estimá-la.

B. Ranking da classificação: posição numérica crescente, posições ausentes depois das conhecidas; empate por `piloto_id` lexicográfico. É ranking, sem probabilidades artificiais, e não usa o antigo grid retrospectivo.

Modelo: probabilidade decrescente, empate exato por ID lexicográfico. Selecionar até três favoritos por GP somente por esses critérios. Registrar todos os grupos empatados, inclusive posições ausentes de mesma prioridade. Grupo com início zero-based inclusivo `i` e fim exclusivo `j` atravessa a fronteira exatamente quando `i < 3 < j`. Manter a correção revisada na etapa 4; não alterar participantes/favoritos após olhar os alvos.

## Métricas e denominadores — mesmas definições v1

Para modelo e constante, usar o mesmo conjunto de elegíveis com alvo conhecido:

- Log loss binária, classes explícitas `[0,1]`.
- Brier: média de `(p-y)^2`.
- Calibração descritiva em dez faixas uniformes: `[0,0.1)`, ..., `[0.9,1]`; contagem, média prevista e frequência observada. Faixa vazia tem contagem zero e médias indefinidas, não frequência zero. Gráfico: x=média prevista, y=frequência observada, sem deslocamento artificial por método.

Para avaliar ambos os rankings no mesmo conjunto de GPs, exigir simultaneamente: ao menos três elegíveis; todos os participantes preparados do GP elegíveis; todos com alvo conhecido; exatamente três positivos. GPs incompletos permanecem no relatório com motivos e pontuação indefinida, nunca zero artificial. Isso não altera quem recebeu previsão ou foi escolhido como favorito.

Informar média de integrantes corretos (0–3), distribuição 0/1/2/3 e proporção dos três integrantes corretos, sem exigir ordem. Sem GPs avaliáveis, média e proporção são indefinidas. Métricas probabilísticas individuais podem permanecer válidas em um GP sem ranking avaliável. Informar denominadores individuais e por GP, exclusões, ambiguidades, alvos desconhecidos e listas de GPs excluídos.

## Comparação, entrega e estado posterior

Comparar descritivamente com as métricas publicadas de 2024, com denominadores separados. São temporadas diferentes; não afirmar significância estatística, superioridade futura ou causalidade. Registrar derrotas para qualquer referência sem tentar melhorar o v1. Um Brier menor não prova isoladamente calibração melhor.

Entregar script separado, previsões por piloto, cobertura por piloto e GP, avaliações por GP, métricas, calibração CSV/SVG, comparação descritiva, relatório em português e manifesto de hashes. Destino novo: `reports/avaliacao_final_v1/`; proteger contra sobrescrita divergente, inclusive em falha parcial. Não modificar `models/modelo_v1/` ou `reports/modelo_v1/`.

A execução real e suas verificações devem provar ausência de ajuste e preservação dos bytes. Testes novos usam dados simulados claramente identificados para casos de fronteira; a conferência real usa somente a fonte autorizada, sem rede. Não executar o treinador como parte da reprodução final.

Após a avaliação real, registrar explicitamente: **2025 passou de reservado a avaliado para o modelo v1; não poderá ser descrito como intocado em experimentos posteriores.** Este plano e os documentos anteriores conservam seu contexto histórico. Atualizar o estado corrente no README e no contexto do projeto, sem reescrever resultados históricos. Sem dashboard nesta tarefa.
