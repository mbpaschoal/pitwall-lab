# Dicionário das variáveis — etapa 3

## Unidade de análise e arquivos

Uma linha representa **temporada + rodada + piloto_id**. Os IDs da Jolpica são usados nas junções; nomes são apenas rótulos. A população é a **união externa** dos pilotos encontrados na classificação e nos resultados da corrida principal. Assim, ninguém desaparece por falta de correspondência. Isso não reconstrói uma lista de inscritos congelada no instante da previsão; pilotos conhecidos apenas pelo resultado são explicitamente sinalizados.

- `data/preparado/identificacao.csv`: chaves, rótulos, equipe e metadados temporais.
- `data/preparado/entradas.csv`: chaves e **somente** variáveis permitidas. As chaves são para junção, não entram automaticamente no modelo.
- `data/preparado/alvos.csv`: chaves e alvo; alvo vazio significa desconhecido, não zero.
- `data/preparado/auditoria_resultados.csv`: chaves e desfechos da corrida atual; **proibidos como entradas**.
- `data/preparado/base_historica.csv`: visão completa para conferência, não para fornecer todas as colunas a um modelo.
- `data/preparado/colunas.json`: lista explícita de chaves, identificação, entradas e alvo, incluindo auditoria proibida como entrada.
- `data/preparado/auditoria_janelas.json`: IDs de todas as corridas que contribuíram para cada janela e datas de liberação pelo protocolo. Essas listas são auditoria, não entradas.
- `data/preparado/divisoes.csv`: uma linha por corrida com sua divisão; `treino.csv`, `validacao.csv` e `teste_final_reservado.csv` contêm as respectivas linhas completas.
- `data/preparado/verificacao.json`: contagens e hashes das fontes e saídas. Deve ser produzido por último.

## Identificação — não são variáveis numéricas automáticas

| Campo | Definição |
|---|---|
| `temporada`, `rodada`, `piloto_id` | Chave estável da linha, conforme fonte. |
| `corrida`, `data_corrida`, `circuito_id`, `piloto` | Nome do evento, data UTC da fonte, ID do circuito e rótulo do piloto. |
| `equipe_id` | Equipe para identificação: preferimos classificação; só na ausência dela, resultado, sem usá-lo para calcular a entrada da equipe. |
| `equipe_id_entrada` | Equipe encontrada **na classificação**. Sem classificação, fica vazio: não usamos a equipe do resultado atual como substituta. |
| `divisao` | `treino` (2021–2023), `validacao` (2024) ou `teste_final_reservado` (2025). |
| `sessao_referencia` | `Qualifying`, ou `Sprint_2021_2022` nos eventos em que a Sprint define a ordem-base do GP. |
| `limite_inferior_referencia_utc` | Início da sessão no calendário; se só houver data, ou `time` estiver vazio, início daquele dia UTC. Horário não vazio precisa ser UTC com `Z`; inválido bloqueia a preparação. **Não é o horário de encerramento da sessão.** |
| `fim_sessao_referencia_utc` | Vazio: esta API não fornece um horário de encerramento comprovado. Não inventamos duração. |
| `precisao_referencia` | `inicio_sessao`, `inicio_dia` ou `desconhecida`. |
| `classificacao_nao_define_grid_gp` | Indica os fins de semana Sprint de 2021–2022; o resultado de `qualifying/` é da tomada de tempos anterior à Sprint, não a ordem final do GP. |

## Entradas e fórmulas

Para um piloto na corrida atual, selecione somente GPs anteriores liberados **antes do limite conservador** descrito no [protocolo temporal](protocolo_temporal.md). Ordene por data/hora da corrida, com temporada/rodada para desempate. Nunca use a própria corrida, mesmo se uma data estiver errada. A data de liberação é uma regra do estudo, não comprovação de publicação histórica.

Seja $H_d$ o conjunto ordenado das **até cinco participações anteriores mais recentes do piloto** e $n_d=|H_d|$. Participação significa **registro no endpoint de resultados**, não necessariamente largada efetiva. Se ele não tiver registro num GP, esse GP não ocupa uma vaga em sua janela.

Para a equipe, selecione os **até cinco GPs anteriores mais recentes em que seu constructorId aparece nos resultados**. Seja $G_e$ esse conjunto, $m_e=|G_e|$ e $P_e$ a união dos registros de pilotos dessa equipe nesses eventos. Seja $n_e=|P_e|$. É uma janela de cinco eventos da equipe, não de cinco linhas de pilotos.

