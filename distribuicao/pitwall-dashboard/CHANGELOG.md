# Evolução do Pitwall Lab

## 0.8.23 — 2026-11-03

Corrige a criação da pasta de uma consulta de Pilotos sem cache, falha identificada na primeira execução hospedada da 0.8.22. Testes agora usam o construtor e o protocolo HTTP reais do cliente, com respostas locais controladas, cobrindo sucesso e HTTP 429. A espera da fonte é persistida mesmo quando o cliente interrompe a consulta por limite. Dados, modelo e probabilidades anteriores permanecem preservados.

## 0.8.22 — 2026-11-03

- Integra o México às análises de Pilotos: 67 GPs, 1.376 resultados e 1.362 largadas. Usa clima dos intervalos efetivos e mapa FIA 2026 conferido; cinco posições NC permanecem ausentes.
- Acrescenta complemento descritivo rastreável à base preservada de 66 GPs. A coleta agendada atualiza comparações mesmo quando o painel do GP não muda; divergências conservam a última versão validada e pendências com mais de seis horas acionam o monitor existente.
- Atualiza o período mostrado e os cartões compartilhados conforme os dados validados. Perfis de estreantes funcionam sem retrato aprovado, sem substituir sua identidade.
- Próximos GPs exigem resultados e clima conferidos e referência de circuito da edição. O registro de mapas desta entrega certifica o México; futuras referências precisam ser admitidas antes da incorporação. Sem treino, nova emissão ou alteração de probabilidades v1.

## 0.8.21 — 2026-11-03

- Corrige o destaque de releases: escolhe a maior versão estável com ZIP completo e hash, mesmo quando uma versão antiga termina depois. Novas releases aguardam o pacote antes de concorrer ao destaque.
- Instala monitor de coleta no GitHub: uma ocorrência atribuída ao proprietário por falha ou seis horas sem conclusão; repetição silenciosa e encerramento após recuperação. Restrições reais da fonte deixam de aparentar coleta saudável.
- Reconferência de São Paulo em OpenF1, Jolpica, F1 e GP Tempo; identidade alternativa 21 versus rodada canônica 20 documentada. Verificador offline confere janela, separação entre GPs e três artes distintas por piloto/equipe do catálogo.
- Previsão continua aguardando classificação observada e snapshot preditivo validado. Sem emissão antecipada, alteração do modelo ou das probabilidades registradas. Guia operacional PT/EN com passos e bloqueios.

## 0.8.20 — 2026-11-03

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 5/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.8.19 — 2026-11-02

- Destrava a coleta do México após revisão explícita da mudança no catálogo OpenF1: somente o fim programado da corrida passou de 23:00 para 22:00 UTC. Largada, identidade e encerramento observado continuam preservados; a validação de catálogo não foi relaxada. A espera conservadora até 23:30 UTC fica em campo próprio, sem antecipar consultas ao acesso gratuito.
- Mantém a recuperação documental dos pneus de Lawson da 0.8.18 e normaliza as cinco sessões a partir de capturas verificadas. Restaura as chaves opcionais de identificação nos tempos de TL1/TL2 do cache legado, sem mudar nomes, números, tempos ou observações do clima.
- Evidências, versão anterior do evento e resposta original com URL/UTC/SHA em `reports/lawson_tyres_mexico_20261102/`. O dado de término programado da API não é usado como encerramento observado nem como entrada de previsão.

## 0.8.18 — 2026-11-02

- Recupera os pneus médios do primeiro trecho de Lawson no TL3 do México: GP Tempo publica MEDIUM nas voltas 2–8; a FIA confirma um trecho contínuo de oito voltas. A atribuição à volta 1 é reconstrução documental por continuidade, identificada na interface e no CSV. Idade inicial e tempo ausentes não viram zero.
- Confere a identidade por data, pista, piloto e sessão: o evento 20 do GP Tempo corresponde ao GP 19 no Pitwall. Mantém os tempos nativos, inclusive duas voltas que a fonte alternativa deixa vazias. TL3 passa a dados recebidos após a conferência; as coberturas original e validada continuam separadas.
- Corrige o seletor existente de pneus para também acessar treinos e classificação, mantendo Corrida como padrão e as passagens pelos boxes separadas por sessão. Fontes clicáveis e textos PT/EN explicam a recuperação.
- Testes bloqueiam conflito de composto, horário/tempo divergente e duplicação do stint, preservam idade nativa válida e comprovam que dados originais não são modificados. Relatório e aceite em `reports/lawson_tyres_mexico_20261102/`.
- Aprendizado: a ausência em uma API não prova ausência na cronometragem. O cruzamento exige identidade e limites verificáveis; não autoriza copiar toda a fonte alternativa nem alterar o modelo ou as probabilidades registradas.

## 0.8.17 — 2026-11-02

Corrige o ícone de Corridas para uma bandeira quadriculada preta e branca, inclusive quando selecionada. Alinha títulos e setas dos expansores, removendo a margem de parágrafo que deslocava o texto. A regra compartilhada atende PT/EN, títulos longos e computador/celular. Validação focal em navegador e pacote; fotos, cores, dados e previsões preservados. Aprendizado: conferir o alinhamento do texto pintado, além do retângulo do controle.

