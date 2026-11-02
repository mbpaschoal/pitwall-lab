# Controles móveis — 0.8.17

Created by: MBPaschoal
Status: completed
Type: interface fix evidence

A captura do usuário revelou duas falhas: bandeira desenhada apenas com linhas, sem quadrados preenchidos, e títulos de expansores deslocados da seta. O SVG agora tem quadrados pretos e brancos também no estado selecionado. A margem inferior de 12 px herdada pelos parágrafos foi removida somente nos cabeçalhos dos expansores. Entrelinha, identidade visual e controles nativos preservados; área mínima de toque de 44 px.

Validação focal local: 24 cenários Chromium + 24 WebKit, seis telas × PT/EN × 390/1440 px. A bandeira é verificada por pixels pretos/brancos e os expansores por diferença entre centros verticais, margens e abertura/fechamento. Suíte focal: 33 testes. Pacote: 141 verificações; 614 arquivos científicos e 28 de emissão/registro intactos. Confirmação pública: versão 0.8.17 e build conferidos em sessão nova; 24/24 cenários por motor passaram, incluindo área mínima de toque de 44 px. Recibos em [public-validation.json](public-validation.json), [Chromium](public-chrome/controls.json) e [WebKit](public-webkit/controls.json). Não houve acesso ao iPhone físico do usuário.

English: the race icon now uses filled black/white checks in every state. Native expander labels no longer inherit the 12 px paragraph margin; line spacing and visual identity are retained, with 44 px touch targets. Local coverage: 24 Chromium + 24 WebKit scenarios across six screens, PT/EN and desktop/emulated mobile. Targeted tests and portable checks passed; protected data are unchanged. Public version/build and all 48 focused scenarios passed; see the linked receipts. No physical iPhone was accessed.

CI main/tag aprovado. [Recibo CI](ci.json) · [ZIP público: 475 arquivos conferidos](release-zip.json) · [Captura pública WebKit/celular](public-webkit/390-pt-expanders.jpg).

Main/tag CI passed. All 475 public ZIP members match the tagged manifest. Build: `6e672756d862029d6e9651c8d8c502f349c067adedb04b18f8911224dd179023`.
