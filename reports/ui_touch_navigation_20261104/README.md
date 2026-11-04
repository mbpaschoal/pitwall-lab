# Controles de idioma e menu móvel — 0.8.31

[English](README.en.md)

Created by: MBPaschoal

Status: validação local concluída; CI e publicação pública pendentes

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

O primeiro CI da branch falhou em `aceite_pilotos_atualizacao.cjs`, com “Stale Max starts” no perfil em inglês. A rotina original passou nos quatro contextos locais; a falha remota não registrou o valor lido. A hipótese de leitura durante a atualização do DOM permanece uma inferência. O aceite agora aguarda o número exato de largadas da fonte, sem aceitar outro valor, e registra métricas/identidade em falhas. Corrige também o recibo parcial: passa a distinguir execução em andamento, falha e sucesso dos quatro casos. [Falha e evidência original](ci-first/analysis.json). A rotina ajustada passou nos quatro contextos locais. Uma [contraprova](starts-counterexample.json) exigiu 68 largadas, quando a fonte e a página têm 67: o valor incorreto foi rejeitado e o recibo registrou a falha.

O primeiro teste móvel encontrou toque na bandeira vizinha ao tocar muito perto da borda. Aumentar somente a largura não bastou; a mesma falha persistiu com `touch-action: manipulation` e intervalo de 8 px. A sonda comparou intervalos maiores e a atribuição dos eventos ao botão inteiro; a solução compacta passou a usar `pointer-events: none` nos descendentes do botão, mantendo o botão interativo e o nome acessível. Os dois motores passaram a sequência original de toques nas bordas. Evidências iniciais e sondas permanecem nesta pasta. Isso documenta o comportamento observado, sem atribuir ao serviço uma causa não comprovada.

A primeira lista local de sincronização do pacote omitiu os dois documentos de navegação e foi corretamente recusada antes de qualquer cópia. A lista foi corrigida para os oito arquivos canônicos esperados; nenhuma proteção do exportador foi retirada.

O navegador simula celular; não houve teste em aparelho físico nem certificação WCAG. Testes locais, CI, release e hospedagem pública são camadas distintas. A aprovação local não demonstra disponibilidade contínua do Streamlit.

## Publicação

Pendente de CI e confirmação da versão/build realmente servidos.