## 0.8.16 — 2026-11-02

- Corrige a URL pública após navegar por links de calendário, capítulos e painéis. A rota é sincronizada pelo canal nativo do Streamlit: recarregar e copiar a URL conservam GP, tela e idioma.
- O retorno dos documentos usa um controle nativo que remove o documento da URL, sem criar outra camada do Streamlit nem reabrir o documento ao recarregar.
- Estende a reserva de espaço do ícone ao botão Explorar pilotos com texto ampliado. Os testes passam a verificar os dois controles e a aguardar a hidratação dos widgets antes de medir a interface.
- A validação pública da 0.8.15 revelou o problema do iframe, ausente na execução local sem wrapper. Regressões preservam o cenário público e o contexto de idioma, temporada e GP. Dados científicos e previsões não são alterados; a tag 0.8.15 permanece preservada.

## 0.8.15 — 2026-11-02

- Corrige o pódio sobre o aviso de coleta, retratos sobre estatísticas e créditos de foto sobre links. Blocos e controles de Pilotos reservam espaço no fluxo da página; a área rolável termina acima do menu fixo, inclusive ao mudar a altura da janela.
- Cabeçalho e seletores passam a refluir com texto ampliado. Links, busca e troca de idioma conservam temporada, GP, perfil e filtros; um piloto sem acervo histórico recebe uma mensagem explícita, sem substituição por outro piloto.
- Amplia o aceite para posições intermediárias de rolagem, alvos realmente clicáveis, PT/EN, computador/celular e reflow de texto. Os testes anteriores não cobriam as colisões reveladas pela captura do usuário. Chromium/WebKit emulados não substituem teste físico de iPhone. Ciência, emissões e identidade visual preservadas.

## 0.8.14 — 2026-11-02

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 4/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.8.13 — 2026-11-02

Corrige a publicação automática quando outro commit chega ao `main` durante a coleta/validação. A execução detecta o avanço antes de criar commit/tag e também após uma rejeição do push atômico. Em vez de mesclar pacotes gerados antigos, agenda uma execução nova sobre o `main` atual, restaura as capturas e refaz versão, pacote e testes.

As fontes originais ficam em cache e em artefato da execução antes do envio. Há até duas recuperações por cadeia; falhas de permissão, transporte e esgotamento continuam explícitas. Só uma versão realmente publicada é conferida no Streamlit. Não há push forçado nem alteração de probabilidades/modelo.

Oito testes com repositórios Git temporários reais verificam concorrência antes/durante o push, versão recalculada, tags e commits preservados, staging alheio e erros de permissão. [Runbook PT/EN](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/runbooks/automatic-publication.md).

## 0.8.12 — 2026-11-02

- Corrige a semântica acessível do controle de movimento: o botão anuncia a ação disponível, sem um estado de alternância que contradiga seu texto. Preferência do sistema e persistência continuam preservadas.
- Conclui a publicação da navegação suave, com testes portáteis, validação pública PT/EN e respeito a movimento reduzido em computador e celular emulado. As tags anteriores permanecem intactas.
- Aprendizado: um botão cujo nome muda com a ação deve usar a semântica de ação, sem aria-pressed. Nenhum dado, previsão ou composição visual foi alterado.

## 0.8.11 — 2026-11-02

- Publica a navegação suave implementada e validada em 0.8.10, mantendo a tag local original. Atalhos com foco, feedback discreto e entrada única em Como funciona respeitam as preferências de movimento.
- Pacote preparado a partir do commit validado, sem incorporar a pesquisa 0.9.0 em andamento. UI PT/EN, dados e identidade preservados.
- Validação: testes portáteis isolados e aceite público PT/EN em computador e celular emulado, incluindo movimento reduzido e navegação por teclado/toque. Aprendizado: publicar exige vincular código, pacote e build servido.

## 0.8.10 — 2026-11-02

- Navegação com foco no destino, retorno ao topo e rolagem suave no contêiner do Streamlit, preservando URL e filtros.
- Feedback discreto nos controles e entrada breve dos passos de Como funciona, uma vez por sessão da página. Preferência do sistema e controle de movimento respeitados.
- Validação PT/EN, computador e celular emulado; dados, modelos e identidade visual preservados. Aceite local não comprova publicação.

## 0.8.9 — 2026-11-02

Correção preventiva da coleta de São Paulo: a configuração explícita e uma configuração descoberta em cache podem representar o mesmo GP. O coletor agora reutiliza a explícita quando identidade, sessões e horários coincidem; conflitos reais de identidade ou programação continuam bloqueados.

O aceite público do fim de semana aguarda as métricas e o fim da renderização de Clima antes de conferir valores. Uma tentativa anterior chegou ao título antes das medições no celular em inglês; o recibo foi preservado. A correção mantém todas as verificações de conteúdo e os 22 resultados, sem reduzir o teste.

Validação operacional: 27 testes, incluindo configuração duplicada idêntica e divergência de horário. Modelo, probabilidades e capturas originais preservados. [Fontes e evidências](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_avaliacao_saopaulo_20261102/README.md).

