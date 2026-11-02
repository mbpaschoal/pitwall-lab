# Avaliação prospectiva do México — 2026

Created by: MBPaschoal
Status: implemented; publication pending verification
Type: posterior evaluation report

[English](relatorio.en.md)

A previsão prospectiva registrada para o México acertou **2 dos 3 integrantes do pódio**, contra **1 de 3 da referência da classificação**. O pódio final é Verstappen, Hamilton e Antonelli. Os favoritos congelados do Lab continuam Verstappen, Hamilton e Russell; os da classificação, Hamilton, Russell e Leclerc. Não houve acerto do pódio completo por nenhuma seleção.

A cobertura é de **22 participantes, 22 alvos conhecidos e zero exclusões**. Os cinco abandonos documentados têm alvo de pódio zero e posição oficial ausente. Ausência de linha, status desconhecido ou alvo inválido continuam impedindo a avaliação; não viram zero. As posições administrativas 18–22 de outros provedores não substituem a ausência na classificação final da FIA.

A [auditoria da emissão](auditoria_emissao.json) aprovou 32 verificações: emissão em `2026-11-01T04:32:23.054391Z`, evidência de publicação anterior à largada e inventário original preservado. Os hashes do manifesto e CSV da emissão vinculam o [anexo público](../../frontend_assets/avaliacao_posterior_mexico_2026.json) às probabilidades, ranks, elegibilidade, pilotos e equipes originais. A confirmação posterior exige encerramento observado da corrida, publicação final e captura posterior, sem usar o relógio de coleta como prova de disponibilidade prévia.

O resultado admitido é o documento **86 da FIA**, publicado em `2026-11-02T01:50:00Z`, capturado em `03:42:24.143473Z`, SHA-256 `681fc44eb9dd8e73096dcafb63d18257d344ead5617aab6fc0b1a3f2f4591cd3`. A [normalização auditada](resultado_final_normalizado.json) foi conferida visualmente no PDF e corroborada pela F1. Jolpica e OpenF1 capturados antes da incorporação das sanções têm posições/pontos divergentes; o pódio permanece igual. [Detalhes e fontes](resumo_resultado.md).

O [produtor offline](../../preparar_dashboard_race_weekend.py) aplica os alvos após conferir os bytes das fontes. O [validador público](../../pitwall/data/post_race_evaluation.py) usa apenas o anexo explícito da allowlist, sem depender de fontes privadas. Adulteração do anexo, da emissão, dos resultados, dos UTCs, da identidade ou dos campos congelados é rejeitada. O ensaio de Singapura e os resultados de Austin permanecem em seus próprios contextos.

“Acertos do Lab” mostra a comparação 2/3 × 1/3 e mantém a limitação de amostra: agora há duas corridas prospectivas avaliáveis em 2026. Duas corridas não demonstram superioridade, calibração ou capacidade futura. “Chances de pódio” conserva os três favoritos e as probabilidades publicadas. Exclusões reais exibem N/A e motivo, sem chamar uma emissão prospectiva de retrospectiva.

A versão do produto é **0.8.7**, incorporando a avaliação e preservando a entrega local 0.8.6 de apresentação dos pneus, já validada em fluxo paralelo. A correção operacional da classificação final e a preparação de São Paulo foram feitas em paralelo; não houve treinamento ou nova emissão neste trabalho. Os modelos e o baseline científico continuam congelados.

Verificações locais e públicas serão detalhadas nos recibos deste diretório. Celular significa viewport e interação por toque emulados; não representa ensaio em aparelho físico ou leitor de tela.

A publicação final usa **0.8.8**, pois o aceite CI da 0.8.7 incluiu cinco testes legados dependentes de capturas locais não publicadas. A correção mantém esses testes locais e preserva os testes CI de integridade e do pacote portátil; a tag 0.8.7 não foi reescrita. O build final será confirmado em sessão pública nova.
