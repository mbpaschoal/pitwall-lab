# Pitwall Lab

Created by: MBPaschoal
Status: active
Type: project context
Updated: 2026-10-18

## Objetivo

Aprender ciência de dados com Fórmula 1 e, futuramente, estimar probabilidades de pódio em um dashboard.

## Estado documentado

O [README](../README.md) registra a etapa 4 concluída: um primeiro modelo logístico de probabilidade individual de pódio foi treinado somente com 2021–2023 e avaliado retrospectivamente em 2024. Não é previsão emitida antes de corrida, não há dashboard e 2025 permanece teste final reservado. Este registro deriva de execução local offline; não executou coletores nem revalidou a base histórica.

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

1. Interpretar o [relatório v1](../reports/modelo_v1/relatorio.md) junto do protocolo, sem transformar validação de 2024 em teste final.
2. Registrar dúvidas e hipóteses em `inbox/` e `ideas/`, com fontes.
3. Antes de qualquer avaliação de 2025, congelar formalmente a decisão de promover ou revisar este experimento; não ajustar escolhas usando esse teste reservado.

## Fontes

- [[notes/Pitwall Lab - Index]]
- [Protocolo temporal](../docs/protocolo_temporal.md)
- [Dicionário de variáveis](../docs/dicionario_variaveis.md)
- [Relatório de qualidade](../reports/historico/qualidade.md)
- [Relatório do modelo v1](../reports/modelo_v1/relatorio.md)
