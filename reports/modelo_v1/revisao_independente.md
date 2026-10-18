# Revisão independente — etapa 4

## Parecer final

**Aprovado em 18 de outubro de 2026, sem problemas remanescentes no escopo revisado.** A aprovação final complementa uma revisão completa inicial que encontrou um bloqueio P2; esse problema foi corrigido e verificado novamente pelo revisor. Aprovação técnica não significa comprovação de desempenho futuro.

- **Implementação e correções:** provedor `openai-codex`, modelo **`gpt-5.6-terra`**.
- **Revisão independente, nas duas rodadas:** provedor `openai-codex`, modelo **`gpt-6-astra`**.
- **Sessão do revisor:** `20261018_031722_614ca3`.
- A rota efetiva foi conferida em `session_model_usage`, na tarefa principal da sessão: `billing_provider=openai-codex`, `model=gpt-6-astra`, 20 chamadas acumuladas após as duas rodadas. Não se inferiu identidade pela resposta textual do agente.
- O revisor não alterou arquivos do projeto. Suas contraprovas adicionais foram executadas em memória ou em diretórios temporários.
- Não houve indisponibilidade do modelo forte nesta etapa nem necessidade de revisor alternativo. A limitação de uso da revisão da etapa 3 é um fato separado, não o resultado desta revisão.
- `auxiliary.review` permaneceu em `auto`. O Astra foi escolhido explicitamente para estas execuções, sem alterar a configuração persistente do Hermes. Isso não configura automaticamente futuras chamadas de `/review`.

Os dois pareceres completos, com evidências, arquivos e linhas, estão em [revisao_independente.json](revisao_independente.json). Referências `scratch/` nesse registro identificam a auditoria local executada; não são scripts distribuídos como parte do projeto.

## Ordem do trabalho

1. O plano do experimento foi escrito antes do primeiro ajuste. Seu SHA-256 permaneceu `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569`.
2. Implementação, documentação, artefatos, testes e reprodução foram concluídos antes de iniciar a revisão independente.
3. A primeira revisão Astra encontrou um P2 no relato de desempates, não nos valores atuais das métricas.
4. O modelo médio corrigiu o bloqueio com testes que falhavam antes da correção.
5. A segunda revisão Astra repetiu as contraprovas, a suíte e a reprodução e aprovou o conjunto.
6. Estes registros de revisão foram acrescentados após o parecer. Não houve mudança posterior na metodologia ou nos artefatos do experimento.

## Problema encontrado e correção

**P2 — relato incorreto da influência do desempate na fronteira do top 3.**

Arquivo original: `treinar_modelo_v1.py`, função `_resumo_empates`, aproximadamente linha 325 na primeira revisão. Correção atual: linhas 306–336. Regressões publicadas: [tests/test_desempates_modelo_v1.py](../../tests/test_desempates_modelo_v1.py).

| Caso simulado, em ordem de prioridade | Comportamento anterior | Comportamento corrigido |
|---|---|---|
| Posições `[1, 2, 2, 4]` | Informava impacto na composição do top 3, embora os dois empatados fossem selecionados. | Informa empate, mas `impacto_fronteira=nao`. |
| Posições `[1, 2, 3, 3]` | O desempate realmente separava o terceiro e o quarto candidatos. | Mantém `impacto_fronteira=sim`. |
| Posições `[1, 2, ausente, ausente]` | Não relatava o grupo de posições ausentes. | Agrupa a mesma prioridade como `posicao=ausente` e informa o impacto na fronteira. |

A condição de cruzamento passou a usar `inicio < 3 < fim`, com fim exclusivo. Posições ausentes com a mesma prioridade são agrupadas. A escolha continua determinística por ID quando necessário; isso **não inventa um desempate esportivo**. Nos três casos, os favoritos permaneceram `a,b,c`.

Cinco regressões cobrem os casos acima, ausentes fora do top 3 e invariância ao alterar alvos/auditoria. O revisor reconstruiu a função anterior em memória: **5 testes, 3 falhas**. Na função corrigida: **5 testes, zero falhas**. Não mudou a ordenação ou a seleção de favoritos. Os dez artefatos reais de 2024 mantiveram os mesmos bytes.

## Outras correções verificadas antes da revisão

- **Compatibilidade numérica:** uma contraprova inteiramente simulada reproduziu avisos de multiplicação matricial com NumPy 2.0.2 nesta máquina. A versão fixada 1.26.4 não reproduziu os avisos. Não se atribuiu causa interna específica ao BLAS sem prova. A rotina transforma avisos numéricos relevantes em erro em vez de escondê-los.
- **Geometria da calibração:** a coordenada horizontal do gráfico passou a representar a média prevista real de cada faixa, sem deslocamentos por método; a vertical representa a frequência observada. Regressões sintéticas verificam as coordenadas e as faixas vazias. A revisão independente conferiu os 11 pontos e as 20 barras do SVG, além do CSV de origem.

Essas correções não escolheram variáveis ou hiperparâmetros para melhorar os resultados.

