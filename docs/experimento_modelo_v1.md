# Experimento modelo v1 — plano fixado antes do treinamento

Created by: MBPaschoal
Status: protocolo fixado
Type: experiment protocol

## Pergunta e períodos

Estimar a probabilidade individual de um piloto terminar no pódio de um GP principal. O alvo é `podio` conhecido, binário; resultado desconhecido permanece desconhecido, nunca vira zero. Não se prevê a ordem dos três integrantes.

- Treino: 2021–2023, exclusivamente `data/preparado/treino.csv`.
- Validação: 2024, exclusivamente `data/preparado/validacao.csv`. Já explorada nas etapas anteriores, não é teste intocado.
- Teste final reservado: 2025. **Proibido abrir, avaliar ou usar para decisões nesta etapa**, inclusive por intermédio da base histórica completa, arquivos globais de entradas/alvos ou regeneração da etapa 3.
- Metadados de colunas: somente `data/preparado/colunas.json`.
- Não consultar Jolpica nem executar os coletores/preparadores históricos. As janelas pré-calculadas permanecem como recebidas.

Este protocolo é escrito antes do primeiro ajuste. Seu hash será registrado nos metadados do experimento. Não haverá mudanças de entradas, elegibilidade, hiperparâmetros ou faixas de calibração para favorecer o resultado observado em 2024. Correções de bugs deverão ser identificadas, testadas e documentadas, não confundidas com novos experimentos.

## População e elegibilidade pré-corrida

A base preparada é uma união externa retrospectiva, não uma lista de inscritos congelada no corte. Para este primeiro experimento, um piloto é elegível para receber previsão quando:

1. Possui registro na classificação (`classificacao_ausente=0`). Isso identifica sua presença por uma fonte admitida antes da corrida, sem usar a existência de resultado posterior.
2. Há referência temporal (`referencia_temporal_ausente=0` e limite inferior preenchido), conforme o protocolo da etapa 3.

Não excluir por resultado, posição final, pontos, grid retrospectivo, abandono, DNS ou desclassificação. Não usar `resultado_ausente` para selecionar previsões. A equipe do resultado atual nunca substitui a equipe pré-corrida.

- **Classificação completamente ausente:** linha preservada na auditoria de cobertura, mas não recebe previsão v1, por falta de participante identificado no corte. Informar motivo.
- **Registro de classificação presente com posição ausente:** continua elegível. A posição será imputada pela mediana do treino no pipeline. A referência de ranking coloca posições ausentes depois das conhecidas.
- **Posição repetida/ambígua:** preservar o valor e seu indicador; não excluir pilotos, inferir desempate esportivo ou usar `Results.grid`.
- **Estreantes/pouco histórico:** continuam elegíveis. Médias ausentes serão imputadas e os contadores/indicadores preservados. Ausência não significa desempenho zero nem necessariamente estreia real na F1.

Elegibilidade para prever é separada da disponibilidade de alvo para treinar/avaliar. O pipeline será ajustado apenas nos elegíveis do treino com alvo conhecido. Todos os elegíveis de validação recebem probabilidades, inclusive se o alvo for desconhecido. Métricas probabilísticas usam somente previsões com alvo conhecido e explicitam o denominador. Registrar exclusões e faltas em tabela por piloto/GP; não eliminar linhas silenciosamente.

## Entradas autorizadas e isolamento

Lista explícita, na ordem abaixo, validada contra `colunas.json`:

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

Alguns indicadores serão constantes na população elegível; serão mantidos com coeficiente zero quando não há variação, sem selecionar variáveis pelo desempenho. As chaves, nomes, equipe, datas, divisão, alvo e auditoria não entram automaticamente na matriz. Recusar explicitamente qualquer lista de entradas fora dessa allowlist ou sobreposta às colunas proibidas do esquema. Não inferir entradas por tipo numérico nem por exclusão de algumas colunas.

Booleanos CSV `True`/`False` e `0`/`1` serão convertidos explicitamente. Células vazias numéricas viram NaN apenas na matriz de trabalho. Recusar valores não numéricos inválidos/infinito, alvo diferente de vazio/0/1, chaves duplicadas e períodos incoerentes. Não alterar a base original.

## Modelo fixado

Python/scikit-learn, com versões em `requirements_modelo_v1.txt`; somente ambiente virtual do projeto.

Pipeline:

1. `SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=False)`: medianas aprendidas somente no treino elegível e rotulado; entradas inteiramente vazias no treino usam a regra de zero documentada pelo imputador. Indicadores de ausência já são entradas explícitas.
2. `StandardScaler`: médias e desvios aprendidos somente nas linhas de treino após imputação. Uma entrada constante não produz divisão por zero.
3. `LogisticRegression(C=1.0, penalty='l2', solver='lbfgs', max_iter=2000, tol=1e-4, class_weight=None, random_state=42)`.

A semente é explícita por reprodução; `lbfgs` não usa sorteio de amostras. Sem busca de hiperparâmetros, balanceamento automático, calibração aprendida ou ajuste com validação. Tratar falta de convergência como erro, não aceitar silenciosamente um ajuste incompleto. Limitar threads nativas a uma durante o ajuste e documentar que reprodução numérica entre plataformas/BLAS pode variar nos últimos dígitos.

Salvar o pipeline ajustado e metadados de versões, entradas, parâmetros, mediana, escala, coeficientes, intercepto e hashes **apenas dos arquivos permitidos**. Não ler comprovantes mistos ou arquivos de 2025 para construir o registro. Artefatos pickle/joblib só podem ser carregados se produzidos localmente e confiáveis; não são seguros para arquivos arbitrários recebidos de terceiros.