## 0.8.8 — 2026-11-02

- Corrige o aceite do checkout público: testes legados que exigem capturas científicas locais continuam executados localmente. O CI mantém os testes de vínculo da avaliação, UI/leitor e o pacote portátil sem fontes privadas.
- A tag 0.8.7 permanece preservada. Esta correção conclui a entrega da avaliação do México e das melhorias de pneus; probabilidades, rankings e alvos posteriores não mudam.
- Validação: reprodução do pacote, testes portáteis e conferência pública PT/EN em computador/celular. Aprendizado: testes de um checkout público precisam declarar dependências disponíveis nesse checkout.

## 0.8.7 — 2026-11-02

### Alterado

- México: avaliação posterior da previsão prospectiva registrada, vinculada aos hashes da emissão e à classificação final da FIA. O Lab acertou 2 de 3 pilotos do pódio; a classificação, 1 de 3. Cobertura de 22 participantes, sem exclusões.
- Cinco abandonos mantêm a posição final ausente, com alvo de pódio confirmado como não. Dados posteriores não alteram as probabilidades ou os rankings registrados.
- Motivos de exclusão e estados pendentes permanecem legíveis em português e inglês, sem placar artificial.
- A coleta incorpora a classificação final FIA do México, com posições, tempos e pontos após as punições, mantendo a resposta anterior na auditoria. São Paulo recebe configuração explícita para as cinco sessões de 6–8/11; a corrida está marcada para 14h locais. [Fontes e validação operacional](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_avaliacao_saopaulo_20261102/README.md).
- Validação: testes de UI/leitor e de vínculo da avaliação, pacote portátil isolado e aceite das seis telas em PT/EN, computador/celular. Limite: duas corridas prospectivas avaliáveis não demonstram superioridade.


Português · [English](CHANGELOG.en.md)

Versões descrevem entregas do produto. O modelo científico v1 permanece congelado. Não foram atribuídas versões retroativas aos commits anteriores.

## 0.8.6 — 2026-11-02

- Revisão focal de pneus: composto ausente ou `UNKNOWN` aparece como “Não informado” em tabela, CSV e legenda. Os códigos conhecidos permanecem identificados por legenda textual; os dados originais não são normalizados nem sobrescritos.
- Idade inicial é explicada em voltas acumuladas pelo jogo antes do stint. Zero permanece um valor publicado, sem comprovar pneu novo; ausência permanece vazia. O hover mostra a mesma idade da tabela, incluindo pontos de uma volta, sem mudar limites ou largura das barras.
- “Limites comparáveis” usa Sim/Não/Não informado em PT e Yes/No/Not reported em EN, com escopo explícito sobre a sequência do piloto. Trechos sem limites válidos permanecem na tabela, sem barra inventada.
- Validação e limites da entrega local em `reports/revisao_pneus_p02_20261102/`. Modelo v1, complemento dos 262 stints, snapshots e previsões preservados. Verificação local não comprova nova publicação pública.
- Aprendizado: idade, composto e validade dos limites são informações distintas; legenda e unidade precisam esclarecer essas diferenças, sem inferir um jogo novo a partir de zero.

## 0.8.5 — 2026-11-01

- Corrigido o aceite do fim de semana para selecionar FP3 na interface em inglês e TL3 em português. O identificador canônico da sessão e as verificações dos 22 pilotos, tempos de Lawson, DSQ e CSV permanecem iguais.
- A 0.8.4 chegou ao main e ao dashboard, mas a release automática foi bloqueada pelo seletor antigo do teste. Seu commit e sua tag permanecem preservados. Esta correção conclui a entrega das 22 melhorias de UI/UX com o fluxo de publicação validado nos dois idiomas.
- A interface, as fontes descritivas, o modelo v1 e as probabilidades mantêm o comportamento da 0.8.4. Validação inclui o aceite corrigido, testes do pacote e confirmação do build público em PT/EN, computador e celular emulado; recibos em `reports/ui_ux_pro_max_implementacao_20261101/publicacao/`.
- Aprendizado: testes de interface precisam localizar o rótulo do idioma selecionado, mantendo os IDs científicos e as contraprovas de conteúdo.

## 0.8.4 — 2026-11-01

- Implementadas as 22 propostas da revisão das seis telas, preservando composição C, paleta, Abril Fatface/Lato, fotografias e cartas aprovadas. Programação compacta com UTC explícito, equipes acessíveis no celular, faixa única de GPs e localização de sessões, datas e rótulos em PT/EN.
- Perfis oferecem tabela equivalente aos gráficos, com condições, séries, valores e N; favorito fica perto da identidade. Duelo e companheiros recebem explicações próprias. A visita a um perfil conserva o GP da previsão, inclusive ao ajustar os critérios.
- Acertos diferencia previsão histórica não avaliável de ausência de previsão, identifica os últimos seis GPs e o resumo da temporada, e usa rótulos descritivos para os detalhes. Como funciona separa as 15 entradas do v1 do contexto do dashboard; documentos abrem diretamente, com fontes atuais e protocolo histórico identificados.
- Idioma programático acompanha PT/EN; bandeiras ganham nome acessível e estado selecionado. Atalho de teclado leva ao conteúdo; o controle de idioma acompanha a rolagem sem cobrir textos ou valores. A foto de Como funciona recebe variantes locais por viewport/DPR, com original, enquadramento e atribuição preservados.
- Validação focal e aceite local das seis telas estão registrados em `reports/ui_ux_pro_max_implementacao_20261101/`. Modelo v1, probabilidades e artefatos científicos preservados; a implementação local não comprova publicação pública.
- Aprendizado: contexto de navegação, ausência versus não avaliação e alternativas aos gráficos precisam de verificação por interação; traduzir textos visíveis não define o idioma programático.

