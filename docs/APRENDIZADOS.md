# Aprendizado e refinamento do produto

Português · [English](en/LEARNING.md)

Created by: MBPaschoal
Status: active
Type: learning journal

Este registro explica decisões técnicas do projeto; não é uma lista de resultados sempre positivos. Mensagens históricas de commit permanecem no idioma e na data originais. A tabela oferece contexto bilíngue sem reescrever esse histórico.

| Evidência | Problema percebido | Correção e aprendizado |
|---|---|---|
| [Etapa 3](protocolo_temporal.md) | Uma base ordenada por data pode ainda conter revisões posteriores da fonte. | Separar corte conceitual, regra conservadora e aquisição real. Hash comprova bytes, não disponibilidade histórica. |
| [Avaliação 2025](../reports/avaliacao_final_v1/relatorio.md) | A vantagem de um modelo pode parecer maior sem comparar a mesma população. | Denominadores explícitos e a mesma coorte: 51 contra 50 integrantes; empate em 8/22 pódios completos. Não afirmar significância. |
| [8beae28](https://github.com/mbpaschoal/pitwall-lab/commit/8beae28) | O menu lateral ficou difícil de recuperar. | Restaurar o controle nativo e verificar viewport móvel. Estética não substitui navegação utilizável. |
| [128e272](https://github.com/mbpaschoal/pitwall-lab/commit/128e272) | Tempos de Austin não estavam cobertos pela fonte principal. | Integrar uma alternativa com identidade e proveniência, separada da emissão já registrada. |
| [0e97fbc](https://github.com/mbpaschoal/pitwall-lab/commit/0e97fbc) | Painéis duplicados e classificação incompleta prejudicavam a leitura. | Definir uma tela responsável por cada informação e mostrar todas as linhas publicadas. |
| [edca988](https://github.com/mbpaschoal/pitwall-lab/commit/edca988) | Links que funcionavam localmente falharam no contexto do Cloud. | Testar clique real em iframe e nova aba. Push não demonstra deploy. |
| [Revisão dos dados](DADOS_ATUAIS.md) | Histórico respondia sobre a prova atual; avisos de stint eram tratados como lacunas. | Filtrar pela identidade literal da pista e data anterior; separar aviso de qualidade de limites desconhecidos. Preservar ausências reais. |
| [Versão 0.1.0](../CHANGELOG.md) | Código disperso e idioma único dificultavam manutenção e apresentação do portfólio. | Organizar responsabilidades, centralizar tradução offline e manter compatibilidade. Versão do produto e do modelo têm significados distintos. |

## 03/11/2026 — A ordem de término não é a ordem das versões

Uma release antiga terminou depois da nova e tomou seu destaque no GitHub. Aprendi a separar criação, envio do pacote e escolha da versão vigente: agora a maior versão estável completa prevalece. Também separei espera normal por dados de uma falha real de acesso à fonte. O monitor abre uma ocorrência só quando há um problema e registra a recuperação; repetir notificações não torna o produto mais confiável. São Paulo ganhou uma conferência offline, sem transformar calendário futuro ou cartas prontas em previsão emitida.

## Como registrar a próxima melhoria

Descrever o comportamento anterior com um exemplo concreto, a causa conhecida (ou a incerteza), a mudança entregue, a verificação executada e o que continua limitado. Uma hipótese não vira resultado confirmado. Datas e versões devem corresponder à entrega real; não criar commits antigos fictícios nem editar resultados para contar uma história melhor.

## 0.2.0: comparar exige verificar o denominador

O brainstorm contava chuva em sessões completas e podia selecionar Sprint pelo tipo Race. A auditoria passou a exigir o nome literal da corrida, status de início e fim e exclusão de suspensões. O resultado mudou para oito provas com chuva durante a disputa. Também aprendi a preservar diferenças entre feeds: a numeração de voltas na Austrália/2026 não deve ser corrigida por um deslocamento aplicado a linhas sem vínculo. Taxas agora mostram largadas e empates; fontes incompletas permanecem incompletas. [Evidência e limites](../reports/pilotos_condicoes_20261029/README.md).

## 0.3.0 — Comparações justas e leitura agradável

Aprendi que um campo com formato correto ainda pode estar semanticamente errado: vento exige média circular. Também não basta comparar um piloto com todo o grid sem alinhar as corridas e os denominadores. Corrigi essas duas decisões e acrescentei regressões. Na interface, cada informação ganhou um destino: resultado em Corridas, classificação em Campeonato, estimativas em Chances de pódio. Duelo usa largadas em comum, e o cartão informa período, amostra e fonte. Um teste verde na raiz não comprova que o pacote publicado corresponde ao código; a entrega passa a verificar os dois.

## 0.7.0 — Resolução natural, identidade e contexto

Os 28 retratos anteriores tinham apenas 93 × 93 pixels. Aumentar sua área por CSS deixava o arquivo maior na tela, mas mantinha a mesma falta de detalhe. A correção começou na fonte: os 29 retratos atuais, incluindo Ryo Hirakawa, superam o mínimo de 512 pixels por eixo; 28 têm largura natural de 1336 pixels. As fotos dos 26 circuitos e os cinco cabeçalhos distintos têm pelo menos 2488 pixels de largura, para a largura de apresentação de até 1244 pixels com densidade 2×. Dimensões, identificação da pessoa, fonte, direitos e SHA-256 ficam registrados. O teste de resolução abre os arquivos reais; uma declaração no catálogo ou um arquivo ampliado não comprovaria o detalhe da fonte. [Catálogo de cabeçalhos](../dashboard_assets/fan/hero_catalog.json), [retratos](../dashboard_assets/fan/sources.json) e [verificações](../tests/test_high_resolution_assets.py).

A prancha C exigiu organizar seis telas como um conjunto: cabeçalho, controles compactos, imagem, conteúdo principal e navegação inferior. Em Pilotos, as quatro barras do líder comparam chuva, ausência de chuva registrada, calor e sentido anti-horário no período e na métrica selecionados. Os líderes empatados permanecem visíveis. As condições podem se sobrepor, seus denominadores ficam explícitos e ausência de chuva registrada não prova piso seco. O ajuste de composição não cria valores para reproduzir a prancha nem demonstra fidelidade visual completa; desktop, celular, idioma e interação precisam de conferência em navegador. [Jornada e limites](JORNADA_DO_FA.md).

As cartas mostraram outro problema de contexto: associar uma única imagem com uniforme Ferrari a Hamilton emprestaria essa equipe ao registro Mercedes/2024. As 87 artes novas usam uniforme neutro e três poses corporais distintas para cada um dos 29 pilotos; nome e cor da equipe vêm do GP exibido. As três cartas originais aprovadas permanecem preservadas e restritas às equipes compatíveis. A seleção determinística distribui três poses por trio sem recalcular probabilidades, reordenar favoritos ou descartar empates. A galeria permite conferir rosto, mãos, texto e pose; o diálogo do aplicativo continua opcional e sem percentuais. [Galeria](galeria-cartas.html) e [contrato testado](../tests/test_tarot_catalog.py).

Aprendi também a separar arquivo planejado, imagem gerada, revisão visual e publicação. A allowlist do pacote enumera as 87 variantes e os 29 retratos sem varrer pastas privadas. Hashes, resolução e testes locais sustentam a entrega local; a versão que o Cloud serve exige uma conferência pública própria. Modelo v1, 15 entradas, probabilidades e evidências científicas não mudam com a apresentação.

### Três erros encontrados na revisão final

Um contêiner do cabeçalho guardado em variável global parecia funcionar numa sessão isolada. Em páginas concorrentes, o objeto de interface podia pertencer à árvore de outra execução e provocar `Bad setIn` ou tela branca. O contêiner agora é criado para cada execução e passado explicitamente às telas. Testes unitários sequenciais não exercitam esse cenário; a revisão passou a incluir páginas reais simultâneas e captura de erros do navegador.

Um perfil compartilhado para Norris em 2026 podia voltar ao período 2024–2026 quando o componente do favorito salvo, por exemplo Verstappen, disparava uma nova execução. O valor padrão serializado do widget divergia do recorte do URL. Os filtros agora têm estado canônico próprio, alterado por escolhas explícitas, e o padrão do controle acompanha esse estado. Um período vazio escolhido pela pessoa continua vazio e editável; a falta de largadas não substitui o piloto solicitado.

Também havia diferença entre gráfico vazio e ausência real: limpar todas as condições ainda criava um gráfico sem observações. Além disso, contagens como 2 a 6 podiam aparecer como 200% a 600% por formatação de taxa. Agora uma seleção sem condições ou sem amostra mostra a ausência correspondente, contagens são inteiras e só taxas usam percentuais. Os valores científicos não mudaram; mudaram a persistência do recorte e sua representação. [Regressões dos perfis](../tests/test_pilot_views.py).

Na composição C3 de Pilotos, o fundo de Piastri em Silverstone e o close de Ricciardo em Miami têm pessoas, eventos e condições separados. A montagem visual não pode atribuir a Ricciardo a pista molhada da outra fotografia. O catálogo registra ambos os créditos e explicita essa separação.

## 0.7.1 — Traduzir texto depois de separar o HTML

A revisão pública em inglês levou a medir o Campeonato/2026/18 localmente: o harness AppTest levou 32,178 s em EN e 0,947 s em PT, incluindo a contabilização diagnóstica; o HTML em inglês somava 15.811.142 bytes. O perfil isolou o custo nas expressões regulares de tradução, que recebiam o documento inteiro, com imagens e fontes em base64, antes do parser. A correção separa o HTML primeiro e traduz somente textos e rótulos de acessibilidade, preservando CSS, URLs, identificadores, mídia, código e templates exatos do catálogo. O aprendizado é medir uma tela preenchida em cada idioma e manter conteúdo binário fora das regras de mensagens; uma etapa sem classificação não seria uma contraprova equivalente. Esses tempos medem execução local anterior à correção, não memória nem desempenho da hospedagem pública. [Implementação](../pitwall/i18n/__init__.py) e [regressões](../tests/test_i18n.py).

## 0.7.2 — Cor da equipe precisa fazer parte da arte

As bases neutras evitaram atribuir um uniforme posterior a corridas históricas, mas não cumpriram o pedido visual: a carta do Norris continuava sem laranja na ilustração. Uma borda colorida não transmitia a identidade da McLaren. A correção liga cada arte a piloto, equipe e período compatível, com cores visíveis no macacão, capacete e ornamentos. Pilotos que mudaram de equipe recebem variantes próprias; as bases neutras ficam arquivadas. Cobertura de arquivos, identidade histórica e inspeção visual das cores são verificações diferentes. Os testes de seleção não demonstram sozinhos a qualidade da arte. [Galeria](galeria-cartas.html) e [contrato](../tests/test_tarot_catalog.py).

## 0.7.3 — Verificar composição, além de presença

Uma tela podia conter todos os componentes esperados e ainda apresentar um título repetido ou esconder o final do pódio atrás da navegação. A comparação visual levou a um pódio compacto com nome completo acessível, clima antes dos detalhes opcionais e separação clara entre explicação e legenda dos acertos. A conferência passou a medir relações entre blocos nos dois idiomas e a densidade natural das imagens em 2×. A versão em inglês precisa de revisão própria: uma frase maior pode mudar a altura de um cartão. [Contrato e limites](JORNADA_DO_FA.md).

## 0.8.1 — Conferir a fonte antes de diagnosticar

Tratei “Bahrain Grand Prix in Malaysia” como anomalia por parecer um nome incoerente. A confirmação primária mostrou que a F1 anunciou oficialmente o GP de Bahrein em Sepang. O dado estava correto; faltavam um rótulo localizado e a distinção entre nome do evento e país anfitrião. O registro anterior fica preservado, com esta correção explícita.

A coleta do México revelou três causas distintas: HTTP 401 durante a janela ao vivo do acesso gratuito, uma revisão do fim programado e mensagens antigas com IDs atuais. A solução separa espera de acesso, revisão auditada de configuração e exclusão temporal identificada. Nenhuma dessas ações autoriza adivinhar pilotos, fabricar medições ou refazer uma previsão já registrada. [Revisão operacional](OPERACAO_FIM_SEMANA.md).
