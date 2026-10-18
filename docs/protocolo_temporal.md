# Protocolo temporal e divisão da avaliação — etapa 3

## O que estamos preparando

Um **estudo retrospectivo** de corridas principais de 2021 a 2025, com variáveis que procuram reproduzir informações anteriores à corrida. Não há modelo treinado, estimativa de desempenho, previsão emitida em tempo real ou dashboard.

O momento conceitual da previsão é **o encerramento da sessão principal que estabelece a ordem-base do grid do GP**, antes de possíveis penalidades posteriores e antes da corrida. Usamos a posição do endpoint `qualifying/`, **não** o grid retrospectivo do endpoint `results/`. A classificação não é necessariamente o grid efetivo.

### Exceção de formato: Sprint em 2021 e 2022

Naqueles anos, nos eventos com `Sprint` no calendário, a tomada de tempos definia o grid da Sprint; a Sprint estabelecia a ordem-base do GP. A partir de 2023, os resultados da Sprint passaram a não definir esse grid.

Assim:

- Normalmente a sessão de referência é `Qualifying`, **na data informada pelo calendário**, seja sexta, sábado ou domingo. Não presumimos dia da semana nem subtraímos um dia da data do GP.
- Em 2021–2022, havendo `Sprint` no calendário, a referência conceitual é o encerramento dessa sessão (`Sprint_2021_2022`). O campo `classificacao_nao_define_grid_gp=1` registra a diferença.
- A variável continua sendo a posição do endpoint de classificação, tomada de tempos anterior à Sprint nesses casos. É uma informação anterior ao corte, mas **não fingimos que ela define diretamente o grid do GP**. Não consultamos resultados de Sprint nem os misturamos aos históricos de corridas principais.
- Não usamos `SprintShootout` ou `SprintQualifying` de 2023 em diante como substitutos da classificação principal do GP.

Essa exceção é necessária para não rotular todos os fins de semana como se tivessem o mesmo formato. A fonte oficial da F1 sobre a mudança de 2023 está ao final.

## Horários: o que sabemos e o que não sabemos

O calendário fornece **início** das sessões, não o horário comprovado de seu encerramento. Não somamos uma duração inventada de uma hora. `fim_sessao_referencia_utc` fica vazio.

Para decidir que resultados anteriores podem entrar nas janelas, adotamos uma regra conservadora reproduzível:

1. `limite_inferior_referencia_utc` é o início UTC registrado da sessão de referência. Se só houver sua data, ou se o campo `time` vier vazio, usamos 00:00 UTC daquele dia como **limite inferior**, não como horário da sessão. Um horário não vazio precisa ser UTC com sufixo `Z` e inválidos interrompem a preparação.
2. Um GP anterior só é liberado para o histórico a partir de **00:00 UTC do dia seguinte à data UTC da corrida**. Isso é uma **regra administrativa deste estudo**, denominada `liberado_pelo_protocolo_utc`; não é o instante de publicação dos resultados nem uma medição de encerramento da corrida.
3. Essa liberação precisa ser menor ou igual ao limite inferior da referência. A própria corrida é sempre excluída. Isso elimina também provas da mesma data da classificação, mesmo que houvessem terminado antes dela. É uma exclusão conservadora, não preenchimento com dados futuros.
4. Sessão datada depois da corrida, ou início da sessão igual/posterior ao início conhecido do GP, provoca erro. Não aceitamos uma referência obviamente posterior ao alvo.
5. Sem data da sessão, a linha permanece, com `referencia_temporal_ausente=1`, médias vazias e contadores zero. Não é legítimo avaliá-la como previsão no corte sem primeiro investigar a data.

As datas dos eventos são as datas UTC registradas na fonte, não datas locais inferidas por cidade. O protocolo assume que um GP anterior constante dos resultados já estava concluído até o dia UTC seguinte; os eventos desta amostra são separados por vários dias. **Não use essa aproximação sem revisão para provas que atravessem dias, sejam adiadas ou ocorram próximas do corte.** A auditoria guarda exatamente quais eventos foram usados. Para uma previsão real futura, deverão ser registrados o encerramento observado e o instante de publicação/obtenção das informações.

Embora o corte conceitual seja ao final da sessão, usar o seu início como limite inferior para os **resultados históricos** evita precisar inventar o horário final. A posição de classificação é admitida conceitualmente no encerramento, não no início. Não apresentamos o CSV como uma previsão emitida no timestamp do limite inferior.