## 0.8.3 — 2026-11-01

- Conferências FIA/F1 recuperam os 22 tempos do TL3 e o cadastro de Lawson sem empréstimo de outro GP. Removidos da projeção um registro anterior ao TL3 e 84 paradas anteriores à classificação; os índices e bytes originais permanecem auditados. São 88 paradas do TL3 e 89 da classificação no recorte validado.
- A decisão FIA 57 e a classificação final 59 confirmam Lawson como DSQ. A interface deixa posição e tempos anulados sem valor; o zero da tabela final não é interpretado como ausência de voltas físicas. A alteração é descritiva e não refaz a previsão.
- O relatório meteorológico FIA também registra o zero isolado. Uma exclusão documental específica permite recalcular a média do asfalto nas 100 leituras válidas: 40,7 °C, cobertura de 98,0%, sem interpolar o minuto ausente. Outros sensores e intervalos ativos permanecem iguais. Leituras não adjudicadas continuam retidas.
- Permanece ausente o composto das voltas 1–8 de Lawson no TL3. O trecho não foi inferido do stint seguinte. O arquivo oficial de cronometragem respondeu 401 e as consultas de voltas do Formula1Dashboard retornaram vazias; isso não demonstra inexistência em qualquer fonte. A revisão alcança caches completos e futuras coletas automaticamente, com testes contra troca de sessão, identidade, regra de cobertura e regressão de DSQ.
- Complemento versionado revisa somente a idade inicial de 262 stints observados do acervo, em 55 sessões/47 GPs. São 210 valores de zero para positivo, 36 de positivo para zero e 16 entre valores positivos; os demais campos permanecem iguais.
- O leitor aplica a revisão offline sobre uma cópia da projeção original, conferindo hashes, sessão, piloto, composto, limites e idade anterior. Complemento obrigatório ausente, corrompido ou incompatível interrompe a leitura; não reapresenta silenciosamente as idades antigas conhecidas.
- Snapshots e projeção-base preservam seus bytes. Modelo v1, 15 entradas e previsões registradas não mudam. Casos com revisão estrutural ou associação ambígua continuam fora deste complemento.
- Validação cobre valores em tabela e CSV, PT/EN, desktop/celular, contraprovas de integridade e pacote portátil isolado. Relatório e recibos em `reports/complemento_idade_pneus_20261101/`; esta entrega local não comprova nova publicação pública.
- Aprendizado: uma revisão do fornecedor pede complemento rastreável e verificação da identidade física do stint; zero publicado não comprova pneu novo.

## 0.8.1 — 2026-11-01

- Acertos do Lab mostra as contagens do modelo e da classificação em texto por GP; as bolinhas ficam como apoio visual decorativo. Etapas sem avaliação continuam sem nota, e empates permanecem explícitos.
- Pilotos mostra o número de largadas de cada condição e dos demais classificados sem depender de hover. Valores ausentes continuam distintos de zero e as comparações usam as amostras reais.
- Azul de texto separado do azul decorativo para melhorar o contraste dos ranks pequenos e dos cards. Rótulos da navegação móvel ampliados, com quebra de linha, e espaço de rolagem reservado para o foco acima do menu fixo. A grade dos líderes se reorganiza com texto ampliado; o menu móvel usa duas linhas.
- Validação focal cobre PT/EN, contagens, amostras e estados científicos. O aceite local verifica contraste, reflow e teclado; os recibos ficam em `reports/ui_ux_pro_max_20261101/implementacao/`. A verificação pública tem etapa própria.
- Aprendizado: legenda e tooltip não substituem contagens e denominadores acessíveis. A skill orienta a revisão; a implementação preserva identidade visual, fontes, modelo e probabilidades registradas.