## Referências e desempates definidos antes da avaliação

A. Probabilidade constante = soma dos alvos positivos / número de alvos conhecidos nas mesmas linhas elegíveis e rotuladas de treino utilizadas pelo modelo. Aplicar essa constante a todos os elegíveis de validação. Não estimar a taxa em 2024.

B. Ranking da classificação: ordenar os elegíveis pela posição numérica da classificação, posições ausentes ao final; desempatar pelo `piloto_id` em ordem lexicográfica. Não usar resultado, pontos ou status. É uma convenção computacional reproduzível, **não** um desempate esportivo. Registrar GPs e grupos empatados e se o empate atravessa a fronteira de seleção do top 3. Nenhuma probabilidade é atribuída a essa referência.

Ranking do modelo: probabilidade decrescente; empates exatos por `piloto_id` lexicográfico, registrados pelo mesmo procedimento. A escolha dos favoritos deve ser feita antes de ler os alvos para calcular acertos. Os dois rankings usam os mesmos participantes elegíveis de cada corrida.

A referência antiga do grid retrospectivo **não** é comparador deste experimento.

## Métricas e cobertura de validação

### Probabilidades

Para modelo e constante, nas mesmas linhas elegíveis de 2024 com alvo conhecido:

- Log loss binária com classes explícitas `[0,1]` (menor é melhor).
- Brier score binário, média de `(probabilidade - alvo)^2` (menor é melhor).
- Calibração descritiva em **dez faixas uniformes fixas**: [0,0.1), ..., [0.9,1]. Mostrar contagem, média prevista e frequência observada por faixa; faixas vazias sem ponto, não com frequência zero. Mostrar gráfico de confiabilidade e histograma/contagens para ambos.

Essas métricas combinam aspectos de discriminação e calibração; um Brier menor não prova isoladamente calibração melhor. Uma curva nessa amostra pequena não certifica probabilidades calibradas para outras temporadas.

### Top 3

Selecionar top 3 dos rankings apenas por entradas/probabilidades. Para pontuar os rankings no conjunto comum de GPs, exigir:

- Pelo menos três elegíveis.
- Todos os participantes da união preparada daquele GP elegíveis — evita apresentar avaliação parcial como se abrangesse todo o GP.
- Alvos conhecidos de todos esses participantes e exatamente três positivos.

A condição de avaliação não altera quem recebeu previsão nem os favoritos selecionados. GPs com comparação incompleta ficam explicitamente não avaliáveis; não recebem acerto zero artificial. Ambos os métodos usam exatamente os mesmos GPs avaliáveis. Reportar denominador de GPs e cobertura sobre todas as corridas presentes em 2024.

Métricas: média de integrantes corretos de 0 a 3, distribuição 0/1/2/3 com contagens e proporção com os três integrantes corretos, ignorando ordem. Sem GPs avaliáveis, valores indefinidos (n/d), nunca zero artificial. Relacionar motivos de exclusão por GP; probabilidades de linhas com alvo conhecido ainda podem ser avaliadas mesmo quando o GP não permite comparação completa de ranking.

Um classificador binário independente não impõe que as probabilidades de um GP somem três. Não renormalizar para forçar essa soma. Relatar essa limitação, sem interpretar a soma como previsão de quantidade de vagas.

## Reprodução, testes e comunicação

Comando do experimento: `./.venv/bin/python treinar_modelo_v1.py`. Instalação única: `./.venv/bin/python -m pip install -r requirements_modelo_v1.txt`. Suíte completa: `./.venv/bin/python -m unittest discover -s tests -v`.

Testes devem recusar colunas proibidas; demonstrar ajuste dos três estágios somente no treino e invariância dos parâmetros ao alterar validação; separar previsão/seleção dos alvos; preservar alvo desconhecido; bloquear leitura do teste real de 2025/bases mistas e acesso à rede; reproduzir previsões/métricas por segunda execução; preservar saídas existentes diferentes em vez de sobrescrever.

Os relatórios devem incluir coeficientes em unidades padronizadas, intercepto e explicação sem causalidade: associação condicionada às demais entradas e ao treino, afetada por correlação/regularização, não efeito de mudar artificialmente uma variável. Não interpretar como importância causal. Reconhecer pequeno número de temporadas, dependência entre pilotos do mesmo GP, validação 2024 já explorada, mudanças esportivas e revisões retrospectivas das fontes. Não afirmar generalização para 2025 nem ocultar derrota para uma referência.

## Referências técnicas primárias

- Pipeline e vazamento: https://scikit-learn.org/1.6/common_pitfalls.html
- Imputação: https://scikit-learn.org/1.6/modules/generated/sklearn.impute.SimpleImputer.html
- Normalização: https://scikit-learn.org/1.6/modules/generated/sklearn.preprocessing.StandardScaler.html
- Regressão: https://scikit-learn.org/1.6/modules/generated/sklearn.linear_model.LogisticRegression.html
- Métricas e calibração: https://scikit-learn.org/1.6/modules/calibration.html
- Persistência e segurança: https://scikit-learn.org/1.6/model_persistence.html

Fontes e limitações esportivas: [protocolo temporal](protocolo_temporal.md) e [dicionário da base](dicionario_variaveis.md). Dados públicos Jolpica-F1 sob CC BY-NC-SA 4.0; nenhuma nova consulta nesta etapa.
