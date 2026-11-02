# Navegação e movimento — implementação

Created by: MBPaschoal
Status: implemented; locally verified; not published
Type: implementation and acceptance report

As três propostas foram implementadas mantendo fotos, paleta, fontes, composição e dados. A implementação usa CSS e JavaScript local, sem instalar a engine upstream ou adicionar dependências.

- Links, cartões, calendário e menu têm transições discretas de cor, fundo e borda (160 ms), sem deslocar controles.
- Atalhos ao final do conteúdo permitem ir ao conteúdo principal ou ao topo. A rolagem ocorre em `.stMain`, move o foco ao destino e preserva URL, GP, temporada, idioma e filtros. O atalho de teclado para pular ao conteúdo também usa esse comportamento.
- Os três passos de Como funciona têm entrada de 220 ms e deslocamento de 6 px, uma única vez por sessão da página. Trocas de tela e reruns não repetem a entrada. O conteúdo nunca começa oculto.

O controle PT/EN de movimento persiste durante a sessão do navegador. `prefers-reduced-motion` tem precedência: rolagem imediata, sem transições ou entrada e texto indicando a preferência do sistema. O listener e o observador são instalados uma vez no documento do app, inclusive dentro do iframe do componente; não acessam o documento externo do host.

O primeiro layout colocou os atalhos entre contexto e capa; o aceite visual detectou o afastamento. Os atalhos foram movidos ao fim da página, preservando os critérios visuais existentes. Não se alteraram testes para relaxar limites de composição.

Verificações: 62 testes de app, metodologia, navegação e idiomas; oito combinações PT/EN × 390/1440 px × movimento normal/reduzido, percorrendo os seis destinos (48 visitas), com teclado, toque móvel, foco, percentuais de rolagem, preservação da URL e entrada única. A geometria das seis telas tem aceite próprio de 24 cenários.

O disco limitou temporários e PNGs. O runner de testes usa cópias APFS independentes dos mesmos bytes para reduzir espaço, sem mock de dados/UI ou alteração das asserções; capturas finais usam JPEG. Logs de falha e medições anteriores permanecem separados dos recibos finais. Os 614 arquivos científicos e 28 arquivos de emissão/registro permanecem idênticos.

Notas da melhoria em 0.8.10 PT/EN. Outro fluxo atualizou simultaneamente a versão global para 0.9.0 (pesquisa statsmodels); essa alteração foi preservada. O erro intermediário de versão no aceite visual reflete essa atualização concorrente. Este trabalho não publica nem atualiza a distribuição canônica.

[Funcional](browser.json) · [Testes](tests-cow.log) · [Preservação](preservation.json) · [Geometria final](geometry-complete/acceptance.json).

English: three local improvements preserve the approved identity: subtle control feedback, focus-aware same-document scrolling, and a once-per-page-session entrance for methodology steps. System and session motion preferences are honored. Local PT/EN desktop and emulated mobile checks cover all six destinations. Physical handsets and screen readers were not tested. No publication occurred.