- Publicados os dados observados do México: resultado com 22 pilotos, 1360 registros de voltas, pneus e paradas, além dos campeonatos da rodada 19 (24 pilotos e 11 equipes). O pódio observado aparece separado das probabilidades registradas; observar um resultado não o promove automaticamente à avaliação do modelo.
- Clima consolidado somente nos intervalos ativos: média de 24,2 °C no ar. A média do asfalto fica retida por uma leitura isolada de 0 °C entre 37,4 e 37,5 °C, com registro e diagnóstico bruto preservados. Doze mensagens anteriores ao início declarado da sessão ficam auditadas e fora da janela; a interrupção é excluída e os horários efetivos continuam vindo do controle de corrida. Originais e índices de exclusão preservados.
- Automação respeita a janela de acesso gratuito da OpenF1: aguarda os 30 minutos anteriores/posteriores às sessões. A extensão publicada do horário da corrida foi conferida e registrada para a coleta, sem reescrever a previsão. TL3 e paradas de Q continuam parcialmente retidos pelos cadastros ausentes 30/236; ausências não foram preenchidas por aproximação.
- Corrigido o diagnóstico sobre “Bahrain Grand Prix in Malaysia”: a F1 confirma o evento em Sepang. A interface mostra Malásia/Sepang com bandeira do país anfitrião, preservando nome e identidade originais. Barcelona também recebe seu rótulo explícito.
- Capa de Austin ganha crédito clicável e ajuste no espaço do mapa. A foto real de 5822 × 3275 px permanece preservada, com enquadramento por CSS. Paleta, fontes, cartas aprovadas e probabilidades preservadas. Aceite visual passa a acompanhar também as publicações automáticas de dados.
- Aprendizado: nomes incomuns exigem confirmação em fontes primárias; indisponibilidade durante a janela ao vivo, mudança de horário e dados contaminados de outra sessão são problemas diferentes. Há testes específicos para essas distinções e para impedir associação de pilotos apenas pelo número.

## 0.7.3 — 2026-11-01

- Refinada a disposição da Jornada do Fã: fotografia e pódio com proporções mais equilibradas, clima antes dos detalhes opcionais da pista e comparação antes/depois mais compacta, sem repetir o título do pódio.
- Acertos do Lab ganha bandeiras, rótulos curtos de GPs e legenda visual ao lado da explicação. Etapas sem avaliação continuam identificadas e não viram acertos ou zeros. A tela Como funciona aproxima os passos e os links sem reduzir a legibilidade.
- Texto móvel da explicação ampliado para 13 px. O atalho de calor utiliza fotografia de pista seca; a cena molhada fica associada à chuva. Cores, fontes, originais fotográficos e cartas aprovadas permanecem preservados.
- Novo aceite visual no CI mede as seis telas em PT/EN e computador/celular: resolução natural para exibição 2×, sobreposições, campeonato completo, controles com pelo menos 44 px e visibilidade do pódio e dos links antes da navegação fixa. Capturas e medidas acompanham o artefato do CI.
- Aprendizado: títulos e contêineres presentes não provam uma boa composição. O aceite agora verifica relações entre blocos e o espaço ocupado pela navegação; fotos reais, dados e reservas do Streamlit continuam distintos da imagem conceitual. Modelo, probabilidades e 614 arquivos científicos preservados.

## 0.7.2 — 2026-11-01

- Corrigida a identidade das cartas: as cores da equipe passam a aparecer no macacão, capacete e ornamentos da própria ilustração. Norris e Piastri usam laranja papaya da McLaren; a moldura deixa de ser a única indicação de cor.
- Catálogo de 126 artes de equipe, com três poses para cada uma das 42 combinações de piloto/equipe conhecidas no acervo. A seleção usa a equipe da linha do GP e o período compatível; Hamilton/Mercedes e Hamilton/Ferrari possuem artes distintas. Registros sem equipe reconhecida permanecem sem arte de equipe por suposição.
- As 87 artes neutras ficam arquivadas, sem substituir silenciosamente cartas de equipe ausentes. As três artes aprovadas do México permanecem preservadas. Galeria PT/EN, cobertura separada, verificações de integridade e allowlist explícita acompanham o catálogo.
- O diálogo continua opcional e sem percentuais; poses distintas, favoritos, empates, probabilidades e artefatos científicos são preservados.

## 0.7.1 — 2026-11-01

- Corrigido o gargalo de tradução em inglês que submetia o HTML completo, incluindo imagens e fontes em base64, às regras de tradução de mensagens. O HTML agora é separado primeiro; somente textos e rótulos de acessibilidade são traduzidos.
- URLs, CSS, identificadores, mídia incorporada e blocos de código permanecem preservados, assim como os templates exatos de hover do catálogo. Regressões cobrem HTML com grande volume de mídia, sem reduzir a resolução das imagens ou alterar dados e probabilidades.
- O marcador de entrega nas dependências solicita nova construção no Community Cloud, mantendo as mesmas versões dos pacotes. A confirmação pública da correção exige verificação própria.

## 0.7.0 — 2026-11-01

