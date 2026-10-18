# Pitwall Lab

Created by: MBPaschoal
Status: active
Type: project context
Updated: 2026-10-18

## Objetivo

Aprender ciência de dados com Fórmula 1 e, futuramente, estimar probabilidades de pódio em um dashboard.

## Estado documentado

O [README](../README.md) registra a etapa 5: avaliação final retrospectiva do modelo v1 **congelado**, sem novo ajuste, em 2025. **2025 passou de reservado a avaliado para esta versão e não poderá ser tratado como intocado em experimentos posteriores.** Não houve dashboard, coletores, nova consulta à Jolpica ou regeneração da base histórica.

## Avaliação final congelada — etapa 5, 2026-10-18

- O [plano final](../docs/avaliacao_final_v1.md) foi registrado antes de abrir o teste. SHA-256: `7b67a47d1136dc02bc24236dfbf6acb8e9e4e646a6d9cb68cba09a4fc6da8983`. Modelo, metadados, plano v1 e treinador mantiveram seus bytes.
- O script `avaliar_modelo_v1.py` usa exclusivamente teste e esquema como fontes de dados; faz inferência com o pipeline local salvo, sem `fit`, `fit_transform`, `partial_fit`, recalibração ou escolhas orientadas pelo teste.
- 480 registros de piloto por GP preparados; 479 receberam previsão; 478 elegíveis com alvo conhecido entraram nas métricas probabilísticas. Os rankings compartilham **22 dos 24 GPs**, sem atribuir zero aos dois excluídos.
- Espanha/rodada 9: alvo de `stroll` desconhecido, mas previsão gerada. São Paulo/rodada 21: `bortoleto` inelegível por classificação ausente na base. São fatos da fotografia preparada; não foram investigadas causas com novas consultas.
- Modelo: log loss 0,2033 e Brier 0,0585, ante 0,4238 e 0,1279 da constante congelada. Ranking: média 2,3182 contra 2,2727 da classificação; ambos acertaram os três integrantes em 8/22 GPs (36,36%). A vantagem média é pequena; houve empate nos pódios completos.
- As três execuções reais produziram os mesmos onze artefatos. Guardas registraram zero chamadas de ajuste e zero rede; o estado em memória de três pipelines e 16 arquivos congelados permaneceu igual. Um oráculo separado, sem retreinar nem importar o avaliador, reconstruiu probabilidades a partir dos parâmetros salvos e conferiu métricas, calibração e rankings.
- Os 109 testes passaram antes da abertura real de 2025, incluindo dados sintéticos de teste para invariância a alvos, cobertura incompleta, períodos incorretos, ausência de ajuste e proteção contra sobrescrita.
- [Resultados e limites](../reports/avaliacao_final_v1/relatorio.md), [métricas](../reports/avaliacao_final_v1/metricas.json), [comparação descritiva com 2024](../reports/avaliacao_final_v1/comparacao_2024.json), [cobertura por GP](../reports/avaliacao_final_v1/cobertura_gps.csv) e [manifesto](../reports/avaliacao_final_v1/manifesto.json).
- [Revisão independente da etapa 5](../reports/revisao_final_v1.md): aprovada por `openai-codex/gpt-6-astra`, com identidade efetiva verificada no registro de uso; 109 testes sem falhas, contraprovas e duas reproduções adicionais. Implementação por `openai-codex/gpt-5.6-terra`. Nenhum bloqueio encontrado; nenhuma mudança metodológica após observar 2025.

A comparação com 2024 usa temporadas e denominadores distintos; não sustenta significância estatística, causalidade ou superioridade futura. Permanecem a dependência entre participantes do mesmo GP, o pequeno número de temporadas e as revisões retrospectivas das fontes. Os registros abaixo descrevem períodos anteriores, quando 2025 ainda estava reservado.

## Execução verificada da etapa 4 — 2026-10-18

- O [plano fixado antes do treino](../docs/experimento_modelo_v1.md) teve SHA-256 `d6c671526aafe1ca8a1a6b98934a1d1915eb7a102872d51e5385991257fec569` registrado antes do primeiro ajuste.
- A rotina leu somente `treino.csv`, `validacao.csv` e `colunas.json`; não abriu nem avaliou 2025, não chamou API e não executou coletores/preparador.
- Foram ajustadas 1.319 linhas elegíveis e rotuladas de treino. Em 2024, as 479 linhas e os 24 GPs ficaram cobertos e avaliáveis pelas regras fixadas.
- O modelo teve log loss 0,2296 e Brier 0,0709, ante 0,4233 e 0,1277 da constante de treino. No top 3, obteve média 1,96 e 6/24 GPs com os três integrantes, contra 1,88 e 4/24 para o ranking da classificação. As diferenças da troca numérica ficaram nos últimos dígitos e não alteraram conclusões.
- Os 100 testes passaram, incluindo as duas regressões geométricas do gráfico de calibração e a contraprova simulada de multiplicação matricial, avisos numéricos como erro no ajuste/previsão, abertura exclusiva das três fontes permitidas, isolamento treino/validação, colunas proibidas, alvo desconhecido, cobertura parcial, bloqueio de 2025/rede, reprodutibilidade e proteção contra sobrescrita.
- As duas execuções reais seguidas com `numpy==1.26.4` geraram bytes idênticos para os dez artefatos de `models/modelo_v1/` e `reports/modelo_v1/`, sem `RuntimeWarning` nem `ConvergenceWarning`.
- A fotografia anterior de `models/modelo_v1/` e `reports/modelo_v1/` foi movida explicitamente, com hashes conferidos antes e depois, para backup único fora do repositório antes da regeneração autorizada.
- O bloqueio numérico foi resolvido ao fixar `numpy==1.26.4`: a contraprova simulada com a fotografia anterior 2.0.2 emitia `RuntimeWarning` em multiplicação matricial; com 1.26.4 não emitiu. Isso documenta uma incompatibilidade observada nesta máquina, não uma afirmação sobre a causa interna do BLAS. O código agora converte `RuntimeWarning` em erro no ajuste e na previsão, sem ocultá-lo.

