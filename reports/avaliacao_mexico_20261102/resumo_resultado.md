# Auditoria posterior do resultado — México 2026/19

Created by: MBPaschoal
Status: audited with source discrepancy
Type: posterior result audit
Date: 2026-11-02

**A avaliação binária de pódio pode ser fechada para os 22 participantes usando a classificação final da FIA como autoridade. A captura atual da Jolpica está completa em cobertura, mas desatualizada na ordem e nos pontos do resultado integral.** Esta auditoria não recalculou probabilidades ou métricas, nem alterou fontes existentes.

O [documento final 86 da FIA](https://www.fia.com/system/files/decision-document/2026_mexico_city_grand_prix_-_final_race_classification.pdf), conferido visualmente na página 2, e a [tabela atual da F1](https://www.formula1.com/en/results/2026/races/1298/mexico/race-result) concordam no pódio Verstappen–Hamilton–Antonelli, em 17 classificados e cinco DNF. Não há DNS ou DSQ na corrida. A DSQ de Lawson pertence à qualificação e não deve ser aplicada à corrida.

Os 22 números, `driverId` e `constructorId` da Jolpica coincidem exatamente com os da qualificação congelada antes da corrida. Hirakawa é o carro 50, `ryo_hirakawa`/`haas`: a lacuna de ID/equipe no asset OpenF1 não justifica excluir esse participante.

A FIA final incorpora sanções posteriores a Piastri (+10 s), Colapinto (+10 s) e Gasly (+30 s). Na comparação com essa final, a [captura Jolpica](jolpica_2026_19_results_20261102T034127Z.json) e o OpenF1 local diferem em 11 posições e sete pontuações. O pódio e os 22 alvos binários de pódio continuam iguais. A Jolpica foi obtida em `2026-11-02T03:41:27.286720Z`, SHA-256 `c3ff9401f39f58edc621731371c9d7e45c3fbe03e6bf0be738fc6fa7a60565f8`.

O documento final foi publicado no índice FIA em `2026-11-02T01:50:00Z` (02:50 CET) e capturado em `03:42:24.143473Z`, SHA-256 `681fc44eb9dd8e73096dcafb63d18257d344ead5617aab6fc0b1a3f2f4591cd3`. As fontes de resultado são posteriores à emissão de referência (`2026-11-01T04:32:23Z`) e ao fim observado da corrida (`22:23:54.505Z`). Captura e hash documentam a fotografia atual; não demonstram disponibilidade histórica.

A [normalização final](resultado_final_normalizado.json) preserva posição oficial nula para DNF. O PDF não publica um texto de status nas linhas dos classificados: `status_oficial_literal` permanece nulo e `status_normalizado` explicita a interpretação. Pontos vazios no PDF permanecem nulos em `pontos_oficiais`; os zeros explícitos corroborados pela F1 ficam em `pontos_f1`. Nenhuma ausência foi transformada em alvo zero: todos os 22 registros de resultado estão presentes.

O [parecer estruturado](auditoria_resultado.json) registra os oito hashes OpenF1 conferidos, as diferenças, fontes e limites. A [imagem da página 2](fia_final_race_classification_page2.png), os [recibos oficiais](fontes_oficiais_recibos.json) e o [recibo Jolpica](jolpica_resultado_fonte.json) preservam a evidência. A conferência local é reproduzível com `python3 -B reports/avaliacao_mexico_20261102/conferir_resultado.py`, sem rede.

No estado examinado, `race_weekend.json` ainda informa resultado indisponível porque seu snapshot canônico contém resultados somente até Austin/18. Isso não contradiz o resultado posterior público. A integração deve criar um artefato posterior separado, sem substituir o snapshot prévio ou a emissão. Não houve coletor, telemetria remota, treinamento, exportação ou publicação nesta auditoria.