- As seis telas refinam a composição C na revisão C3: cabeçalho e controles compactos, foto do circuito em destaque, cinco fotografias principais distintas para os demais destinos e navegação inferior. Pilotos combina o fundo de Piastri em Silverstone com o close de Ricciardo em Miami, identificando pessoas e eventos distintos, e mostra quatro comparações por líder com os empates preservados. Chances de pódio reforça a linha antes/depois e o contexto temporal da emissão.
- Os 28 retratos de 93 × 93 pixels foram substituídos por fontes naturais maiores, com o acréscimo de Ryo Hirakawa: 29 retratos, todos acima do mínimo de 512 pixels por eixo; 28 têm largura de 1336 pixels. As 26 fotos de circuitos e os cinco cabeçalhos têm largura natural de pelo menos 2488 pixels, com fonte, direitos, dimensões e hash registrados. A apresentação usa os originais, sem ampliar miniaturas como evidência de qualidade.
- Catálogo de 87 cartas geradas: três poses corporais distintas para cada um dos 29 pilotos. As artes neutras permitem mostrar nome e cores da equipe do GP, inclusive nos períodos históricos. As três cartas originais aprovadas permanecem preservadas e restritas às equipes compatíveis.
- O diálogo das cartas continua opcional, sem percentuais ou ordem P1/P2/P3. A seleção determinística conserva os favoritos e suas probabilidades e distribui três poses diferentes por trio, inclusive quando há favoritos adicionais por empate. [Galeria das 87 cartas](docs/galeria-cartas.html).
- Corrigidos o compartilhamento indevido de um contêiner entre sessões, a perda do recorte do URL após atualização do favorito e a exibição de gráficos vazios ou contagens como percentuais. Período, métrica e amostra mínima permanecem canônicos; seleções vazias intencionais continuam editáveis. A regressão inclui perfis concorrentes e persistência do favorito.
- Testes verificam fontes e resolução natural, identidades, poses, hashes e allowlist do pacote. Modelo v1, 15 entradas, previsões e 614 arquivos científicos protegidos permanecem preservados. Esta nota descreve a entrega local; a conferência pública possui evidência própria.

## 0.6.3 — 2026-11-01

- Banners de pilotos fictícios substituídos por fotografias identificadas de Lando Norris e Max Verstappen em alta resolução; crédito clicável junto à imagem.
- Banner de carro usa a foto real de Sergio Pérez em Miami 2022, com autor, data e licença. Ilustrações anônimas anteriores deixam a distribuição.
- Cartas aprovadas de pilotos reais preservadas. Layout, dados e probabilidades não mudam; regressão impede fallback para um piloto fictício.

## 0.6.2 — 2026-11-01

- Cartões de acertos de 2024/2025 identificam o estudo retrospectivo; o aviso sobre previsões registradas fica restrito à avaliação prospectiva de 2026.
- Regressão adicional preserva essa distinção entre os períodos. Nenhum resultado ou probabilidade foi alterado.

## 0.6.1 — 2026-11-01

- Menu inferior elevado para preservar todos os botões diante do selo externo do Streamlit Community Cloud, identificado na verificação pública.
- Aceite do título principal usa seu nível semântico para evitar ambiguidade com o título da tabela do campeonato.

## 0.6.0 — 2026-11-01

- Reconstrução das seis telas seguindo a composição C aprovada: imagens em destaque, cabeçalho compacto compartilhado, calendário com bandeiras e menu inferior.
- Pódio observado com retratos, painel do circuito, ranking visual por condição, campeonato completo, linha antes/depois e comparação visual dos acertos.
- Três passos para explicar o Lab; fontes e documentação aprofundada continuam acessíveis. Cartas de tarô aprovadas permanecem em janela opcional.
- Retratos locais com proveniência, tradução PT/EN e adaptações para celular. Empates e dados ausentes permanecem explícitos; nenhuma probabilidade ou emissão é recalculada.
- Aceite visual e funcional das seis telas, links compartilhados, idioma, campeonato completo e cartas opcionais.

## 0.5.2 — 2026-11-01

Corrige a interrupção da coleta do México quando falta um cadastro de piloto na OpenF1. A sessão afetada permanece parcial, com motivo visível e suas projeções bloqueadas; as demais sessões continuam sendo coletadas. Duplicações, conflitos de voltas e mistura de sessões continuam rejeitados. Fontes originais, previsões registradas e modelo v1 preservados.

## 0.5.1 — 2026-11-01

Cartas de tarô aprovadas para o México, com cores das equipes, poses distintas e rostos ajustados a referências fornecidas pelo proprietário. A janela continua opcional; percentuais ficam somente na tabela de previsões. Retratos só aparecem quando a equipe do registro corresponde à arte, preservando os períodos históricos. Nenhuma probabilidade, emissão ou modelo foi alterado.

## 0.5.0 — 2026-11-01

A Jornada do fã substitui o menu lateral pela navegação inferior com seis destinos e controles nativos de teclado. Temporada/GP no topo, faixa de etapas próximas e imagem da pista em destaque com traçado e ficha abaixo. Pilotos ganha uma descoberta principal; campeonato continua completo, com tabelas em sequência. As cartas são opcionais, abertas por botão ou link direto nas previsões, com percentuais da emissão real, equipe do período e fallback de capacete. PT/EN e celular preservados. As ilustrações são decorativas, sem inferência ou alteração do modelo, das previsões ou dos dados.

## 0.4.7 — 2026-11-01

A previsão do México permanece intacta. O teste de ausência agora seleciona um GP realmente sem emissão, em vez de presumir que o México continuaria sem probabilidades. Essa correção preserva a verificação contra empréstimo de previsões entre GPs.

## 0.4.6 — 2026-11-01

