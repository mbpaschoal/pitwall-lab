# Jornada do fã

[English](en/FAN_JOURNEY.md)

A composição C aprovada, refinada na revisão C3, orienta o produto inteiro: Corridas, Pilotos, Campeonato, Chances de pódio, Acertos do Lab e Como funciona. A paleta azul/branco/marinho/vermelho e as fontes Abril Fatface/Lato permanecem. A implementação usa dados existentes, não os números ilustrativos da prancha de estudo.

## Navegar

Os seis destinos ficam no rodapé, com ícone, rótulo e seleção visível. O controle é nativo, acessível por teclado. A área final da página reserva espaço para o menu; ele não elimina conteúdo. Logo, temporada, GP e busca compartilham um único cabeçalho nas seis telas. As bandeiras de idioma permanecem no canto superior direito. O seletor inclui o calendário inteiro; a faixa visual mostra etapas próximas, com a selecionada identificada. No celular, destaca o GP e seus vizinhos.

Corridas mantém os seis capítulos acessíveis nas abas: Resumo, Sessões e voltas, Pneus e paradas, Clima, Nesta pista e Equipes. Foto e traçado aparecem antes do pódio. As abas preservam as rotas antigas e evitam uma página com todas as tabelas abertas de uma vez. Pilotos mantém destaques, perfil e duelos, com seus recortes próprios. Campeonato mantém todas as linhas publicadas de pilotos e equipes, agora em sequência. As outras áreas continuam com as fontes, limites e documentos acessíveis.

## Composição C nas seis telas

1. **Corridas:** título e data sobre a foto, traçado à direita; pódio observado com retratos em ordem visual 2–1–3, ao lado dos dados do circuito e do clima. As posições vêm exclusivamente dos resultados oficiais disponíveis.
2. **Pilotos:** fotografia identificada de Daniel Ricciardo com capacete no cockpit, em um painel à direita, e fundo com Oscar Piastri na pista molhada. São fotografias distintas: Ricciardo em Miami em maio/2024 e Piastri em Silverstone em julho/2024; a composição não representa a mesma pessoa, evento ou condição climática. Pergunta direta, atalhos por condição e ranking com retratos completam a tela. Cada líder tem quatro barras: chuva, sem chuva registrada, calor e sentido anti-horário. Todos os líderes empatados aparecem identificados; ranking completo, critérios, perfis e duelos continuam acessíveis. Período, métrica e mínimo de corridas ficam no controle compacto de filtros.
3. **Campeonato:** fotografia de Lewis Hamilton no cockpit, progressão da temporada e classificação completa com retratos e marcas de equipes. Todas as linhas da fonte são preservadas.
4. **Chances de pódio:** fotografia histórica de Sergio Pérez em Miami e linha antes/depois, com o estado temporal da emissão destacado. A etapa anterior concentra as chances individuais em barras; a posterior reserva mais espaço ao pódio observado, quando disponível. As cartas continuam opcionais e a imagem histórica não representa o GP da previsão.
5. **Acertos do Lab:** fotografia de Max Verstappen em Silverstone, cartões por GP com acertos do Lab e da classificação e dois destaques. Corrida sem emissão não recebe nota zero; corrida ainda não disputada não recebe resultado. Uma corrida avaliada não vira uma amostra de seis corridas para reproduzir a prancha.
6. **Como funciona:** fotografia identificada de Andrea Kimi Antonelli no cockpit, três passos ilustrados e dois links para os documentos. Detalhes técnicos ficam em uma seção expansível, aberta automaticamente ao seguir um link de documento.

As fotografias dos 26 circuitos e dos cinco cabeçalhos usam fontes com largura natural de pelo menos 2488 pixels. Os 29 retratos superam o mínimo de 512 pixels por eixo; 28 têm largura de 1336 pixels. A aplicação usa essas fontes originais: ampliar os antigos retratos de 93 × 93 pixels não criaria detalhe. Retratos não estabelecem uniforme ou equipe de temporadas anteriores. Fontes e direitos estão em [créditos das imagens](../dashboard_assets/fan/ATTRIBUTION.md) e nos [testes de resolução](../tests/test_high_resolution_assets.py). A prancha orienta hierarquia, composição e navegação; os números exibidos vêm dos artefatos reais, sem copiar valores fictícios do estudo visual. Sem chuva registrada não comprova pista seca; as amostras das quatro condições podem se sobrepor.

