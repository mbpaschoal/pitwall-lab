# Dashboard local v1 — contrato de dados e interface

Created by: MBPaschoal
Status: contrato registrado antes da interface
Type: dashboard data contract

## Escopo fixado

Apresentação local, somente leitura, do estudo retrospectivo já calculado. Streamlit e Plotly; nenhum joblib, inferência, ajuste, coletor, API de dados, regeneração ou dado de 2026. **2025 já foi avaliado para o v1.** O aplicativo não oferece previsão ao vivo, próxima corrida, cenários, chatbot, login ou edição.

Os 109 testes anteriores passaram antes de alterar o projeto. Hashes dos arquivos científicos/artefatos anteriores e identificadores Git dos dados foram registrados para comparação final. Alteração preexistente em `projects/Pitwall Lab.md` será preservada; somente o estado corrente e a nova etapa serão acrescentados/atualizados.

## Arquivos por temporada e tela

| Temporada e função | Arquivo | Uso na interface |
|---|---|---|
| 2024 — validação já explorada | `reports/modelo_v1/previsoes_validacao.csv` | Probabilidades, elegibilidade, ranks, favoritos e alvos conhecidos, por piloto/GP. Separar a projeção de previsões das colunas de avaliação. |
| 2024 | `reports/modelo_v1/avaliacao_corridas.csv` | Cobertura, razões de não avaliação, conjuntos favoritos e pontuação oficial por GP. |
| 2024 | `reports/modelo_v1/metricas.json` | Métricas agregadas e denominadores, sem números copiados para o código. |
| 2024 | `reports/modelo_v1/calibracao.csv` | Dez faixas por método, médias previstas, frequências e contagens. |
| 2025 — avaliação final retrospectiva congelada | `reports/avaliacao_final_v1/previsoes_pre_corrida.csv` | Probabilidades, elegibilidade, ranks e favoritos SEM alvos. |
| 2025 | `reports/avaliacao_final_v1/avaliacao_por_piloto.csv` | Alvos e sua disponibilidade, relacionados por chave à projeção pré-corrida. Não ordenar favoritos por esses alvos. |
| 2025 | `reports/avaliacao_final_v1/avaliacao_corridas.csv` | Cobertura, razões de não avaliação e pontuação oficial por GP. |
| 2025 | `reports/avaliacao_final_v1/metricas.json` | Métricas agregadas e denominadores. |
| 2025 | `reports/avaliacao_final_v1/calibracao.csv` | Calibração descritiva e contagens já calculadas. |

“Explorar um GP” usa previsões, avaliação por piloto e avaliação por corrida da temporada selecionada. “Desempenho” usa métricas, calibração e avaliação por corrida, com validações cruzadas da cobertura. “Como funciona” apresenta explicação baseada nos protocolos já lidos e links para os documentos/repositório; não precisa abrir modelos ou dados brutos. As quinze entradas podem ser lidas do bloco explícito de `docs/experimento_modelo_v1.md` se necessário para listar seus nomes; não importar treinador para isso.

Não abrir `data/` no fluxo do dashboard. Não importar treinadores/avaliadores ou sklearn/joblib para servir telas. Não usar arquivos de auditoria como entradas de previsão. Identificação disponível nos artefatos é `piloto_id`; exibir IDs de modo claro, sem fabricar nomes completos, equipes ou ordem esportiva que não constem das fontes.

## Validação antes da apresentação

- Arquivos presentes e legíveis, CSV/JSON válido, cabeçalhos necessários sem duplicação, conjuntos não vazios e tipos explícitos.
- Temporada somente 2024 ou 2025 conforme seleção; rodada positiva; chaves únicas `(temporada, rodada, piloto_id)` e GP único `(temporada, rodada)`; nomes/data consistentes dentro do GP.
- Probabilidades finitas em `[0,1]` para elegíveis; ausentes para inelegíveis; alvo vazio é desconhecido, nunca zero. Flags booleanas e ranks precisam ser válidos.
- Favoritos derivados exclusivamente dos ranks/favoritos publicados, ordenados por rank; conferir coerência com probabilidades e desempates por ID, sem usar alvos. A referência de classificação é ranking, não previsão probabilística.
- Conferir alinhamento por chave entre os dois CSVs de 2025, sem descartar participantes silenciosamente. Valores pré-corrida repetidos devem concordar.
- Conferir cobertura/denominadores dos JSONs contra os CSVs; distribuição 0–3 e pódios completos contra GPs avaliáveis, sem recalcular um experimento ou escolher outras regras.
- GP não avaliável tem pontuação indefinida e motivo preenchido; nunca converter ausência em zero. Os campos `podio_observado` dos CSVs por GP podem estar vazios nesses casos: mostrar integrantes com `podio=1` conhecidos no CSV por piloto como **integrantes identificados na base**, sem inventar suas posições e sem pontuar o GP excluído.
- Calibração contém dez faixas uniformes por método; contagem inteira não negativa, médias/frequências finitas em `[0,1]` somente quando contagem positiva. Faixas vazias preservam médias/frequências indefinidas e aparecem com contagem zero, sem ponto artificial na curva.
- Ausência, formato inválido ou inconsistência: mensagem em português com arquivo e orientação para conferir/restaurar a entrega verificada. Não gerar, baixar, corrigir ou preencher dados automaticamente.