## Limite fundamental das fontes históricas

Jolpica consultada hoje pode incorporar correções, desclassificações e revisões decididas **depois** do corte histórico. O mesmo vale para classificações e resultados de GPs anteriores. Nossos testes demonstram que os cálculos não consultam a corrida atual ou eventos futuros, mas **não certificam que cada versão dos dados já estava publicada no corte histórico**.

O instante UTC de obtenção e o hash das novas respostas identificam a fotografia coletada. Eles **não comprovam disponibilidade histórica**. Caches anteriores sem essa informação ficam com data de obtenção `desconhecida`; não usamos data do arquivo, data do commit ou início desta tarefa como substituto.

Eliminar essa limitação exigiria arquivos versionados publicados no próprio momento histórico ou documentos datados por sessão. Até lá, o estudo deve ser descrito como retrospectivo com controles de ordenação temporal, não como backtest com informação historicamente congelada e comprovada.

## Divisão congelada antes do treinamento

| Divisão | Temporadas | Uso permitido |
|---|---|---|
| Treino | 2021, 2022, 2023 | Futuro ajuste do modelo e dos transformadores. |
| Validação | 2024 | Futuras comparações e decisões de desenvolvimento. **Já explorada na etapa 2; não é teste intocado.** |
| Teste final reservado | 2025 | Nesta etapa: somente integridade, cobertura e geração mecânica das variáveis. Sem medir desempenho, escolher variáveis ou ajustar decisões com os alvos de 2025. |

Todos os pilotos de uma corrida recebem a mesma divisão. Não fazemos embaralhamento aleatório por piloto. `divisoes.csv` torna essa atribuição conferível por temporada/rodada. O histórico pode cruzar anos: a primeira corrida de 2024 pode usar resultados permitidos do final de 2023. Janelas não são reiniciadas artificialmente em janeiro.

### Avaliação sequencial (walk-forward)

Na futura avaliação, em cada corrida:

1. Formar entradas usando apenas resultados liberados antes do corte.
2. Registrar a previsão sem consultar o alvo da corrida.
3. Após o GP, guardar o alvo para avaliação.
4. Seus resultados podem compor as janelas de corridas seguintes, respeitado o corte destas.

Em 2025, usar resultados de um GP de 2025 na janela de um GP posterior é permitido nessa simulação sequencial. Isso **não autoriza reestimar pesos do modelo, imputadores, escalas, seleção de variáveis, hiperparâmetros ou limiares usando o teste**. Para a avaliação final, esses componentes devem estar congelados após treino/validação. O relatório de 2025 nesta etapa só mostra cobertura e contagens de qualidade, nunca acurácia, taxas de acerto de favoritos ou ranking de variáveis.

### Ausências e elegibilidade futura

A base mantém pilotos sem classificação e participantes só da classificação. Sem resultado, o alvo é **desconhecido**, não negativo. Antes de avaliar um modelo futuro, será preciso definir e congelar uma regra de elegibilidade baseada no corte, reportar quantos casos não são avaliáveis e investigar alvos desconhecidos; não fazer uma exclusão silenciosa por conveniência.

A população por união externa é uma escolha de **auditoria**, não uma lista de inscritos capturada no corte. `resultado_ausente` e `equipe_id` obtido só dos resultados não podem se transformar acidentalmente em entradas.

## Transformações não realizadas

- Nenhum treinamento, busca de hiperparâmetros ou comparação de desempenho.
- Nenhuma imputação aprendida, normalização ou seleção de variáveis.
- Nenhuma alteração na configuração dos modelos do Hermes.
- Nenhuma correção manual de resultados esportivos ou preenchimento com temporadas futuras.

## Fontes primárias e atribuição

- Jolpica — contrato, User-Agent e paginação: https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md
- Jolpica — limites (4/s e 500/h no momento da consulta, sujeitos a mudança): https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md
- Jolpica — calendário e campos das sessões: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md
- Jolpica — posição de classificação opcional: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/qualifying.md
- Jolpica — resultados principais: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md
- Fórmula 1 — mudança de formato Sprint em 2023: https://www.formula1.com/en/latest/article/formula-1-confirms-f1-sprint-format-tweaks-for-2023-season.6v1c2lGggpLNEom2MMtjj0
- Termos dos dados (CC BY-NC-SA 4.0): https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md

Projeto educacional não comercial. Preserve a atribuição e os termos ao redistribuir os dados.