## Abrir as cartas

Em Chances de pódio, **Abrir as cartas do GP** abre um diálogo opcional. O link direto pode usar `?tela=Previsões&temporada=2026&gp=19&cartas=1&lang=pt`. O usuário fecha pelo X, Escape ou pelo link para a tabela; o estado da abertura é removido ao fechar ou mudar de GP. Nada abre automaticamente na navegação normal.

Os pilotos vêm dos favoritos da emissão do GP selecionado, inclusive empates. As cartas exibem somente arte, nome e equipe; os percentuais permanecem na tabela de previsões. Não há sorteio, recálculo ou P1/P2/P3. A equipe vem do registro daquele GP; suas cores aparecem na própria ilustração — macacão, capacete e ornamentos — além da moldura. Hamilton em Mercedes/2024 não recebe a carta Ferrari de um período posterior. Ausência de emissão não gera cartas. Para estudos retrospectivos, o diálogo identifica essa condição. Falta de uma imagem válida permanece explícita, sem emprestar outro piloto ou um capacete genérico. No celular, as cartas são empilhadas e o diálogo permite rolagem.

O catálogo de equipe reúne 126 ilustrações geradas por IA: três poses para cada uma das 42 combinações de piloto/equipe reconhecidas no acervo, cobrindo 29 pilotos. As poses mostram capacete sob o braço, braços cruzados com capacete apoiado ao lado e capacete nas duas mãos à frente. Cada trio usa três poses distintas; favoritos adicionais por empate continuam incluídos, sem mudar seu ranking. A seleção é determinística pelo contexto do GP. As três cartas originais aprovadas de Verstappen, Hamilton e Russell permanecem preservadas, com prioridade quando a equipe corresponde. As 87 bases neutras são um arquivo histórico separado; não substituem arte colorida ausente. Falta de equipe reconhecida, imagem, hash válido ou compatibilidade de período mantém a ausência explícita.

A [galeria HTML das cartas](galeria-cartas.html) permite conferir as variantes por piloto e equipe, fora do aplicativo. Os caminhos são relativos; abra a galeria junto da pasta de imagens do repositório ou pacote exportado. O dashboard carrega somente as cartas dos favoritos solicitados. As ilustrações são decorativas e não representam fotografias, endosso ou resultados. Créditos: [arte das cartas](../dashboard_assets/tarot/ATTRIBUTION.md). As probabilidades continuam individuais e não indicam ordem de chegada.

## Filtros e amostras

Um link compartilhado conserva piloto, período, métrica e mínimo de corridas mesmo quando o favorito salvo no navegador é diferente. Mudar o favorito não muda silenciosamente o período analisado. Limpar o período ou as condições é uma seleção intencional: o controle permanece editável e o gráfico correspondente fica ausente, com orientação para selecionar dados. Um piloto sem largadas no recorte continua selecionado e não recebe um gráfico sem observações. Contagens aparecem como números inteiros; somente taxas recebem formatação percentual.

## Idioma e renderização

A partir da 0.7.1, a tradução em inglês separa o HTML antes de traduzir seus textos e rótulos de acessibilidade. Imagens e fontes em base64, CSS, URLs e identificadores permanecem intactos, evitando aplicar regras de mensagens a megabytes de mídia. A revisão de idioma precisa abrir também uma classificação preenchida, como Campeonato/2026/18: uma etapa sem classificação não exercita o mesmo volume. As imagens mantêm sua resolução natural. [Regressões de tradução](../tests/test_i18n.py); tempos locais e disponibilidade pública continuam sendo verificações distintas.

## Limites preservados

A navegação continua offline: não coleta dados, treina ou executa inferência. Previsão registrada, retrospectiva e resultado posterior mantêm seus significados. Modelo v1, 15 entradas e emissões anteriores permanecem preservados. Uma interface nova não resolve ausências dos provedores; essas continuam explícitas.
