# Pitwall Lab — correção da interface compartilhada

Created by: MBPaschoal
Status: implemented; public deployment verified
Type: implementation and verification report
Date: 2026-10-27

## Diagnóstico e correção

O problema era estrutural: regras CSS repetidas, espaçamentos nativos somados às margens do HTML, `margin-bottom:-16px` do Markdown sobrepondo blocos e campeonatos fora do elemento que deveria estilizar seus cards. O cabeçalho nativo transparente também interceptava os cliques dos controles próprios.

- [CSS único](../../frontend_assets/pitwall.css), [composição HTML](../../pitwall_ui.py) e [leitor de contexto](../../pitwall_ui_dados.py) separados.
- Hero, mapa, coluna técnica e campeonatos estão na mesma hierarquia HTML com CSS Grid. Nenhuma regra depende de uma temporada específica.
- Busca local por GP/cidade/circuito da temporada e por pilotos do GP selecionado; preferências reais da sessão. Links dos campeonatos preservam temporada e rodada e abrem as tabelas completas.
- Menu adaptável ao viewport, controles acessíveis, navegação nas quatro telas e seis abas mantidas. Camada do cabeçalho deixa passar os cliques, preservando o botão nativo de reabrir o menu.
- Snapshot oficial de Austin/R18: 23 pilotos no campeonato e 11 construtores. Não se transfere esse campeonato para outra rodada ou temporada; não se reconstrói campeonato por soma parcial de resultados.
- Campos ausentes ocupam a mesma composição com lacunas explícitas. Sem clima ou pontuação fictícios.

## Fidelidade e verificação visual

Referência: imagem fornecida pelo proprietário, 1672×941, SHA-256 `48b935f724fdf8de7b04899fa7fd6ce15fb68132453972af1948596c2b2cbdb2`.

Em 2024, 2025 e 2026, o navegador mediu os mesmos valores em 1672×941:

| Elemento | x | y | largura | altura |
|---|---:|---:|---:|---:|
| Cabeçalho | 307 | 64 | 1333 | 154 |
| Grade principal | 307 | 289 | 1333 | 375 |
| Campeonatos | 307 | 678 | 1333 | 235 |

A referência inicia a grade em y=289 e os campeonatos em aproximadamente y=677. Os cards inferiores cabem no primeiro viewport. Conferidos também 1440×900, 1024×768 e 390×844, sem transbordamento horizontal da página ou do elemento principal. [Medições](geometria.json), [2024](local-2024-1672x941.png), [2025](local-2025-1672x941.png), [2026](local-2026-1672x941.png), [mobile](local-2026-390x844.png).

Busca por Leclerc, preferência de abrir fontes, navegação para tabelas completas, quatro telas, comparação de equipes e abertura/fechamento do menu móvel foram exercitados no navegador. A revisão independente confirmou as correções de parsing de URL, da aba de equipes e da apresentação por temporada.

Não se certifica identidade pixel a pixel de 100%. Permanecem diferenças de imagem, geometria do mapa, ícones e pequenos detalhes tipográficos. A interface também deve apresentar os fatos reais: resultado observado, dados ausentes e pontuações oficiais, em vez dos valores ilustrativos da referência.

## Ativos e fontes

A vista aérea anterior não tinha o mesmo enquadramento da referência. Foi criada uma [ilustração IA](../../dashboard_assets/circuit/americas-illustration-20261027.png), identificada na interface e no catálogo. O mapa foi derivado da geometria vetorial existente, preservando a atribuição CC BY-SA 4.0. Originais anteriores permanecem preservados na raiz. [Atribuições](../../dashboard_assets/circuit/ATRIBUICOES.md).

Dados técnicos descritivos de Austin conferidos na [página oficial F1 de 2026](https://www.formula1.com/en/racing/2026/united-states), no [guia oficial do circuito](https://www.formula1.com/en/latest/article/circuit-guide-everything-you-need-to-know-about-the-circuit-of-the-americas.3OjhBbugiQRmN4FnlpBtBc) e no [próprio COTA](https://circuitoftheamericas.com/blog/2014/10/25/austin-circuit-of-the-americas-get-high-praise-from-formula-one-drivers-teams/). Altitude e DRS ausentes permanecem ausentes. Metadados específicos de 2026 não são projetados retrospectivamente para 2024/25.

## Verificação técnica e preservação

- 78 testes relevantes passaram: app, leitores, catálogo, estados de Austin, exportador, contexto editorial e tempos de sessão.
- A suíte de tempos possui um caminho temporário fixo na pasta do Hermes. O harness desta verificação substituiu somente essa variável por `tempfile.gettempdir()`, sem alterar o teste ou produto.
- 50 testes passaram no pacote exportado isolado, sem dados brutos, cofre ou modelo.
- [64 arquivos científicos protegidos](preservacao.json) mantiveram os hashes esperados. Não houve coletor, treino, inferência, recalibração ou alteração da emissão congelada.
- Exportação conserva baseline científico, allowlist, manifesto, hashes e bloqueios de sobrescrita. A mudança preexistente no teste distribuído foi preservada em cópia de segurança antes da atualização; seus três critérios de estilo foram mantidos na origem, adaptados à nova composição.

## Publicação

Commit de implementação `8aa088578918cb9b2cc1a0c114b37ef87cb2dccc` enviado a `origin/main`. A nova composição foi confirmada em uma nova aba pública do Streamlit, com Austin/R18 selecionado pelo link, ilustração IA, campeonatos oficiais e sem erro de importação. A inspeção identificou uma sobreposição específica do Cloud: a barra “Fork/GitHub” cobria o perfil. Ela foi ocultada pelo seletor próprio `stToolbarActions`, preservando o botão independente de abrir a navegação.