Previsão prospectiva do México 2026 registrada em 01/11 às 04:32 UTC, antes da largada programada para 20h UTC. Classificação canônica com 22 pilotos, encerramento de Q3 comprovado e modelo v1 congelado. As probabilidades individuais de pódio não indicam ordem de chegada. Dados posteriores da corrida foram excluídos das entradas. Fontes, manifesto e probabilidades preservados para auditoria.

## 0.4.5 — 2026-10-31

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 2/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.4.4 — 2026-10-30

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 2/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.4.3 — 2026-10-30

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 1/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.4.2 — 2026-10-30

Atualização automática de dados de Mexico City Grand Prix pelo GitHub Actions. Sessões com dados recebidos: 0/5. Fontes, horários e arquivos originais preservados. Clima previsto separado do observado. As probabilidades e o modelo v1 permanecem congelados.

## 0.4.1 — 2026-10-30

Coleta e publicação automáticas no GitHub Actions, agendadas a cada meia hora. O calendário identifica os próximos GPs de 2026, incluindo sessões Sprint, sem troca aproximada de identidade. Cache com espera persistida, originais preservados como asset de release e novas versões apenas para mudanças reais. Publicação exige testes, navegação e conferência pública. A automação de coleta não treina nem emite previsões; as barreiras do modelo v1 continuam intactas.

## 0.4.0 — 2026-10-30

No Resumo, foto e traçado da pista passam a aparecer antes do pódio, dando destaque ao circuito.

Preparação do México com cinco sessões identificadas, coleta serial após encerramento observado, cache auditável e espera persistida em limites da API. Tempos, voltas, pneus, paradas, previsão meteorológica separada dos sensores da corrida e campeonatos da rodada própria. Admissão explícita de Q OpenF1 para o México; código commitado e publicação antes da largada continuam obrigatórios. Acertos de 2026 inclui somente previsões registradas e resultados posteriores validados. A corrida e a classificação ainda não aconteceram; não há previsão prospectiva do México nesta entrega.

## 0.3.1 — 2026-10-30

Corrige a sincronização do teste de favorito: o aceite passa a localizar o iframe atual após recarregar e aguardar o valor persistido, em vez de guardar uma referência que pode ser removida pelo Streamlit. A instabilidade foi observada no CI da branch principal; a release 0.3.0 e a aplicação pública haviam passado. Dados, regras de comparação e modelo científico permanecem iguais. O CI também regenera a distribuição e compara com a cópia publicada. Validação: jornada completa do navegador contra o pacote servido e conferência de integridade.

## 0.3.0 — 2026-10-29

- Navegação para fãs: campeonato completo em uma tela própria, resultados primeiro e explicações técnicas em segundo nível.
- Pilotos: duelos nos mesmos GPs, favorito no navegador, histórico recente, filtros preservados e cartões SVG para compartilhar.
- Correções: vento usa média circular; comparação individual usa os mesmos GPs; clima do resumo corresponde à corrida quando disponível.
- Leitura e celular: contraste, parágrafos, abas visíveis e imagens de apresentação menores, preservando os originais.
- Entrega: licença MIT para código original, verificação do pacote real em CI e documentação PT/EN.
- Limites: análise histórica não mede habilidade isolada. 17 compostos de treinos/classificação continuam ausentes. Modelo v1 e emissões preservados.

## 0.2.0 — 2026-10-29

### Pilotos: comparar resultados com condições reais de corrida

Novo menu com capacete, visão geral por condição e perfil individual, em português e inglês. Os seis destaques mostram chuva registrada, temperaturas da pista, sentido, curvas e altitude. Há filtros de temporadas, métrica e mínimo de largadas, classificação completa da coorte, mapa de todos os pilotos, confronto com o companheiro e evidências exportáveis com links para cada GP. Empates permanecem explícitos; ausência de amostra não vira desempenho zero.

A base descritiva reúne 66 corridas principais, 1.354 resultados e 1.340 largadas. Controle de corrida delimita os intervalos realmente disputados e exclui pausas: oito provas tiveram chuva registrada. Open-Meteo fornece 70 amostras atmosféricas horárias dentro desses intervalos, identificadas como reconstrução em grade. Foram conferidos 66 mapas FIA da edição: Suzuka tem traçado em oito; Spielberg e Marina Bay respeitam seus comprimentos por ano.

A [auditoria](reports/pilotos_condicoes_20261029/README.md) registra 295 verificações. Dos 50 limites de stint inválidos, 30 foram reconstruídos com voltas observadas; os demais correspondem a zero voltas completadas ou DNS. Nove compostos foram recuperados. Os 17 compostos ainda indisponíveis pertencem a treinos/classificação e ficam ausentes, excluídos destes cruzamentos. Corridas recebeu 11 sequências observadas de estratégias e oito preenchimentos pontuais de compostos; o nono composto recuperado já está numa dessas sequências.