## Verificações e evidências

| Item solicitado | Resultado e evidência principal |
|---|---|
| Elegibilidade sem seleção pelo desfecho | Conferidas as regras pré-corrida, a cobertura e a invariância ao alterar alvos e auditoria; `treinar_modelo_v1.py`, validação e funções de previsão/ranking. |
| Transformações somente no treino | Ajuste independente reproduziu medianas, médias, escalas, coeficientes e intercepto do pipeline salvo; `criar_pipeline` e `ajustar`, linhas 259–290, e metadados. |
| Entradas explícitas | Lista fixa de 15 colunas, com validação dos papéis; `ENTRADAS_AUTORIZADAS`, linha 32, e testes de rejeição. |
| Teste real de 2025 fechado | Guardas de abertura de arquivos e de rede durante execução real e suíte. Somente `treino.csv`, `validacao.csv` e `colunas.json` foram abertos como fontes na reprodução do experimento. Nenhum dado reservado foi aberto, inclusive para hashes. |
| Referências justas | Constante calculada no treino elegível; classificação tratada somente como ranking. Modelo e referência usam os mesmos participantes e 24 GPs avaliáveis. Não se usa a referência antiga de grid retrospectivo. |
| Métricas e ranking | Recalculadas independentemente as 479 probabilidades, log loss, Brier, favoritos e acertos dos 24 GPs; `avaliar`, linha 409, CSVs e JSON. |
| Cobertura e alvos desconhecidos | Conferidas as 1.320 linhas de treino e os denominadores; alvos desconhecidos não são convertidos em zero. Casos sintéticos cobrem GPs incompletos e ausência de classificação. |
| Consistência das entregas | Conferidos pipeline, previsões, métricas, coeficientes, calibração, gráfico e conclusões. |
| Reprodução | Duas execuções reais protegidas geraram os mesmos dez artefatos, byte a byte, preservando as fontes; uma reprodução independente com o código corrigido também coincidiu. |
| Testes | **100 executados, zero falhas, zero erros**, incluindo as cinco regressões da correção. A suíte foi repetida pelo agente principal e pelo revisor. `pip check` também passou. |

Os testes históricos que usam o ano 2025 geram dados **simulados em pastas temporárias**; não leem o conjunto real reservado. As guardas bloqueariam esse acesso.

## Resultados da validação de 2024

Treino: **1.319 linhas usadas no ajuste**, das 1.320 disponíveis. A única exclusão de elegibilidade foi `mick_schumacher`, Mônaco 2021, por classificação ausente; não por resultado final. Validação: **479 participantes, 24 GPs, zero alvos desconhecidos**; os 24 GPs foram avaliáveis no ranking comum. As oito linhas com posição de classificação ambígua foram preservadas e sinalizadas.

### Probabilidades — menor é melhor

| Método | Log loss | Brier score | Denominador |
|---|---:|---:|---:|
| Regressão logística | 0,229556 | 0,070918 | 479 participantes |
| Constante do treino | 0,423252 | 0,127719 | 479 participantes |

### Ranking — integrantes corretos, sem exigir ordem

| Método | Média de acertos | 0 acertos | 1 acerto | 2 acertos | 3 acertos | Pódio completo |
|---|---:|---:|---:|---:|---:|---:|
| Modelo | 1,9583 | 1 | 5 | 12 | 6 | 6/24 = 25,00% |
| Referência de classificação | 1,8750 | 1 | 5 | 14 | 4 | 4/24 = 16,67% |

A regressão foi melhor que a constante nas duas métricas probabilísticas e teve pequena vantagem sobre a referência de classificação neste conjunto. Isso não prova superioridade futura ou significância estatística. A referência de classificação não recebeu probabilidades artificiais. Não há comparação direta com o antigo grid retrospectivo.

## Reprodução pública

Na raiz do projeto, com o ambiente virtual preparado:

```bash
./.venv/bin/python -m pip install -r requirements_modelo_v1.txt
./.venv/bin/python treinar_modelo_v1.py
./.venv/bin/python -m unittest discover -s tests -v
```

O primeiro script lê apenas treino, validação e esquema. Não execute novamente os coletores ou o preparador histórico para reproduzir esta etapa. Saídas existentes divergentes são preservadas, não sobrescritas automaticamente. O arquivo joblib deve ser carregado apenas se local e confiável.

## Limites do parecer

- Validação de 2024 já explorada: não é um teste intocado.
- Fontes retrospectivas não comprovam, de forma imutável, o que estava publicado em cada corte histórico.
- Probabilidades individuais não foram forçadas a somar três por GP; o modelo não é um sistema conjunto de probabilidades de pódio.
- Não foi feita calibração posterior, busca extensa de hiperparâmetros ou avaliação de 2025.
- Os bytes foram reproduzidos nesta pilha de versões e máquina; outra plataforma pode alterar os últimos dígitos numéricos.
- A aprovação cobre a etapa 4 e suas correções, não um dashboard, operação em produção ou desempenho em temporadas futuras.
