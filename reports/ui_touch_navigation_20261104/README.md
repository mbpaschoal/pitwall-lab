# Controles de idioma e menu móvel — 0.8.31

[English](README.en.md)

Created by: MBPaschoal

Status: publicada 0.8.31; CI e aceite público aprovados

Type: evidência de entrega

A auditoria pública anterior recomendou ampliar o alvo das bandeiras e tornar inequívoca a seleção no menu móvel de duas linhas. Esta entrega mantém a Jornada do fã: mesmas cores, fontes, fotografias e ícones. Os botões passam a medir 44 × 50 CSS px, com bandeiras pequenas e 8 px entre as células. O texto do menu fica centralizado com o ícone; no celular, um sublinhado dentro da célula selecionada substitui a borda superior. Desktop conserva seu marcador anterior. Links alternativos recebem a mesma indicação móvel.

## Evidência local

- 42 testes focais; 144 testes portáteis, distribuídos em 17 módulos: aprovados.
- Chromium: 24/24 cenários. WebKit: 24/24. Cada motor cobre seis páginas × PT/EN × 390/1440 px, com duas trocas de idioma por cenário, toques/cliques nas bordas, 44 × 50 px e posição do marcador. [Chromium](local-chromium-final/controls.json), [WebKit](local-webkit-final/controls.json).
- Resiliência: quatro contextos, seis destinos por teclado em cada um, troca de idioma e recuperação tardia dos controles com foco preservado: aprovados. [Evidência](local-resilience-final/resilience.json).
- Versão, 18 pares de documentos e limites de confiança dos workflows: aprovados. Dependências de segurança da 0.8.30 preservadas.
- Pacote canônico: 481 membros do ZIP conferidos byte a byte. [Build, hash e tamanho](package-final.json). A árvore servida foi sincronizada apenas com os arquivos alterados pelo exportador.
- [Verificação dos arquivos protegidos](preservation.json): comparação com o commit de origem. Nenhum coletor, treino ou emissão executado.

## Falhas preservadas e aprendizado

O segundo CI aprovou os quatro casos de Pilotos e a navegação, mas parou em um timeout de download do CSV de pneus, em inglês no desktop. O processo saiu sem imagem de falha: a promessa de espera era criada antes de aguardar o clique e podia rejeitar sem tratamento enquanto a ação ainda esperava. O teste agora centraliza o botão, confere sua acionabilidade sem forçar e aguarda clique/download com `Promise.all`; falhas ficam explícitas no recibo. A causa específica de bloqueio daquele clique permanece não demonstrada. [Evidência do segundo CI](ci-second/analysis.json).

O primeiro CI da branch falhou em `aceite_pilotos_atualizacao.cjs`, com “Stale Max starts” no perfil em inglês. A rotina original passou nos quatro contextos locais; a falha remota não registrou o valor lido. A hipótese de leitura durante a atualização do DOM permanece uma inferência. O aceite agora aguarda o número exato de largadas da fonte, sem aceitar outro valor, e registra métricas/identidade em falhas. Corrige também o recibo parcial: passa a distinguir execução em andamento, falha e sucesso dos quatro casos. [Falha e evidência original](ci-first/analysis.json). A rotina ajustada passou nos quatro contextos locais. Uma [contraprova](starts-counterexample.json) exigiu 68 largadas, quando a fonte e a página têm 67: o valor incorreto foi rejeitado e o recibo registrou a falha.

O primeiro teste móvel encontrou toque na bandeira vizinha ao tocar muito perto da borda. Aumentar somente a largura não bastou; a mesma falha persistiu com `touch-action: manipulation` e intervalo de 8 px. A sonda comparou intervalos maiores e a atribuição dos eventos ao botão inteiro; a solução compacta passou a usar `pointer-events: none` nos descendentes do botão, mantendo o botão interativo e o nome acessível. Os dois motores passaram a sequência original de toques nas bordas. Evidências iniciais e sondas permanecem nesta pasta. Isso documenta o comportamento observado, sem atribuir ao serviço uma causa não comprovada.

A primeira lista local de sincronização do pacote omitiu os dois documentos de navegação e foi corretamente recusada antes de qualquer cópia. A lista foi corrigida para os oito arquivos canônicos esperados; nenhuma proteção do exportador foi retirada.

O navegador simula celular; não houve teste em aparelho físico nem certificação WCAG. Testes locais, CI, release e hospedagem pública são camadas distintas. A aprovação local não demonstra disponibilidade contínua do Streamlit.

## Publicação e aceite concluídos

A [release 0.8.31](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.31) está publicada e o [Pitwall Lab](https://pitwall-lab.streamlit.app/) serviu o build `06f98e667d64f02b64bc56c587aeaf7c31c19606e1c7431a92574c74e92f3a24` nos quatro contextos de conferência. [Resumo estruturado](summary.json).

| Camada | Resultado e evidência |
|---|---|
| CI da branch | 405 testes de código, 144 portáteis, dez contraprovas do verificador e 13 suítes de navegador: aprovado. [Execução](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41837228872), [recibo](ci-branch-final.json). |
| CI de main e tag | Ambos aprovados no commit `80cef1760a12ad2e46e5083b482b5b9c79e9ae8a`. [Main](ci-main-final.json), [tag/release](ci-tag-final.json). |
| Versão, build e fotos públicos | Quatro contextos PT/EN × 390/1440 px, fotos decodificadas e hashes corretos, todos na primeira tentativa. [Recibo](publication-final/publication.json). |
| Páginas e bandeiras públicas | 24/24 cenários em [Chromium](public-controls-chromium/controls.json) e 24/24 em [WebKit](public-controls-webkit/controls.json). Seis páginas; 96 trocas de idioma nas bordas; alvos mínimos medidos de 44 × 50 px; marcador móvel dentro da própria célula. |
| Menus públicos | Oito fluxos com seis destinos cada: 48 cliques/toques reais, mantendo GP, temporada e sincronização do endereço externo. [Chromium](public-menu-chromium/interactions.json), [WebKit](public-menu-webkit/interactions.json). |
| ZIP oficial | 481 membros conferidos em CI; 665.860.833 bytes. O digest do anexo GitHub coincide com o ZIP do CI e o pacote local. [Prova do CI](release-proof.json), [metadados da release](release.json). |

São 60 cenários públicos concluídos, sem repetição de caso nesta versão. O celular foi simulado. O resultado corresponde à janela de teste e não estabelece disponibilidade permanente da hospedagem. As duas falhas iniciais de CI permanecem documentadas acima; uma prévia de CSS sobre a 0.8.30 é identificada como temporária em `live-css-preview.json` e não foi contada como publicação.

[Captura pública móvel PT](publication-final/390-pt-0-Metodologia.jpg) · [captura pública desktop EN](publication-final/1440-en-0-Corridas.jpg). A [contraprova de espera rejeitada](download-counterexample.json) confirmou o recibo de falha e a captura; seu limite de observação inicial também permanece explícito.
