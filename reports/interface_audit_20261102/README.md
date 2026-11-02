# Revisão integral da interface — 0.8.16

Created by: MBPaschoal
Status: completed
Type: interface audit and release evidence

Português · English below

A correção está publicada no [dashboard](https://pitwall-lab.streamlit.app/) e na [release 0.8.16](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.16). A versão e o build foram conferidos em sessões públicas novas. Os cenários da matriz terminaram sem falhas conhecidas.

A captura do usuário revelou o pódio sobre o aviso de coleta e o menu fixo encobrindo o circuito. A revisão ampliada encontrou também colisões de retratos/estatísticas, créditos de foto interceptando cliques, controles sem espaço para texto ampliado e links que perdiam temporada, GP ou filtros. Foram corrigidos o fallback indevido para outro piloto e a contaminação da temporada em buscas curtas.

Os blocos agora reservam espaço no fluxo da página e a área rolável termina acima do menu, inclusive após mudanças de altura. Cabeçalho, seletores, ícones e rótulos dos controles de Pilotos refluem. Fotos, fontes e cores da identidade atual foram preservadas.

A validação pública encontrou uma falha adicional do wrapper do Streamlit: links podiam mudar a página interna sem atualizar a URL externa, e o retorno documental podia aninhar o site. A 0.8.16 publica a rota pelo canal nativo no início da sessão e retorna dos documentos com uma atualização nativa atômica. Calendário, capítulos e documentos conservam o destino após recarregar. A tag 0.8.15 permanece intacta.

## Validação pública

| Verificação | Resultado |
|---|---|
| Seis telas, PT/EN, computador/celular: Chromium e WebKit | 120 posições de rolagem + 14 provas adicionais por motor, sem falhas |
| Composição, fotografias, CSS, H1, alvos e overflow | 24/24 casos Chromium |
| Inventário de páginas/estados, incluindo sete documentos e perfis/duelos | 100/100 estados, 3.814 âncoras; nenhum fragmento, contexto ou query inválido |
| Cliques reais, filtros, idiomas, favoritos, documentos, cartas e downloads | 56/56 fluxos Chromium + 56/56 WebKit |
| Retorno documental, URL externa/interna e recarregamento | Passaram nas quatro combinações PT/EN × 390/1440 px |
| Reprodução do cenário original | 4/4 casos na versão final |
| Foco, retorno ao topo, seis destinos e movimento reduzido | 8/8 jornadas |
| Endereços externos no DOM e canvas | 119/119 alcançáveis: 33 HTTP 200 + 86 HTTP 206 |
| Pacote portátil e publicação | 141 verificações locais; CI main/tag e release aprovados |
| ZIP público | 475/475 arquivos conferidos contra o manifesto imutável da tag |

As provas adicionais cobrem texto ampliado no cabeçalho e nos dois controles de Pilotos, além da mudança de altura da janela. A rodada local também incluiu 320 px, Chromium/WebKit e calor/perfil com texto duplicado. O inventário distingue 2.936 âncoras visíveis e 878 ocultas. Os quatro CSVs científicos baixados têm 86.031 bytes e SHA idêntico ao original; os cartões SVG também foram baixados e inspecionados. O link do canvas foi clicado no público e abriu Abu Dhabi 2024/24 corretamente. Os 54 PDFs adicionais do canvas têm assinatura PDF válida.

- [Resumo público verificável](public-validation-0816.json) · [links e fluxos](links-final-receipt-0816.json).
- [Chromium: rolagem e reflow](public0816-rolagem-chromium/scroll-audit.json) · [WebKit](public0816-rolagem-webkit/scroll-audit.json) · [composição visual](public0816-visual-chromium/acceptance.json).
- [100 estados](public0816-links/links-browser.json) · [56 fluxos Chromium](public0816-interactions/interactions.json) · [56 fluxos WebKit](public0816-webkit-interactions/interactions.json).
- [Build servido](deploy-check.json) · [CI](ci-0816.json) · [integridade do ZIP público](release-zip.json).
- [Captura corrigida PT/celular](public-critical-390-pt.jpg) · [EN/celular](public-critical-390-en.jpg) · [PT/computador](public-critical-1440-pt.jpg) · [EN/computador](public-critical-1440-en.jpg).

## Integridade e limites

Commit da entrega: `2326477c25dac7601b3db7d160c012e9e685cc13`, tag `v0.8.16`. Build: `cf5f36655486530283b3dcc800aad0dbe40ab6a4331170df1150fdf5b008415e`. Baseline científico: `05eec0b70b24abf9a68dae45aac36730eefb5bc5`.

Os [614 arquivos científicos + 28 de emissões/registro](protected-integrity-after.json) permanecem byte a byte intactos. O trabalho foi feito em checkout isolado, preservando a pesquisa concorrente no cofre. Não houve coleta, treinamento, inferência ou alteração de probabilidades.

A validação móvel é emulada; não houve teste em iPhone físico ou leitor de tela. O stress duplica métricas de fonte/linha, sem representar zoom nativo ou Dynamic Type. Não é uma certificação WCAG. Fotografias de fundo com títulos fazem parte da composição aprovada; retratos sobre conteúdo foram tratados como defeitos. Canvas/Plotly e iframes têm testes funcionais próprios, pois a análise de texto DOM não cobre seu interior. Disponibilidade HTTP confirma esta execução, sem garantir serviços externos futuros.

Os testes permanentes estão em `tests/browser/`, com [instruções PT/EN](https://github.com/mbpaschoal/pitwall-lab/blob/v0.8.16/tests/browser/README.md). A espera inclui hidratação dos controles, idioma e fontes; não força cliques nem ignora falhas geométricas. A sincronização segue o [ciclo de sessão documentado pelo Streamlit](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#caveats-and-limitations): navegação HTML inicia uma sessão; reruns de widgets retêm o marcador e publicam suas próprias mudanças de query.

## English

The fix is live in the dashboard and release 0.8.16. Fresh public sessions confirmed the expected version/build. All scoped checks passed: 292 interface cases, 100 route states, 56 functional flows per engine, eight motion/focus journeys and four reproductions of the original collision. PT/EN, desktop and emulated mobile were checked in Chromium/WebKit. All 119 inventoried external URLs were reachable; all 475 public ZIP members match the tagged manifest.

Content now reserves space above the persistent dock. Portraits, photo credits, headers, selectors and driver controls no longer collide in the tested matrix. Season/GP/profile/filter context is retained. Missing historical coverage stays explicit without replacing the requested driver. Public URL synchronization and atomic document return fix stale reload destinations and nested wrappers. Photographs, typography and colors retain the existing identity; the 0.8.15 tag is preserved.

All 642 protected scientific/emission hashes remain unchanged. Work used an isolated checkout without collecting data, training or changing probabilities. Mobile coverage is emulated, not a physical iPhone or screen-reader certification. Doubled-font stress is not native browser zoom. DOM geometry excludes intentional hero backgrounds and has separate functional checks for canvas/iframes. External HTTP reachability is an observation for this run, not a promise of future availability. Detailed receipts above retain the provenance of each check and release artifact.
