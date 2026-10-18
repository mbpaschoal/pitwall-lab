# Revisão independente e verificação de entrega — etapa 3

## Resultado e identidade dos modelos

A revisão alternativa final foi **aprovada, sem problemas apontados**, após as correções descritas abaixo. Essa aprovação refere-se à preparação retrospectiva da base, não a um modelo preditivo ou a previsões historicamente registradas.

O orquestrador conferiu os registros efetivos de uso (`session_model_usage`), e não apenas o modelo solicitado no comando ou uma declaração do agente:

| Papel | Provedor efetivo | Modelo efetivo | Sessão | Resultado |
|---|---|---|---|---|
| Implementação | `openai-codex` | `gpt-5.6-terra` | `20261017_143737_5e623e` | Concluída |
| Revisão inicial | `openai-codex` | `gpt-6-astra` | `20261017_144517_91eb8c` | Interrompida por HTTP 429 antes do veredito |
| Correções | `openai-codex` | `gpt-5.6-terra` | `20261017_151643_ab1bd0` | Concluídas e testadas |
| Revisão alternativa final | `openai-codex` | `gpt-6.1-sol` | `20261017_152757_cf7766` | Aprovada; nenhum problema apontado |

**Não houve aprovação final do Astra.** O limite de uso impediu sua conclusão. A aprovação do Sol é independente e explicitamente alternativa; não deve ser atribuída ao Astra. Os revisores receberam instruções para não alterar arquivos; suas contraprovas foram executadas em diretórios temporários fora do projeto.

## Problemas reproduzidos e correções

As contraprovas escritas durante a revisão parcial Astra foram executadas pelo orquestrador, com dados exclusivamente simulados. Não foram aplicadas alterações manuais aos dados esportivos.

| Prioridade | Local na versão anterior à correção | Evidência | Correção realizada |
|---|---|---|---|
| P2 | `preparar_historico.py:36` | `time=''`, aceito e preservado pelo coletor, produzia uma string como `2023-12-16T` e interrompia a preparação. | Horário vazio equivale a ausente: início UTC do dia como limite inferior e precisão `inicio_dia`, mantendo encerramento desconhecido. Horários preenchidos inválidos ou sem UTC explícito são recusados. |
| P2 | `tests/test_coletar_historico.py:17` | A importação do módulo substituía globalmente `tempfile.tempdir` por um caminho pessoal, ignorando `TMPDIR` e prejudicando outros computadores. | Removida a atribuição global; os temporários respeitam o ambiente do executor. |

As correções estão em `preparar_historico.py`, na função `_inicio_utc` e em `definir_referencia`, e no módulo de testes da coleta. `tests/test_regressoes_astra.py` contém três regressões: horário vazio em sessão normal/Sprint, horário inválido/sem UTC e portabilidade da importação dos módulos de testes. O nome desse arquivo identifica a origem das contraprovas, **não** uma aprovação final Astra.

Os novos testes foram executados falhando antes das correções e passaram depois. README, dicionário e protocolo foram atualizados para refletir o comportamento final.

## Escopo conferido pela revisão alternativa

- Exclusão da corrida atual e dos eventos futuros das janelas históricas; alterações simuladas de resultados atuais/futuros não modificaram as entradas contemporâneas/anteriores.
- Posição da classificação separada do grid retrospectivo; diferença de formato Sprint em 2021–2022; início de sessão não apresentado como encerramento.
- Últimas cinco participações do piloto e últimos cinco GPs da equipe, denominadores reais, ordenação, histórico entre anos e mudanças por identificadores.
- Preservação de DNS, desclassificações e participantes sem correspondência; médias vazias sem histórico e alvo desconhecido sem resultado.
- Junções por identificadores, recusa de chaves duplicadas e sinalização de posições de classificação repetidas, sem desempate inventado.
- Divisão por corrida: 2021–2023 para treino futuro, 2024 como validação já explorada e 2025 como teste reservado.
- Paginação, totais, proveniência e hashes das fontes e saídas.
- Coerência entre código, testes, dicionário, protocolo, README e artefatos gerados.

O revisor relatou recomputação independente das 2.279 linhas e respectivas janelas, e regeneração offline dos 19 artefatos com conteúdo idêntico aos existentes. A conferência final do orquestrador também recalculou as entradas e verificou hashes, sem divergências.

## Testes e preservação

Comando executado na conferência final:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Resultado: **82 testes executados, zero falhas e zero erros**.

A reprodução dos coletores e da preparação foi verificada com:

```bash
./.venv/bin/python coletar_historico.py --temporadas 2021 2022 2023 2024 2025 --somente-cache
./.venv/bin/python preparar_historico.py
```

Resultado: **114 corridas, 2.279 linhas e 2.279 chaves únicas**. Conferidos 120 hashes de fontes e 18 hashes de saídas registrados no comprovante da preparação. Trinta arquivos das etapas anteriores foram comparados com o manifesto inicial e permaneceram idênticos; o README é a atualização documental intencional.

| Divisão | Linhas |
|---|---:|
| Treino 2021–2023 | 1.320 |
| Validação 2024 | 479 |
| Teste final reservado 2025 | 480 |

Em 2025, 479 registros de resultados e 479 de classificação produzem 480 linhas pela união externa dos participantes, não por fabricação de registros. Somente integridade e geração mecânica foram verificadas; não houve treinamento, seleção de variáveis ou análise de desempenho nesse período.

A publicação seleciona somente os arquivos da etapa 3. Ambiente virtual, credenciais e arquivos do cofre de conhecimento ficam fora desta entrega. A verificação estática não encontrou padrões de segredos, chaves privadas, caminhos pessoais ou chamadas perigosas nos arquivos selecionados; isso não equivale a uma garantia absoluta de ausência de qualquer informação sensível.

## Limitações que permanecem

- Os dados consultados hoje podem conter revisões posteriores ao corte histórico. Hashes e horários de coleta identificam a fotografia preservada, mas não comprovam sua disponibilidade naquele momento.
- Liberar um resultado a partir do dia UTC seguinte é uma aproximação administrativa conservadora documentada, não comprovação do encerramento ou da publicação oficial.
- A população por união externa é de auditoria, não uma lista de inscritos capturada no instante da previsão.
- Não houve nova consulta à documentação externa da API durante a revisão final; a revisão verificou as fontes locais preservadas e a implementação.
- Uma futura modelagem ainda exige regras de elegibilidade e transformações ajustadas somente no treino, decisões pela validação e avaliação final preservando 2025.

Consulte o [protocolo temporal](../../docs/protocolo_temporal.md), o [dicionário](../../docs/dicionario_variaveis.md) e o [relatório de qualidade](qualidade.md).
