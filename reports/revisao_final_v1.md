# Parecer e verificação — avaliação final congelada do v1

**Parecer final: aprovado, sem problemas identificados no escopo revisado.**

## Implementação e revisão efetivamente utilizadas

- Implementação: **`openai-codex / gpt-5.6-terra`**, sessão `20261018_034603_2c67cc`.
- Revisão independente: **`openai-codex / gpt-6-astra`**, sessão `20261018_040318_30a6a5`, concluída com parecer final.
- O orquestrador consultou `session_model_usage` após a conclusão e confirmou provedor/modelo da tarefa principal, com 13 chamadas na sessão do revisor. O revisor não havia feito essa consulta por conta própria; essa limitação de seu parecer original foi resolvida pela conferência do orquestrador, não por autodescrição.
- Nenhum revisor alternativo foi necessário. A configuração persistente dos modelos do Hermes não foi alterada. O revisor não modificou arquivos do projeto.

O [parecer original completo](revisao_final_v1.json) inclui arquivos, linhas, comandos, contraprovas e limitações. Referências `scratch/` são registros internos de execução; não prometem scripts temporários disponíveis no clone.

## Ordem da avaliação

1. Documentos e metadados lidos; 100 testes antigos passaram com o teste real ainda bloqueado.
2. [Plano final](../docs/avaliacao_final_v1.md) registrado, sem conhecer as métricas de 2025. Hash confirmado em registro local às **06:46:20 UTC de 18/10/2026**.
3. Avaliador separado e nove novos testes implementados; os 109 testes passaram antes de abrir o teste real.
4. Primeira abertura registrada do teste real às **07:00:01 UTC de 18/10/2026**, seguida de duas repetições idênticas do mesmo v1, sem seleção de versões.
5. Oráculo separado e revisão independente conferiram as probabilidades e os resultados sem ajustar modelos ou abrir treino/validação.

A [verificação das execuções originais](verificacao_final_v1.json) preserva horários, hashes, fontes abertas e contagens. Esses registros são evidências locais do fluxo executado, não prova externa imutável de inexistência de qualquer acesso fora dele.

## Garantias verificadas

- Só teste e esquema foram abertos como fontes de dados durante as execuções finais; nenhuma base mista, dado de 2026, coletor ou API Jolpica foi usado.
- **Zero chamadas de ajuste** na avaliação real. Guardas bloquearam `fit`, `fit_transform` e `partial_fit` nos estágios aplicáveis. Os testes antigos que treinam usam exemplos simulados, não um retreino do v1 real.
- **16 arquivos congelados** permaneceram idênticos nas execuções protegidas, incluindo modelo, metadados, planos, treinador, dependências e relatórios anteriores. Três objetos joblib carregados também mantiveram o estado em memória.
- **11 artefatos** reproduzidos byte a byte nas duas pastas temporárias e no destino final. O revisor repetiu duas execuções adicionais, também idênticas.
- Previsões e favoritos são produzidos sem alvos/auditoria; os alvos são extraídos e relacionados depois, por chave. Alvo desconhecido não vira zero.
- Validação de período/divisão/chaves/valores, seleção das 15 entradas e desempates v1 foram conferidos, inclusive com contraprovas próprias do revisor.
- Probabilidades reconstruídas diretamente dos parâmetros salvos, sem `fit` ou `predict_proba`, diferiram das publicadas em no máximo `3.3306690738754696e-16`.
- Métricas, calibração, rankings, cobertura e todos os hashes do manifesto foram recalculados. Foram conferidos os onze pontos não vazios do gráfico de 2025.
- **109 testes, zero falhas**. Contraprova de falha de escrita confirmou ausência de publicação parcial; destino divergente foi recusado sem sobrescrita.

## Resultados e interpretação

### Cobertura antes de falar em desempenho

| Conjunto | Quantidade |
|---|---:|
| Registros preparados — um piloto em um GP | 480 |
| Elegíveis com previsão | 479 |
| Elegíveis com previsão e alvo conhecido — métricas probabilísticas | 478 |
| GPs presentes | 24 |
| GPs avaliáveis em comum nos rankings | 22 |