Aprendizado: tipo de sessão não basta para separar Sprint e corrida; horário agendado não define tempo efetivo de prova; concordância entre feeds não garante independência. Na Austrália/2026, a seleção de voltas considera piloto, UTC e duração, preservando uma divergência de numeração entre fontes. Taxas usam largadas como oportunidades, inclusive abandonos e DSQ; não largadas são excluídas. As comparações são associações históricas, sem estimar habilidade isolada. Os 614 arquivos protegidos, o modelo v1 e as probabilidades registradas permanecem inalterados.

## 0.1.4 — 2026-10-29

### Imagens de São Paulo e Madrid

A imagem de Interlagos tinha apenas 349 × 197 pixels. Ela foi substituída por uma fotografia de 5000 × 3333 pixels do S do Senna durante o GP de São Paulo de 2022, com carros de Fórmula 1 e pista em destaque. Crédito Beto Issa/Fórmula 1 e Governo do Estado de São Paulo, CC BY 2.0.

Em Madrid, o recorte de uma foto vertical destacava o céu e escondia a pista. A nova foto oficial mostra a reta principal, boxes e arquibancadas em setembro de 2026. O enquadramento lateral da interface prioriza o circuito e mantém a pessoa retratada fora da área visível. Crédito Comunidad de Madrid, CC BY-NC-SA 4.0; a restrição não comercial é específica desse arquivo e permanece no catálogo.

A revisão confere resolução original e assunto visível no tamanho real do card em desktop e celular. As imagens originais permanecem sem edição; os recortes de apresentação, fontes, créditos e textos alternativos PT/EN estão registrados. Mapas, dados e previsões não mudaram.

## 0.1.3 — 2026-10-29

### Fotografia de Miami

Substitui a fotografia da Porsche Sprint Challenge, selecionada por ocorrer no mesmo circuito, por uma foto real de Sergio Pérez no Red Bull RB18 de Fórmula 1 no GP de Miami de 2022. A correção surgiu do uso público: o local correto não garante que a categoria mostrada seja a correta. A seleção visual agora confere circuito, categoria e identificação do carro.

Crédito: Dcmaradiaga (David Castro), Wikimedia Commons, CC BY-SA 4.0. Arquivo original preservado; texto alternativo PT/EN e catálogo com hash e origem atualizados. A foto é ilustrativa e datada de 2022, sem representar a temporada selecionada. Dados e previsões permanecem preservados.

## 0.1.2 — 2026-10-29

### Interface

Move as bandeiras BR/GB para o canto superior direito após o uso público mostrar sobreposição com a marca e os controles do Streamlit/GitHub no rodapé. Uma faixa reservada abaixo da barra nativa evita cobrir busca, perfil e título do GP em desktop e celular. Idioma, GP, aba e filtros permanecem preservados.

O aceite verifica a posição superior, as bandeiras lado a lado e a ausência de interseção com os controles da aplicação. Dados, modelo e probabilidades não mudaram.

## 0.1.1 — 2026-10-29

### Publicação e verificação

O GitHub e o CI da versão 0.1.0 estavam atualizados, mas uma sessão pública limpa ainda recebeu a interface anterior. Reexecutar a página não sincronizou o código. O arquivo de dependências da apresentação recebeu um marcador da entrega para solicitar um build novo ao Community Cloud, mantendo exatamente as mesmas versões de pacotes. A confirmação pública continua separada do push e do CI.

O teste de versões passou a usar changelogs sintéticos, para não depender de quais versões já existem no histórico real. Nenhum dado, modelo, probabilidade ou artefato científico foi alterado.

Aprendizado: uma release e testes aprovados não comprovam que o serviço de hospedagem já executa esse código. [Mecanismo documentado pelo Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-streamlit).

## 0.1.0 — 2026-10-29

Primeira versão sob a política explícita de versionamento do produto.

### Dados e correções

- 75 itens resolvidos na fila de dados: 71 conflitos de classificação documentados, complemento FIA para Baku/Q, dois estados de qualidade corrigidos e origem do archive identificada. Seis ausências confirmadas; 31 limitações de pneus permanecem.
- Histórico passou da corrida atual para até cinco edições anteriores na mesma pista, inclusive para GPs futuros sem acervo próprio.
- Fichas de 26 circuitos com altitude aproximada, recorde e contexto de DRS por temporada/referência.

### Produto e manutenção

- Bandeiras BR/GB com navegação, tabelas, gráficos, mensagens e documentos PT/EN; idioma preservado nos links.
- Código organizado por responsabilidade em `pitwall/`, com pontos de entrada compatíveis e fontes congeladas preservadas.
- README, aprendizados, arquitetura, contribuição e política de versões bilíngues.
- Cada nova entrega de dados ou melhoria exige incremento de versão e registro do problema, mudança, validação e aprendizado.

### Aprendizado e limites

A correção do Histórico mostrou que ter dados não garante responder à pergunta do usuário. A revisão dos stints distinguiu aviso de qualidade de lacuna real. O registro de origem do archive não inventa seu horário original de aquisição. Tradução altera apresentação, não evidência científica. Uma entrega local só passa a ser considerada pública após conferência do build servido.

## Antes da política de versões

Marcos anteriores são identificados por commits reais no [diário de aprendizado](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/APRENDIZADOS.md). Datas e mensagens originais foram preservadas.
