# Jornada do fã

[English](en/FAN_JOURNEY.md)

A composição C aprovada, refinada na revisão C3, orienta o produto inteiro: Corridas, Pilotos, Campeonato, Chances de pódio, Acertos do Lab e Como funciona. A paleta azul/branco/marinho/vermelho e as fontes Abril Fatface/Lato permanecem. A implementação usa dados existentes, não os números ilustrativos da prancha de estudo.

## Navegar

As bandeiras têm área clicável de 44 × 50 CSS px, com o símbolo no tamanho original. No celular, o marcador vermelho fica abaixo do rótulo e dentro da célula ativa, nas duas linhas do menu; o ícone selecionado continua vermelho. Teclado, links alternativos e contexto do GP seguem disponíveis.

Os seis destinos ficam no rodapé, com ícone, rótulo e seleção visível. O controle nativo é acessível por teclado e tem links equivalentes enquanto seu módulo não carrega. As bandeiras também oferecem links nessa situação; os seis destinos e o contexto permanecem iguais. Quando o controle nativo fica disponível, os links alternativos são ocultados, sem duplicar o menu. A área final da página reserva espaço para o menu; ele não elimina conteúdo. Logo, temporada, GP e busca compartilham um único cabeçalho nas seis telas. As bandeiras de idioma permanecem no canto superior direito. O seletor inclui o calendário inteiro; a faixa visual mostra etapas próximas, com a selecionada identificada. No celular, destaca o GP e seus vizinhos.

Corridas mantém os seis capítulos acessíveis nas abas: Resumo, Sessões e voltas, Pneus e paradas, Clima, Nesta pista e Equipes. Foto e traçado aparecem antes do pódio. As abas preservam as rotas antigas e evitam uma página com todas as tabelas abertas de uma vez. Pilotos mantém destaques, perfil e duelos, com seus recortes próprios. Campeonato mantém todas as linhas publicadas de pilotos e equipes, agora em sequência. As outras áreas continuam com as fontes, limites e documentos acessíveis.

## Composição C nas seis telas

1. **Corridas:** título e data sobre a foto, traçado à direita; pódio observado com retratos em ordem visual 2–1–3, ao lado dos dados do circuito e do clima. As posições vêm exclusivamente dos resultados oficiais disponíveis.
2. **Pilotos:** fotografia identificada de Daniel Ricciardo com capacete no cockpit, em um painel à direita, e fundo com Oscar Piastri na pista molhada. São fotografias distintas: Ricciardo em Miami em maio/2024 e Piastri em Silverstone em julho/2024; a composição não representa a mesma pessoa, evento ou condição climática. Pergunta direta, atalhos por condição e ranking com retratos completam a tela. Cada líder tem quatro barras: chuva, sem chuva registrada, calor e sentido anti-horário. Todos os líderes empatados aparecem identificados; ranking completo, critérios, perfis e duelos continuam acessíveis. Período, métrica e mínimo de corridas ficam no controle compacto de filtros.
3. **Campeonato:** fotografia de Lewis Hamilton no cockpit, uma faixa canônica de GPs e classificação completa com retratos e marcas de equipes. Todas as linhas da fonte são preservadas; as equipes também são consultáveis na linha móvel de cada piloto.
4. **Chances de pódio:** fotografia histórica de Sergio Pérez em Miami e linha antes/depois, com o estado temporal da emissão destacado. A etapa anterior concentra as chances individuais em barras; a posterior reserva mais espaço ao pódio observado, quando disponível. As cartas continuam opcionais e a imagem histórica não representa o GP da previsão.
5. **Acertos do Lab:** fotografia de Max Verstappen em Silverstone, cartões por GP com acertos do Lab e da classificação e dois destaques. Corrida sem emissão não recebe nota zero; corrida ainda não disputada não recebe resultado. Uma corrida avaliada não vira uma amostra de seis corridas para reproduzir a prancha.
6. **Como funciona:** fotografia identificada de Andrea Kimi Antonelli no cockpit, três passos ilustrados e dois links para documentos. Os passos separam entradas do v1, probabilidades e contexto descritivo. Um documento selecionado abre diretamente na área de leitura, com retorno à explicação e índice de outras referências.

As fotografias dos 26 circuitos e dos cinco cabeçalhos usam fontes com largura natural de pelo menos 2488 pixels. Os 29 retratos superam o mínimo de 512 pixels por eixo; 28 têm largura de 1336 pixels. A aplicação usa essas fontes originais: ampliar os antigos retratos de 93 × 93 pixels não criaria detalhe. Retratos não estabelecem uniforme ou equipe de temporadas anteriores. Fontes e direitos estão em [créditos das imagens](../dashboard_assets/fan/ATTRIBUTION.md) e nos [testes de resolução](../tests/test_high_resolution_assets.py). A prancha orienta hierarquia, composição e navegação; os números exibidos vêm dos artefatos reais, sem copiar valores fictícios do estudo visual. Sem chuva registrada não comprova pista seca; as amostras das quatro condições podem se sobrepor.