- **Espanha, rodada 9:** `stroll` recebeu previsão, mas o alvo está desconhecido. O ranking desse GP não foi pontuado. As demais linhas elegíveis com alvo conhecido continuam nas métricas probabilísticas.
- **São Paulo, rodada 21:** `bortoleto` não tem registro de classificação na base, sendo inelegível pela regra pré-corrida fixada antes do teste. O ranking desse GP não foi pontuado. As outras linhas elegíveis com alvo conhecido continuam nas métricas probabilísticas.
- Essas são características observadas na fonte preparada; não se inventou causa esportiva nem consultou nova fonte para explicar as ausências. Os GPs excluídos ficaram com pontuação indefinida, não zero.

### Probabilidades — menor é melhor

| Método | Log loss, 478 casos | Brier, 478 casos |
|---|---:|---:|
| Modelo congelado | **0,2033** | **0,0585** |
| Constante congelada do treino | 0,4238 | 0,1279 |

As probabilidades do modelo tiveram erros menores que a previsão constante nesse conjunto. Isso não implica que cada faixa esteja bem calibrada nem que as probabilidades sejam confiáveis em outra temporada.

### Ranking — somente os mesmos 22 GPs

| Método | Média de integrantes corretos | GPs com 0 / 1 / 2 / 3 acertos | Pódios completos |
|---|---:|---:|---:|
| Modelo | **2,3182** | 0 / 1 / 13 / 8 | 8/22 — 36,36% |
| Classificação | 2,2727 | 0 / 2 / 12 / 8 | 8/22 — 36,36% |

O modelo identificou **51 integrantes**, contra **50** da referência, mas empatou na quantidade de pódios completos. Por GP, venceu em três, perdeu em dois e empatou em dezessete; as derrotas estão preservadas na avaliação por corrida. A vantagem média é pequena, não prova de significância estatística ou superioridade futura. A referência de classificação é ranking, sem probabilidades inventadas, e não o antigo grid retrospectivo.

### Comparação descritiva com 2024

| Resultado do modelo | 2024 — validação já explorada | 2025 — avaliação final congelada |
|---|---:|---:|
| Casos probabilísticos | 479 | 478 |
| GPs de ranking | 24 | 22 |
| Log loss | 0,2296 | 0,2033 |
| Brier | 0,0709 | 0,0585 |
| Média de integrantes corretos | 1,9583 | 2,3182 |
| Pódios completos | 6/24 — 25,00% | 8/22 — 36,36% |

São temporadas e coberturas diferentes, não grupos intercambiáveis. Os números observados foram melhores em 2025, mas não demonstram que o modelo melhorou — ele permaneceu idêntico — nem que o mesmo ocorrerá futuramente.

## O que fica estabelecido

O v1 pôde ser aplicado a uma temporada posterior ao treino sem reaprender seus parâmetros, seguindo as regras predefinidas e com cobertura explicitada. Este é um resultado de engenharia e uma avaliação retrospectiva, não uma previsão emitida em tempo real. Permanecem as revisões posteriores das fontes, a pequena quantidade de temporadas e a dependência entre pilotos do mesmo GP. As janelas históricas não foram reconstruídas ou reauditadas nesta tarefa.

**2025 está agora avaliado para o modelo v1 e não deve ser apresentado como teste intocado em experimentos posteriores.** Não houve criação de dashboard ou tentativa de melhorar o v1 com base nesses resultados.

## Reprodução

```bash
./.venv/bin/python avaliar_modelo_v1.py
./.venv/bin/python -m unittest discover -s tests -v
```

Usar as versões fixadas em `requirements_modelo_v1.txt`. Não executar treinador, coletores ou preparador para essa reprodução. O [manifesto dos onze artefatos](avaliacao_final_v1/manifesto.json) cobre as fontes e as saídas do avaliador; estes registros de revisão são documentos separados, acrescentados após a conferência.
