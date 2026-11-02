# Controles móveis — 0.8.17

Created by: MBPaschoal
Status: local validation passed; public confirmation pending
Type: interface fix evidence

A captura do usuário revelou duas falhas: bandeira desenhada apenas com linhas, sem quadrados preenchidos, e títulos de expansores deslocados da seta. O SVG agora tem quadrados pretos e brancos também no estado selecionado. A margem inferior de 12 px herdada pelos parágrafos foi removida somente nos cabeçalhos dos expansores. Entrelinha, identidade visual e controles nativos preservados; área mínima de toque de 44 px.

Validação focal local: 24 cenários Chromium + 24 WebKit, seis telas × PT/EN × 390/1440 px. A bandeira é verificada por pixels pretos/brancos e os expansores por diferença entre centros verticais, margens e abertura/fechamento. Suíte focal: 33 testes. Pacote: 141 verificações; 614 arquivos científicos e 28 de emissão/registro intactos. Uma sessão pública nova será registrada após publicação. Não houve acesso ao iPhone físico do usuário.

English: the race icon now uses filled black/white checks in every state. Native expander labels no longer inherit the 12 px paragraph margin; line spacing and visual identity are retained, with 44 px touch targets. Local coverage: 24 Chromium + 24 WebKit scenarios across six screens, PT/EN and desktop/emulated mobile. Targeted tests and portable checks passed; protected data are unchanged. Public deployment confirmation is recorded separately. No physical iPhone was accessed.