Os resultados de 2024 são retrospectivos e de desenvolvimento: não provam generalização para 2025. Coeficientes e probabilidades não recebem interpretação causal; as limitações de revisões retrospectivas, pequena janela temporal e dependência entre pilotos do mesmo GP permanecem.

## Revisão do Codex da etapa 4 — 2026-10-18

Revisado o commit [9a3b7b8](https://github.com/mbpaschoal/pitwall-lab/commit/9a3b7b832334888af799e981cd173f26339c28d2), identificado pelo conector GitHub e correspondente ao HEAD local. Nenhum problema bloqueante encontrado no escopo do experimento v1.

- Os 100 testes passaram e `pip check` não encontrou dependências quebradas.
- Duas reproduções do experimento em pasta temporária geraram os mesmos dez artefatos publicados, byte a byte. Uma guarda de abertura de arquivos permitiu somente `treino.csv`, `validacao.csv` e `colunas.json` dentro de `data/`; a rede foi bloqueada. Não foram abertos dados reais de 2025.
- Uma implementação de conferência separada recalculou medianas, médias e escalas das 1.319 linhas elegíveis e rotuladas de treino e as 479 probabilidades de validação a partir dos coeficientes. Log loss, Brier, rankings e contagens coincidiram com os relatórios.
- O ranking identificou 47 integrantes de pódio contra 45 da referência de classificação nos mesmos 24 GPs. A vantagem é pequena e não foi apresentada como evidência de significância ou generalização.

**Registro histórico da etapa 4, proposta agora executada na etapa 5:** congelar o experimento v1 e suas regras, definir o tratamento de cobertura/alvos desconhecidos da avaliação final antes de consultar seus resultados e então avaliar o teste reservado sem reajuste orientado por ele. Manter explícita a natureza retrospectiva. A revisão da etapa 4 não alterou código, dados ou artefatos do modelo.

## Revisão verificada da etapa 3 em 2026-10-18

O commit [467fc19](https://github.com/mbpaschoal/pitwall-lab/commit/467fc19d74a090db73634f3db89132f6557a9f75) foi identificado pelo conector GitHub e correspondia ao HEAD local naquela revisão da etapa 3, sem diferenças nos arquivos rastreados na conferência inicial.

- Os 82 testes passaram no ambiente virtual existente.
- A preparação foi executada offline com saídas em pasta temporária: 19 artefatos idênticos aos publicados, incluindo o comprovante.
- Uma conferência independente dos JSON originais recalculou as posições de classificação, médias, contadores e IDs das janelas das 2.279 linhas, sem divergências. Foram conferidos 120 hashes de fontes e 18 hashes de saídas.
- A base contém 114 corridas; 1.320 linhas de treino (2021–2023), 479 de validação (2024) e 480 de teste reservado (2025). Essas são contagens de integridade, não métricas de previsão.
- Não foram executadas consultas à API, treinamento ou avaliação de desempenho em 2025.

Conclusão da revisão: nenhum problema bloqueante encontrado para encerrar a preparação histórica. Antes de treinar, definir elegibilidade dos participantes, tratamento de entradas ausentes e posições de classificação ambíguas; manter alvos desconhecidos distintos de negativos. Congelar essas regras antes da avaliação final. As limitações sobre revisões históricas e o horário de encerramento desconhecido continuam válidas, conforme o [protocolo](../docs/protocolo_temporal.md).

## Decisões e restrições

- Preservar as entregas das etapas anteriores.
- Preparar dados offline a partir de fontes validadas e caches completos.
- Separar entradas, identificação, alvos e desfechos de auditoria.
- Usar apenas informações anteriores ao corte temporal e registrar suas limitações.
- Tratar ausências explicitamente, sem convertê-las automaticamente em desempenho zero.
- Não substituir saídas diferentes sem preservar backup explícito, conforme o README.

## Próximas ações

1. Interpretar a [avaliação final v1](../reports/avaliacao_final_v1/relatorio.md) junto da cobertura por GP, sem extrapolar os 22 GPs avaliáveis para os 24.
2. Registrar dúvidas e hipóteses em `inbox/` e `ideas/`, com fontes.
3. Qualquer versão futura precisa de novo plano e avaliação honesta: 2025 já foi observado e não é mais teste intocado. Não ajustar o v1 nesta tarefa.

## Fontes

- [[notes/Pitwall Lab - Index]]
- [Protocolo temporal](../docs/protocolo_temporal.md)
- [Dicionário de variáveis](../docs/dicionario_variaveis.md)
- [Relatório de qualidade](../reports/historico/qualidade.md)
- [Relatório do modelo v1](../reports/modelo_v1/relatorio.md)
