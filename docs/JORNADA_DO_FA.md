# Jornada do fã

[English](en/FAN_JOURNEY.md)

A interface 0.13.0 usa o menu lateral aprovado pelos usuários. Mantém Abril Fatface/Lato, o azul do Pitwall e a linguagem editorial. As capas dos GPs usam ilustrações abstratas originais, cores e formas associadas ao destino, com cidade, circuito e data identificados. México, Japão e São Paulo têm composições próprias. Eventos no mesmo país conservam sua identidade.

## Navegar

O menu reúne quinze destinos: Previsões deste GP e Acertos do Lab; Resultado da corrida, Sessões e voltas, Pneus e paradas, Clima, Histórico desta pista e Equipes neste GP; Perfis de pilotos e Duelo de pilotos; Campeonato de pilotos e Campeonato de equipes; Como funciona, Fontes e limites e Termos da F1. No celular, abre por “Explorar o Pitwall” e fecha após a seleção. A seção ativa tem faixa vermelha e nome visível.

Há um único seletor de Grande Prêmio, com temporada e rótulos explícitos. A faixa de bandeiras de etapas e o menu de rodapé foram retirados. Os seletores irrelevantes ficam ocultos em Pilotos e Sobre o Lab, conservando o contexto para o retorno. A busca encontra páginas por tarefas como “voltas”, “cartas” e “pneus”, além de pilotos, equipes e corridas. Links internos usam a mesma aba; o menu usa botões nativos e links alternativos enquanto esses controles carregam. A troca preserva GP e idioma. Somente o capítulo selecionado de Corridas é renderizado.

Resultado da corrida mantém pódio observado em ordem visual 2–1–3 e contexto do circuito. Foto e mapa ficam em “Foto e mapa do circuito”, com fonte e licença. “Atualização e cobertura” separa o estado operacional do conteúdo principal. Ausência de dados permanece explícita. Campeonato permite acessar diretamente cada tabela completa; links antigos sem painel continuam exibindo as duas.

## Abrir as cartas

Previsões mostra a capa, a condição temporal da leitura e **Ver as cartas deste GP**. Favoritos, chances e comparação posterior ficam fora da leitura inicial, inclusive da árvore de acessibilidade. O botão abre versos iguais, sem nomes. Cada clique revela uma carta com arte, piloto, equipe daquele GP, probabilidade individual registrada e explicação. É possível virar uma carta para baixo. Não há botão de revelar todas.

A máscara de revelação fica na sessão do navegador, identificada por temporada, GP, emissão e probabilidades. Navegar para outra seção e voltar conserva as cartas; trocar o idioma também. Outro GP ou outra emissão tem estado independente. `cartas=1` abre os versos, sem revelar faces novas. Após revelar todas as cartas disponíveis, a comparação, a distribuição completa, a cobertura e os detalhes ficam acessíveis. Sem emissão não há cartas inventadas. Estudos retrospectivos continuam identificados como retrospectivos.

As cartas ilustram os favoritos existentes, inclusive empates; não há sorteio, inferência ou P1/P2/P3. A equipe corresponde ao registro daquele GP. Os originais e o catálogo de arte são preservados. Uma imagem indisponível tem aviso, sem emprestar outro piloto. As probabilidades individuais não indicam ordem de chegada. No celular, as cartas ficam em coluna. Teclado, foco visível, contador de revelação e preferência de movimento reduzido são respeitados.

A [galeria HTML das cartas](galeria-cartas.html) permite conferir as variantes fora do aplicativo. Créditos: [arte das cartas](../dashboard_assets/tarot/ATTRIBUTION.md). Fotografias e retratos mantêm seus originais e [créditos](../dashboard_assets/fan/ATTRIBUTION.md).

## Validação

Os testes percorrem os quinze destinos, PT/EN e larguras de computador e celular, revelação individual, conteúdo acessível, retorno, mudança de idioma, foco, links alternativos, rolagem e downloads. O modelo v1 e as probabilidades são preservados. Aceite local, CI, pacote e domínio público são etapas distintas. Larguras emuladas e texto ampliado por simulação não constituem teste em aparelho físico ou zoom nativo.

## Histórico da composição

As notas abaixo descrevem entregas anteriores. Na 0.13.0, o menu lateral e as cartas fechadas substituem o rodapé, a faixa de etapas e o diálogo de cartas então usados.

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

## Filtros e amostras

Um link compartilhado conserva piloto, período, métrica e mínimo de corridas mesmo quando o favorito salvo no navegador é diferente. Mudar o favorito não muda silenciosamente o período analisado. Limpar o período ou as condições é uma seleção intencional: o controle permanece editável e o gráfico correspondente fica ausente, com orientação para selecionar dados. Um piloto sem largadas no recorte continua selecionado e não recebe um gráfico sem observações. Contagens aparecem como números inteiros; somente taxas recebem formatação percentual.

## Idioma e renderização

A partir da 0.7.1, a tradução em inglês separa o HTML antes de traduzir seus textos e rótulos de acessibilidade. Imagens e fontes em base64, CSS, URLs e identificadores permanecem intactos, evitando aplicar regras de mensagens a megabytes de mídia. A revisão de idioma precisa abrir também uma classificação preenchida, como Campeonato/2026/18: uma etapa sem classificação não exercita o mesmo volume. As imagens mantêm sua resolução natural. [Regressões de tradução](../tests/test_i18n.py); tempos locais e disponibilidade pública continuam sendo verificações distintas.

## Limites preservados

A navegação continua offline: não coleta dados, treina ou executa inferência. Previsão registrada, retrospectiva e resultado posterior mantêm seus significados. Modelo v1, 15 entradas e emissões anteriores permanecem preservados. Uma interface nova não resolve ausências dos provedores; essas continuam explícitas.

## Conferência visual da entrega 0.7.3

O aceite [aceite_visual.cjs](https://github.com/mbpaschoal/pitwall-lab/blob/main/tests/browser/aceite_visual.cjs) percorre as seis telas nos dois idiomas, em 1040 × 992 pixels para as três telas superiores da referência C, 1040 × 875 para as inferiores e 390 × 844 no celular, com densidade 2×. Ele registra capturas e medidas, sem tratar o CSS anterior como modelo aprovado. Confere ordem de leitura, sobreposição, resolução natural, legenda, campeonato completo e controles; o pódio observado e os links explicativos precisam ficar acima da navegação na conferência desktop. O CI preserva essas evidências por três dias.

A comparação preserva diferenças legítimas: fotografias reais substituem as imagens conceituais, empates continuam empates, todas as linhas do campeonato permanecem disponíveis e etapas sem avaliação não recebem números fictícios. O selo externo do Streamlit tem espaço reservado. Por isso, a referência orienta a composição, mas não se declara identidade pixel a pixel.
