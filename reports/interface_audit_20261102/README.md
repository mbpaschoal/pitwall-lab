# Revisão da interface — 0.8.16

Created by: MBPaschoal
Status: local validation completed; public confirmation pending
Type: interface audit and release evidence

Português · English below

A captura do usuário mostrou duas falhas reais: o pódio invadia o aviso de coleta e o menu fixo encobria o conteúdo durante a rolagem. O aceite anterior verificava principalmente posições iniciais e limites globais da página; isso não detectava conteúdo escondido por outros elementos.

A correção elimina margens negativas nos blocos de conteúdo, reserva uma área rolável acima do menu e acompanha mudanças na altura da janela. Retratos, chips, créditos e controles de Pilotos passam a reservar espaço. Cabeçalho e seletores refluem com texto ampliado. Mantém fotos, fontes, cores e os seis destinos da identidade atual.

A revisão funcional também corrigiu links do logo, pódio, classificação e busca que perdiam temporada/GP; a troca de idioma agora conserva perfil, rival e filtros. Pilotos sem cobertura histórica mantêm sua identidade e recebem uma indicação de indisponibilidade, sem substituição silenciosa. As buscas curtas não reaproveitam a temporada do último evento encontrado.

## Escopo e evidências

- Seis telas, seis capítulos de Corridas, sete documentos, perfis e duelos; estados históricos, retrospectivos, observados, futuros e excluídos.
- PT/EN, computador e celular emulado; Chromium e WebKit. Testes de rolagem verificam geometria, texto pintado, retratos, alvos clicáveis e ausência de transbordamento. O stress de texto duplica métricas de fonte/linha; não representa zoom nativo ou Dynamic Type.
- Cliques reais cobrem menu, calendário, capítulos, busca, favoritos, filtros, troca de idioma, documentos, compartilhamento, CSV/SVG e retorno das cartas. Downloads científicos são comparados com os bytes originais.
- As URLs externas são verificadas somente por leitura; respostas HTTP válidas nesta execução não garantem disponibilidade futura.
- Pacote final isolado: 475 arquivos; baseline `05eec0b70b24abf9a68dae45aac36730eefb5bc5`; build `cf5f36655486530283b3dcc800aad0dbe40ab6a4331170df1150fdf5b008415e`.
- [Integridade protegida](protected-integrity.json): 614 arquivos científicos + 28 arquivos de emissões/registro sem alteração.

A implementação foi feita em checkout isolado para preservar a pesquisa concorrente na raiz do cofre. Não houve coleta, treinamento, inferência ou alteração de probabilidades.

Resultados locais: 100 estados inventariados, 56 fluxos funcionais por motor, 24 composições visuais por motor, 120 posições de rolagem por motor e testes adicionais em 320 px e texto ampliado. Os 119 endereços externos inventariados no DOM e no canvas responderam HTTP 200/206; os PDFs adicionais têm assinatura PDF válida. Os 141 testes portáteis passaram no pacote final. Os recibos guardam a proveniência e distinguem as rodadas anteriores do ajuste localizado de Filtros. A primeira publicação 0.8.15 passou na geometria pública, mas os cliques completos revelaram uma falha do wrapper: navegações por HTML podiam deixar a URL externa antiga, e o retorno documental podia aninhar o site. A 0.8.16 sincroniza a rota no início de cada sessão pelo canal nativo do Streamlit e usa retorno documental nativo e atômico. Recarregamento, URL externa e ausência de frames aninhados entram no aceite. O ícone de Explorar pilotos também recebe espaço no stress de texto. A confirmação pública final da 0.8.16 está em andamento. Nenhum teste automatizado permite prometer funcionamento perfeito em todos os dispositivos; esta auditoria não inclui iPhone físico, leitor de tela ou todas as versões de navegador.

## English

The user screenshot exposed two real defects: the podium overlapped collection notices and the persistent dock covered content during scrolling. Earlier acceptance focused on initial positions and global page bounds, missing content hidden by other elements.

The fix removes negative content margins, reserves a scroll viewport above the dock and follows window-height changes. Driver portraits, chips, credits and controls reserve their own space. The header and selectors reflow with enlarged text while retaining the existing photographs, typefaces, colors and six destinations.

Functional review also fixed season/GP context loss through the logo, podium, standings and search. Language changes retain profiles, rivals and filters. Missing historical driver coverage is explicit without substituting another identity. Short search queries retain the selected context independently of matched events.

Coverage includes all six screens, six race chapters, seven documents, driver profiles/duels and historical, retrospective, observed, future and excluded states in PT/EN, desktop and emulated mobile. Real clicks test navigation, search, favorites, filters, language, sharing, CSV/SVG downloads, documents and cards. Chromium/WebKit and deterministic doubled-text stress tests do not replace physical iPhone, native zoom, screen-reader or all-browser testing.

The isolated package contains 475 files, preserving the scientific baseline and all 642 protected hashes. Work took place in a separate checkout without touching concurrent research, collecting data, training or changing probabilities. Public confirmation remains pending until the recorded served version and build match this package.

SDK reference: [Streamlit Session State lifecycle](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#caveats-and-limitations). HTML navigation starts a fresh WebSocket session; native widget reruns retain session state. The URL publication marker follows that lifecycle to avoid repeated query messages during widget updates.
