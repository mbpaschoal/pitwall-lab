# Publicação da navegação suave — 0.8.12

Created by: MBPaschoal
Status: published and verified
Type: publication receipt

A entrega publica as três melhorias do commit `57a8471`: feedback discreto nos controles, navegação por âncoras com foco e entrada única dos passos de Como funciona. Preferências de movimento reduzido têm precedência; idioma, GP, filtros, identidade e dados são preservados.

As tags 0.8.10 e 0.8.11 permanecem intactas. A 0.8.12 foi preparada em checkout isolado a partir desse commit, sem incluir as pesquisas em andamento que permanecem no diretório compartilhado. Não foi usado stash, reset ou reescrita do histórico. O branch da publicação é `codex/publicar-motion-0811`, commit `3aaff725c6efe377b18e005031d9dd22be368c26`, enviado à main remota e à tag `v0.8.12`.

O exportador oficial produziu 475 arquivos e o ZIP, verificado membro a membro. Os 141 testes portáteis e 48 visitas funcionais passaram no pacote isolado. [Recibo do pacote](package-0812.json). O checkout e pacote anteriores foram preservados.

Em sessão pública limpa, o site serviu a versão 0.8.12 e o build `87a68758a2a2017e9c66ce1946af3d7baf7ed359cfad03f3fb3dc5c9e5ddd0df`, igual ao manifesto do pacote. [Versão e build](deploy-check.json). A comprovação do comportamento no site é registrada separadamente da validação local.

Celular significa viewport de 390 px e toque emulados. Não se realizou teste em aparelho físico ou leitor de tela. Os efeitos foram adaptados localmente; nenhuma engine ou serviço externo foi instalado.

English: release 0.8.12 publishes the three validated motion/navigation improvements from an isolated checkout, preserving the original local 0.8.10 tag and the ongoing research. The stock exporter produced 475 files; 141 portable tests and 48 package navigation visits passed. Public build and behavior, CI and uploaded ZIP have separate receipts. Mobile checks are emulated; no physical handset or screen reader was tested.

A revisão final removeu `aria-pressed` do controle cujo texto muda com a ação disponível. Ele é um botão de ação nativo, com nome igual ao texto visível, acionável por Space/teclado ou toque. Os estados visual e funcional continuam preservados. A correção recebeu versão própria, sem reescrever tags.

Uma primeira tentativa do aceite público leu o cabeçalho durante um rerun. O harness passou a aguardar a tela de destino, o estado ocioso e a versão esperada conjuntamente, mantendo todas as asserções de versão, idioma, foco e movimento.

O aceite público da versão final passou **48 visitas funcionais** em oito combinações de idioma/tamanho/movimento e **24 cenários visuais** das seis telas. Os testes verificam a versão servida, teclado/Space, toque, foco, preservação de contexto, ausência de transbordamento e entrada única. [Funcional](public-motion-0812/browser.json) · [Visual](public-visual-0812/acceptance.json).

A release final está concluída: **CI de main e tag aprovado**, todos os 475 membros do ZIP público iguais ao manifesto da tag v0.8.12. O SHA-256 do ZIP é `42bbca9385733bab8c14b894897c25bbea1ed508a8ff6912dac6e4b0f269a0c2`, igual ao digest do GitHub e ao ZIP determinístico local. [Release](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.12) · [CI](ci.json) · [Integridade do ZIP](release-zip.json).

A preferência manual de movimento persistiu após recarregar; reativar movimento não repetiu a entrada de conteúdo já lido. A mudança da preferência do sistema em tempo real também foi respeitada nos fluxos PT e EN. [Persistência](persistence.json). [Arquivos científicos e emissão preservados](preservation-final.json).

English: final publication is complete. Both main and tag CI passed; 48 functional public visits and 24 visual scenarios passed. The public ZIP matches the tagged manifest member by member and its digest matches GitHub and the local deterministic ZIP. Reload persistence and live system-preference changes passed in PT/EN. Frozen data and predictions remain unchanged.
