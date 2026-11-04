# Sonda exploratória não aceita

Created by: MBPaschoal
Status: superseded
Type: evidência de diagnóstico

A sonda inicial comparou os glifos da fonte com a própria caixa de linha, sem considerar overflow visível; isso produz falsos positivos de corte em Abril Fatface. As imagens não demonstraram texto oculto. A inspeção também mostrou que manter duas colunas com texto muito ampliado era pouco legível. O produto foi melhorado para reorganizar os painéis por largura disponível e tamanho da fonte. O aceite canônico em `tests/browser/aceite_editorial.cjs` agora testa essa reorganização em 320 px com fonte raiz ampliada, sem usar o critério de caixa de linha desta sonda. Resultados finais ficam em `release-chromium/` e `release-webkit/`.
