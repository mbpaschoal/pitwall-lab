# Auditoria de dados para Pilotos

Created by: MBPaschoal  
Status: Validado para resultados por condições de corrida; limitações declaradas  
Type: Report

[English](README.en.md)

O [controle consolidado](consolidado_v1/gate_dados.json) libera as comparações descritivas por clima e circuito. Isso **não significa que todos os campos das fontes estejam preenchidos**: 17 compostos de pneus de treinos/classificação continuam indisponíveis e não podem sustentar cruzamentos de pneus. O [registro de 295 verificações](consolidado_v1/pendencias.csv) distingue recuperação, ausência aplicável, exclusão e limitação de fonte.

| Verificação | Resultado |
|---|---|
| Corridas principais | 66: 24 de 2024, 24 de 2025 e 18 de 2026 |
| Intervalos efetivos | Status de corrida e bandeirada; períodos de suspensão excluídos |
| Sensores | Chuva, temperaturas, umidade, pressão e vento aprovados nas 66 provas |
| Chuva registrada durante a prova | 8 corridas; não equivale a uma classificação de pista seca/molhada |
| Nuvens e código WMO | 70 amostras horárias dentro dos intervalos ativos, nas 66 provas; reconstrução ECMWF IFS/Open-Meteo |
| Resultados e largadas | 1.354 resultados, 1.340 largadas e 14 DNS |
| Limites de pneus | 30 reconstruídos na fonte alternativa; 17 registros sem volta completada e três DNS sem limites aplicáveis |
| Compostos ausentes | Nove recuperados, 30 registros órfãos excluídos, dois casos sem volta completada e 17 lacunas declaradas |
| Circuitos | 66 mapas FIA da própria edição conferidos; Suzuka tem categoria de traçado em oito |
| Preservação | 614 arquivos científicos e fontes originais com hashes inalterados |

## Correções que mudam a interpretação

- `session_type=Race` também pode identificar Sprint. A corrida principal é selecionada pelo nome literal `Race`. As 18 Sprints não entram no denominador de corridas principais.
- A indicação de chuva de um fim de semana ou de uma sessão inteira não demonstra chuva durante a prova. A chuva anterior à largada, posterior à bandeirada e durante suspensões fica fora deste recorte. O inventário inicial do brainstorm que mencionava 13 provas chuvosas está superado por esta auditoria.
- Spa/2025 exemplifica a diferença entre chuva caindo e pista molhada: o atraso da largada não pode entrar como tempo efetivamente disputado. “Sem chuva registrada” não significa “pista seca”.
- Hadjar/Austrália/2025 é DNS segundo o resultado nativo e a [Honda](https://global.honda/en/F1/race/2025/Australia/), apesar de constar como abandono na tabela canônica. A correção vale para o denominador complementar; o original foi preservado. Abandonos com zero voltas e desclassificados com voltas observadas continuam contando como largadas.
- Na Austrália/2026, 960 pares de piloto, horário UTC e duração têm números de volta diferentes em uma unidade. A sessão foi vinculada por correspondências únicas de horário/duração, com 95,7% de cobertura. A [camada complementar](../../frontend_assets/pilotos_condicoes.json) seleciona a numeração da fonte alternativa; não desloca arbitrariamente linhas nativas sem vínculo.
- Os limites reconstruídos descrevem stints da fonte alternativa; não provam a identidade de um mesmo jogo físico de pneus entre provedores. A divergência de composto de Lawson/Austrália/2025 permanece explícita e bloqueia preenchimentos misturando ordinais incompatíveis.
- São Paulo tem 15 curvas principais, não 16. Subdivisões como 1A ou 20A não são somadas à contagem de curvas principais. Comprimentos são específicos da edição: Spielberg/2024 tem 4,318 km, enquanto os mapas de 2025/2026 informam 4,326 km; Marina Bay passa de 4,940 km em 2024 para 4,927 km em 2025/2026.

## Regras de qualidade e limites

Para cada campo de sensor, pelo menos 95% dos intervalos de um minuto devem ter observação válida, sem lacuna superior a 180 segundos, incluindo as bordas. Essa é uma regra de qualidade, não um nível de certeza estatística. Zero observado é válido; vazio, fora de domínio e não observado são distintos. Direção do vento usa média circular.

Nuvens e código WMO vêm de modelo atmosférico em grade, com amostras horárias. Não substituem sensores de chuva, não recebem interpolação como se fossem medidos e não demonstram pista molhada. Acumulados de precipitação por hora não são rateados como medições de minutos de corrida. Altitude é aproximação DEM no ponto do calendário, não altitude média nem desnível do circuito.

TracingInsights e OpenF1 podem compartilhar a cronometragem F1 subjacente. A concordância verifica o vínculo dos dados; não é confirmação científica independente. Linhas `FastF1Generated` não fornecem voltas observadas. As tentativas de acesso público ao índice e a um arquivo específico da cronometragem F1 receberam HTTP 401, foram preservadas e não foram repetidas.

As 17 lacunas de compostos estão integralmente listadas em [pendencias.csv](consolidado_v1/pendencias.csv), com estado `lacuna_explicada_limite_fonte`. Nenhuma é de corrida principal. Não foram convertidas em pneus presumidos, zeros ou informação completa. Se uma análise futura depender desses compostos, seu controle de qualidade deverá bloqueá-la.

## Fontes e reprodução

- [OpenF1](https://openf1.org/docs/): controle de corrida e sensores.
- [Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api): contexto atmosférico reconstruído.
- [TracingInsights / tif1](https://github.com/TracingInsights/tif1/blob/main/DATA_REFERENCE.md): contrato dos dados de voltas; arquivos por temporada fixados por commit nos recibos.
- [TracingInsights / DDocs](https://github.com/TracingInsights/DDocs/tree/9f647f7c62a838405c85219e5eb2feb5c3575027): arquivo de documentos de autoria FIA/F1, com URL original, edição, hash e data de publicação. Os PDFs não são incluídos no pacote público do dashboard.
- [FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py): a telemetria usa o campo UTC; `LapStartDate` deriva desse relógio. Timestamps pandas serializados sem offset são interpretados conforme esse contrato, sem relaxar a exigência de timezone para outros provedores.

Coletores foram executados serialmente, com cache, recibos UTC/SHA-256 e intervalo mínimo de 3,1 segundos. As ferramentas locais reprodutíveis são `pitwall.data.race_weather`, `pitwall.data.tyre_reconciliation`, `pitwall.data.driver_source_audit`, `pitwall.data.circuit_conditions` e `pitwall.data.driver_quality_report`. Todas exigem novos destinos para preservar evidências anteriores.

O modelo preditivo v1, suas 15 entradas, emissões e probabilidades permanecem preservados. Estas fontes posteriores servem a análise descritiva e auditoria.

## Reprodução das projeções

```sh
python -m pitwall.data.driver_conditions --acquisition data/acervo_historico/pilotos-condicoes-20261029 --gate reports/pilotos_condicoes_20261029/consolidado_v1/gate_dados.json --output frontend_assets/pilotos_condicoes.json
python -m pitwall.data.driver_archive_projection --drivers frontend_assets/pilotos_condicoes.json --archive frontend_assets/acervo_dashboard.json --panels frontend_assets/paineis_editoriais.json --verified-on 2026-10-29
```

O primeiro comando exige os snapshots locais auditados, preservados fora do pacote público. O segundo é idempotente e aplica apenas projeções descritivas. O JSON portátil conserva os hashes das fontes e os suplementos observados; os PDFs originais não são redistribuídos.

[Revisão dos 66 mapas por edição, página e hash](circuitos_revisados.csv).