## Continuidade e acesso — 0.8.4

As bandeiras mantêm a posição no cabeçalho e acompanham sua rolagem; nomes acessíveis, seleção e idioma programático seguem PT/EN. Um atalho de teclado pula ao conteúdo. Programação usa linhas compactas com UTC explícito; sessões e datas seguem o idioma, preservando IDs e timestamps.

Perfis oferecem tabela equivalente com condições, séries, valores e N, mantendo ausência abaixo do mínimo distinta de zero. O favorito fica próximo da identidade; Duelo e companheiros têm regras explicadas separadamente. Links e alterações de critérios conservam o GP de origem de uma previsão, separado do período histórico do perfil.

Acertos identifica a janela dos últimos seis GPs e o resumo da temporada. Previsões históricas existentes fora dos critérios de avaliação são identificadas com motivo, sem nota; ausência de probabilidades continua explícita. Os documentos distinguem fontes atuais e protocolo histórico, e abrem diretamente na área de leitura. A foto de Como funciona usa três variantes WebP locais por viewport/DPR; o original, os créditos e o enquadramento permanecem preservados. O pacote entrega apenas as variantes explicitamente allowlistadas.

## Contagens, amostras e leitura — 0.8.1

Acertos do Lab apresenta, em cada GP avaliado, as contagens do Lab e da classificação como texto. As bolinhas são decorativas; etapas sem avaliação continuam sem nota. Pilotos mostra o número de largadas do ranking e de cada comparação de condição, sem depender de passar o mouse. Uma taxa ausente continua distinta de zero.

O azul dos textos pequenos tem um token próprio, com contraste maior que o azul decorativo das barras. Rótulos da navegação móvel usam 12 px e podem quebrar linha. A rolagem reserva espaço para o foco acima do menu fixo; no celular, até 600 px, os líderes do ranking ficam em uma coluna para acomodar empates e amostras, e o menu se distribui em duas linhas. A identidade, as fotos e as probabilidades permanecem as mesmas.

No desktop, a grade usa a largura disponível e o tamanho do texto para acomodar os líderes; com texto ampliado, os cards podem passar a uma coluna. Os percentuais conservam espaço para o valor completo.

O [relatório de aceite local](../reports/ui_ux_pro_max_20261101/implementacao/relatorio.md) separa testes automatizados, medição em navegador e limites. Texto ampliado por simulação e largura de 320 CSS px não são apresentados como teste de zoom nativo ou certificação completa de acessibilidade.

## Acabamento e Duelo — 0.10.0

A composição mantém a paleta e a tipografia aprovadas, com contornos discretos, títulos equilibrados, números tabulares e acompanhamento de fontes agrupado. As respostas de abas, condições e expansores são curtas e respeitam a preferência de movimento reduzido.

No Duelo, retratos e métricas ficam lado a lado quando há espaço, inclusive no celular. Em largura muito estreita ou com texto ampliado, os painéis passam a uma coluna para preservar a leitura. A faixa de diferença acompanha a métrica, o período e a condição selecionados: taxas são comparadas em pontos percentuais; contagens, em números inteiros. Empate e amostra abaixo do mínimo permanecem explícitos. O placar de posições continua independente dessa diferença. Largadas em comum, resultados comparáveis e evidências ficam disponíveis, sem alteração nos dados ou nas probabilidades registradas.

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

## Conferência visual da entrega 0.7.3

O aceite [aceite_visual.cjs](https://github.com/mbpaschoal/pitwall-lab/blob/main/tests/browser/aceite_visual.cjs) percorre as seis telas nos dois idiomas, em 1040 × 992 pixels para as três telas superiores da referência C, 1040 × 875 para as inferiores e 390 × 844 no celular, com densidade 2×. Ele registra capturas e medidas, sem tratar o CSS anterior como modelo aprovado. Confere ordem de leitura, sobreposição, resolução natural, legenda, campeonato completo e controles; o pódio observado e os links explicativos precisam ficar acima da navegação na conferência desktop. O CI preserva essas evidências por três dias.

A comparação preserva diferenças legítimas: fotografias reais substituem as imagens conceituais, empates continuam empates, todas as linhas do campeonato permanecem disponíveis e etapas sem avaliação não recebem números fictícios. O selo externo do Streamlit tem espaço reservado. Por isso, a referência orienta a composição, mas não se declara identidade pixel a pixel.