| Entrada | Definição |
|---|---|
| `posicao_classificacao` | `QualifyingResults.position`, inteiro positivo quando informado. **Não** usa `Results.grid`. Não usamos Q1/Q2/Q3 para inventar posição ausente. Quando a fonte repete uma posição, o valor original continua aqui: ele não é transformado em uma ordem única. |
| `posicao_classificacao_repetida` | 1 quando a mesma `QualifyingResults.position` positiva aparece para dois ou mais pilotos naquela corrida; 0 nos demais casos, inclusive posição ausente. Sinaliza que a posição preservada é ambígua. Não inferimos desempate, não reordenamos pilotos e não substituímos pelo `Results.grid`. |
| `classificacao_ausente` | 1 quando não há registro daquele piloto em `qualifying/`; 0 quando há. |
| `posicao_classificacao_ausente` | 1 se posição ausente, mesmo que exista registro de classificação. Distingue sessão presente de posição conhecida. |
| `media_posicao_final_5` | $\sum_{r\in H_d}position_r/n_d$. Vazia se $n_d=0$. Menor média representa posições numéricas melhores, não prova de que terminou todas as provas. |
| `taxa_podios_5` | $\sum_{r\in H_d}1(1\le position_r\le3)/n_d$. Vazia se $n_d=0$. Frequência observada recente, não probabilidade calibrada. |
| `n_posicoes_5` | $n_d$, denominador da média de posições (0 a 5). |
| `n_podios_5` | $n_d$, denominador da taxa de pódios (0 a 5). São iguais porque não removemos status. |
| `media_pontos_equipe_5` | $\sum_{p\in P_e}points_p/n_e$. Pontos por **registro de piloto**, não pontos totais por GP. Vazia se $n_e=0$. Não somamos pontos das sprints. |
| `n_corridas_equipe_5` | $m_e$, quantidade de eventos na janela da equipe (0 a 5). |
| `n_participacoes_equipe_5` | $n_e$, denominador real da média de pontos. Não presumimos dois pilotos em cada evento. |
| `historico_piloto_insuficiente` | 1 se $n_d<5$. Pouco histórico não é preenchido com dados futuros. |
| `historico_equipe_insuficiente` | 1 se $m_e<5$. |
| `equipe_pre_corrida_ausente` | 1 se `equipe_id_entrada` não estiver disponível; nesse caso a média de pontos fica vazia e os dois contadores da equipe são zero. |
| `referencia_temporal_ausente` | 1 quando nem a data da sessão de referência consta do calendário. A linha é preservada, mas não se calcula histórico para ela e ela não pode ser tratada como previsão temporal validada sem investigação posterior. |

Contadores zero significam ausência de observações, **não desempenho ruim**. Médias/taxas com uma a quatro observações usam apenas as observações disponíveis e informam o denominador. Médias não são arredondadas para calcular outras variáveis; o CSV conserva a representação numérica do Python.

## Alvo e auditoria — separação obrigatória

| Campo | Papel e definição |
|---|---|
| `podio` | **Alvo**: 1 se a posição final numérica da corrida principal está entre 1 e 3; 0 nos demais resultados conhecidos. Vazio para participante da classificação sem resultado na API. |
| `posicao_final` | Auditoria: posição numérica atual da fonte. Proibida como entrada. |
| `pontos` | Auditoria: pontos atuais da corrida principal. Proibidos como entrada. |
| `status` | Auditoria: situação final original, incluindo abandonos, não largadas e desclassificações. Proibido como entrada. |
| `grid_resultado` | Auditoria: grid retrospectivo dos resultados, inclusive zero; **nunca** substitui a posição da classificação. |
| `resultado_ausente` | Auditoria da junção: 1 se não há resultado para o piloto. **Não é entrada**, pois pode depender de informação posterior ao corte. |

`DNS`, `Did not start`, abandonos e desclassificações com registro de resultado permanecem no histórico e no alvo conforme a posição numérica. Isso evita excluir seletivamente maus desfechos, mas a média de posições também incorpora as posições administrativas atribuídas pela fonte. Não equivalem a desempenho de ritmo nem a posições em que o piloto cruzou a linha.

## Mudanças de equipe, estreantes e início da amostra

- Histórico do piloto segue `driverId` mesmo que ele mude de equipe.
- Histórico da equipe segue o **constructorId literal**. Mudança de nome com o mesmo ID não o apaga; IDs diferentes não são unidos manualmente, ainda que representem continuidade esportiva. Essa escolha pode reiniciar o histórico de uma equipe rebatizada.
- Sem observações desde 2021 não significa necessariamente estreia na F1: pode ser um veterano no início da amostra ou retornando de uma ausência. Não coletamos 2020 para preencher artificialmente o começo.
- Posição ausente, equipe ausente e pouco histórico têm indicadores próprios. Nenhuma imputação, normalização ou seleção de variáveis é ajustada nesta etapa.

## Atribuição e limites

Dados públicos Jolpica-F1, CC BY-NC-SA 4.0. Transformações: junção por identificadores, janelas temporais, indicadores de ausência e divisão cronológica. As fontes históricas podem conter revisões posteriores, inclusive desclassificações ou correções de posição. Não existe garantia de disponibilidade histórica só porque a resposta foi obtida e datada hoje.

Fontes de contrato: documentação Jolpica em `docs/README.md`, `docs/endpoints/qualifying.md`, `docs/endpoints/results.md` e `docs/endpoints/races.md` no repositório oficial `jolpica/jolpica-f1`. Links completos no protocolo temporal e no README.