## Apresentação e comunicação

Superfície principal: **Explorar**; secundária: comparar métodos e aprender. Filtros na lateral, conteúdo alinhado à esquerda, tipografia numérica clara, paleta restrita inspirada em automobilismo, sem logos/fotos/fontes externas. Evitar hero promocional e cartões decorativos.

Destaque permanente: **“Estudo retrospectivo com dados históricos.”** Temporadas rotuladas por função; status de 2025 como já avaliado. Mostrar probabilidade individual de **pódio**, em porcentagem, não vitória ou posição específica. Não renormalizar probabilidades para somarem três.

Modelo/referência de classificação e observações posteriores devem ter seções, rótulos e símbolos distintos, não apenas cores. Pódio observado é conjunto sem ordem. Pontuação depende da cobertura oficial. Exibir motivos de inelegibilidade/alvos desconhecidos, inclusive Stroll/Espanha e Bortoleto/São Paulo conforme os artefatos, sem inventar causas.

“Desempenho”: probabilidades modelo versus constante; ranking modelo versus classificação. Exibir denominadores junto das métricas e distinguir casos individuais de GPs. Curva de calibração usa x=média prevista e y=frequência observada; histograma/tabela contém contagens e faixas vazias. Valores sempre vêm dos arquivos. Comparação entre anos é descritiva; ganho de ranking pequeno e empate em pódios completos de 2025 não podem ser ocultados.

“Como funciona”: pergunta, fonte Jolpica/CC BY-NC-SA 4.0, entradas, regressão logística, treino 2021–2023, validação 2024 já explorada, avaliação 2025 já realizada, classificação versus grid, ausências, elegibilidade, limites históricos e ausência de garantia futura. Links são referências de navegação; nenhum conteúdo remoto é carregado automaticamente.

## Cache, ambiente e execução

Separar carregamento/validação da apresentação. Cache apenas em memória, sem persistência. A cada interação, ler os bytes dos arquivos necessários e incluir o conteúdo ou seu SHA-256 na chave de cache; não confiar apenas em data de modificação. Arquivo alterado ou removido não pode servir resultado antigo do cache. Nenhuma interação escreve nos dados/relatórios científicos.

Dependências adicionais em `requirements_dashboard.txt`, com restrição pelas versões de `requirements_modelo_v1.txt`. Python existente 3.9.6; versões adicionais verificadas como compatíveis: Streamlit 1.50.0, Plotly 6.3.1, pandas 2.2.3 e PyArrow 20.0.0. Não atualizar os cinco pacotes científicos congelados nem instalar globalmente. Esta pilha serve ao aplicativo local desta etapa, não é recomendação de implantação pública.

Servidor apenas em `127.0.0.1`, sem telemetria. Navegador e servidor precisam comunicar-se localmente; o bloqueio de rede significa ausência de acesso externo automático, não proibição do HTTP/WebSocket local indispensável ao aplicativo. Não publicar, criar túnel ou serviço pago. Publicar o commit do código no repositório privado não é publicar o aplicativo.

## Verificação de aceitação

Testes unitários de validação e projeção; AppTest de navegação das três telas, duas temporadas, GPs avaliáveis e não avaliáveis, denominadores, mensagens de erro, ausência de inferência/rede/gravação e invalidação de cache. Fixtures inválidas claramente simuladas em temporários, sem alterar artefatos reais.

Reexecutar testes antigos/novos; iniciar servidor real; testar pelo navegador, capturar imagem real se possível e conferir viewport menor. Comparar hashes e versões científicas com o registro inicial. Documentar limitações reais das ferramentas, sem fabricar screenshot. Nenhuma verificação autoriza retreinar ou regenerar as etapas 4/5.
