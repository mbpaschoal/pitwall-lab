# Protocolo operacional 2026 v1 — fixado antes da coleta

Created by: MBPaschoal
Status: protocolo operacional; publicação não autorizada
Type: protocol

## Escopo e congelamento

Documento fixado em 19/10/2026, antes de consultar resultados de 2026 nesta etapa. Base do código anterior: `b067ad55dd97d964b132129838773cf6108773e3`. Mantêm-se os scripts e artefatos das etapas 1–7, a distribuição preparada, o ambiente Python 3.9.6 e o modelo v1. Novos componentes operacionais não alteram os antigos. Não há treinamento, recalibração, ajuste por 2026, licença nova, deploy ou mudança de visibilidade.

A fotografia inicial abrange os 288 arquivos rastreados e registra a modificação preexistente de `projects/Pitwall Lab.md`, que será preservada. Arquivos de auditoria desta etapa identificarão hashes antes/depois; somente README/contextos autorizados podem receber texto novo. A emissão usa apenas o joblib local confiável de SHA-256 `16718ea5c4a7f662e72f09d38b073e545df1bba5c64c87b2cc1a0973ad9116e3` e metadados de SHA-256 `77d24dc765d773e49b717b79844dd4678a91087dbbc091e3e9cb184215ea9cc6`.

## Seleção prévia do ensaio, sem olhar o resultado

O GP escolhido é **Singapura 2026**, por ser o último GP anterior a Austin no calendário oficial consultado, não pela qualidade de qualquer resultado ou previsão. Seu identificador e rodada serão encontrados pelo calendário e pelo circuito, sem número de rodada fixado no código. Se sua classificação não estiver disponível, registrar a impossibilidade do ensaio real; não escolher outro GP pela qualidade dos resultados nem apresentar fixture como real. Fixtures de testes serão explicitamente sintéticas e separadas.

A previsão de Singapura será sempre **ENSAIO RETROSPECTIVO**, emitido agora com fontes obtidas agora. Não comprova a versão histórica dos dados nem previsão anteriormente registrada. Não calcular desempenho do ensaio para escolher modelo ou alterar decisões.

## Fontes e programação oficial

Consultadas em 19/10/2026 antes da coleta: página oficial F1 de Austin, calendário F1, programação do COTA e contrato Jolpica. Respostas oficiais foram obtidas com UTC e hashes no ambiente de auditoria. URLs ao final; conferir novamente as sessões antes da futura emissão, pois podem mudar.

| Sessão Austin | America/Chicago | UTC | America/Sao_Paulo |
|---|---|---|---|
| Classificação — início previsto | 24/10/2026 16:00 -05:00 | 24/10/2026 21:00Z | 24/10/2026 18:00 -03:00 |
| Classificação — fim **programado**, não observado | 24/10/2026 17:00 -05:00 | 24/10/2026 22:00Z | 24/10/2026 19:00 -03:00 |
| Corrida — largada prevista | 25/10/2026 15:00 -05:00 | 25/10/2026 20:00Z | 25/10/2026 17:00 -03:00 |

Conversão efetuada por `zoneinfo`, não por fuso constante aplicado a todo o calendário. Os números acima são conferência humana, **não** um número de rodada no programa. Austin é identificado por `season=2026` e `Circuit.circuitId=americas`; a rodada vem do calendário validado. Não usar classificação de outro evento nem `SprintQualifying`/`SprintShootout` como substituto de `Qualifying` principal.

## Coleta separada e fotografia disponível

Área nova `data/operacao_2026/`, com pasta nova por snapshot. Prioridade para `https://api.jolpi.ca/ergast/f1/2026/`, resultados por rodada `.../2026/<rodada>/results/` e classificação principal `.../2026/<rodada>/qualifying/`. Calendário e resultados antigos ficam intactos. Resultados de Sprint não são consultados ou somados.

- Um único coletor sequencial. User-Agent identificável, requisições espaçadas em pelo menos oito segundos, limite por página 100 e paginação por registros, sem presumir 20 ou 22 pilotos.
- As regras oficiais consultadas indicam 4 requisições/s e 500/h, sujeitas a mudança; o espaçamento escolhido é conservador. Respeitar `Retry-After` numérico ou HTTP-date, nunca tentar antes do prazo; tentativas limitadas e prazo excessivo encerra com mensagem clara, sem loop infinito.
- Guardar bytes JSON originais e metadados: URL solicitada/real, parâmetros, status, obtenção UTC, SHA-256 e origem cache/rede. Resposta inválida pode ser preservada como diagnóstico, mas nunca se torna cache válido. Resposta vazia de classificação futura é estado de indisponibilidade, não um pelotão vazio previsto.
- Cache só pode reutilizar resposta validada com data de obtenção original; não fingir recaptura. Nova atualização gera snapshot novo e nunca sobrescreve silenciosamente o anterior. Deve existir opção explícita de atualização, especialmente para uma classificação anteriormente vazia.
- Selecionar resultados principais de eventos cuja liberação administrativa (00:00 UTC do dia seguinte à corrida) não exceda o corte da coleta. O endpoint ainda precisa realmente ter dados. Reportar eventos concluídos disponíveis, ausentes e futuros separadamente; não exigir futuros para declarar o histórico **disponível** completo, nem omitir lacunas passadas.
- Cada GP de 2026 tem fonte separada: isso permite ao gerador não abrir o resultado do alvo ou de eventos posteriores. Ler o calendário e os nomes/hashes do manifesto não autoriza abrir todos os arquivos de resultados.
- Conferir ano/rodada/circuito/data, total/offset/limit, IDs e unicidade de registros, posições e pontos válidos. Registrar IDs novos/desaparecidos em relação a 2021–2025; nunca unir por nome nem inventar equivalências de equipes.

## Corte, participantes e elegibilidade sem resultado futuro

A população de emissão vem **somente da classificação principal admitida no corte**. Não fazer união com os resultados do alvo, não consultar sua lista de participantes posterior e não usar `Results.grid`. A cobertura declarada é sobre registros publicados pela fonte; sem lista independente de inscritos não se pode prometer o pelotão integral.

Ausência completa da classificação: **aguardando classificação**, nenhuma probabilidade ou favorito. Paginação incompleta, identidade divergente, piloto duplicado, tipo inválido ou dado temporal incoerente: bloquear com motivo, sem fabricar resposta. Posição ausente preserva o indicador e a imputação já aprendida, conforme elegibilidade v1; posição repetida preserva o valor e acende o indicador, sem inventar ordem de classificação. A referência de ranking trata ausências/desempates explicitamente.

Elegibilidade permanece a do v1: registro de classificação presente e referência temporal conhecida. Ausência de posição ou histórico insuficiente não é novo motivo de exclusão: é representada pelas mesmas entradas e pelo imputador congelado. IDs/equipe vazios ou envelopes incoerentes são erros de validade da fonte, não oportunidade para derivar a equipe do resultado atual.

Para o histórico, manter o limite conservador do v1: início da classificação no calendário é limite inferior do seu encerramento, **não** horário de emissão. Usar apenas eventos anteriores, excluindo explicitamente alvo e posteriores, liberados até esse limite. Conservar ordenação por data/hora, temporada e rodada. Histórico antigo 2021–2025 é lido das páginas `raw/` de resultados/calendário já preservadas e conferido pelos manifestos; não consultar treinamento/validação como substituto de resultados brutos, nem reexecutar o preparador antigo.

Na emissão prospectiva, distinguir: início da sessão, fim observado/confirmado pelo operador com fonte, corte de admissão, obtenção das fontes e emissão efetiva. Não inventar duração nem tratar o fim programado como fim observado. O comando futuro deve exigir confirmação da sessão encerrada e fonte; documentos/revisões ainda provisórios devem ser identificados. Classificação precisa ter sido obtida até o corte e não antes do início da sessão. A emissão e o corte têm de ocorrer antes da largada conhecida; relógio atual é consultado pelo programa, sem opção CLI para retrodatá-lo.

## As mesmas 15 entradas, fórmulas e ordem

A ordem é a de `models/modelo_v1/metadados.json` e `data/preparado/colunas.json`:

1. `posicao_classificacao`: posição em QualifyingResults, nunca grid retrospectivo.
2. `posicao_classificacao_repetida`: 1 para posição positiva repetida na sessão.
3. `classificacao_ausente`: ausência do registro de classificação.
4. `posicao_classificacao_ausente`: posição não informada.
5. `media_posicao_final_5`: soma das posições numéricas das até cinco últimas participações anteriores do driverId / número dessas participações; nulo se zero.
6. `taxa_podios_5`: número de posições de pódio nessas participações / mesmo denominador; nulo se zero.
7. `n_posicoes_5`: número de participações, de zero a cinco.
8. `n_podios_5`: mesmo denominador, não número de acertos/pódios.
9. `media_pontos_equipe_5`: soma Decimal dos pontos dos registros da equipe nos até cinco últimos GPs anteriores em que seu constructorId aparece / número real desses registros; nulo se zero.
10. `n_corridas_equipe_5`: número de GPs na janela da equipe, zero a cinco.
11. `n_participacoes_equipe_5`: registros da equipe nessas corridas, sem presumir dois por GP.
12. `historico_piloto_insuficiente`: 1 se menos de cinco participações.
13. `historico_equipe_insuficiente`: 1 se menos de cinco eventos.
14. `equipe_pre_corrida_ausente`: equipe não disponível na classificação; média nula e contadores zero, sem substituição pelo resultado atual.
15. `referencia_temporal_ausente`: referência de calendário não conhecida; bloqueia elegibilidade.

DNS/abandonos/desclassificações com registro continuam conforme posição numérica da fonte, sem exclusão seletiva. Janelas atravessam anos; equipe segue constructorId literal e piloto driverId literal. ID novo começa sem histórico inventado. Não acrescentar treinos, clima, nome de equipe, alvo ou resultado atual à matriz. Não criar `podio=0` para alvo não ocorrido: emissões não contêm seus desfechos.

## Inferência estritamente congelada

Antes de carregar joblib, validar modelo, metadados e esquema contra hashes congelados. Carregar exclusivamente artefato local confiável. Bloquear `fit`, `fit_transform`, `partial_fit` nos estágios e pipeline durante a inferência. Conferir medianas, médias/escalas, coeficientes, intercepto e hiperparâmetros com os metadados antes/depois, e bytes do modelo ao final. Não recalibrar ou atualizar nada.

Constante de treino preservada: `0.15011372251705837`, lida/conferida no metadado. Probabilidades individuais para elegíveis, top 3 por probabilidade e referência de ranking da classificação usam regras de desempate v1 (ID literal). Não estimar ordem P1/P2/P3, não forçar soma das probabilidades a três. Registrar empates, particularmente na fronteira do top 3. Não calcular métricas de 2026 para ajustar decisões.

## Emissões imutáveis e comprovação limitada

Pasta nova por emissão em `reports/operacao_2026/emissoes/`, criada sem sobrescrita. Conteúdo: evento/modo/corte/obtenção/emissão UTC, fontes e snapshots admitidos com hashes, matriz exata de entradas, históricos realmente usados, probabilidades/favoritos sem alvos atuais, cobertura/limites, hashes do modelo/metadados/esquema e código. Registrar Git commit e situação dos componentes: se ainda não estiverem no commit, declarar base + hashes/dirty explicitamente, nunca atribuir código novo a commit velho. Prospectivo exige componentes de código commitados e intactos. Ensaio de desenvolvimento pode ter dirty explícito; entrega final deve incluir ensaio com commit real dos componentes.

Correção/retomada exige pasta nova relacionada à anterior e motivo, sem substituir a original. Avaliação posterior é outro fluxo/pasta e não modifica a previsão. Arquivos locais, timestamps e commits não são prova externa imutável de emissão anterior ao evento. Não há automação, agendamento ou espera até sábado.

## Alternativa gratuita e indisponibilidade

Se a Jolpica atrasar, manter o estado de espera; não consultar infinitamente nem reutilizar outro GP. Alternativa: classificação oficial no site F1 do evento ou documento de classificação da FIA disponibilizado para esse GP. Antes de admitir importação manual, guardar cópia original com URL, obtenção UTC/hash, evento/ano/circuito, mapeamento explícito verificado para driverId/constructorId literais, posições e responsável pela transcrição. Validar com a mesma regra, marcar `origem=manual` em toda a emissão e não alegar consulta via API. Sem evidência e IDs coerentes, não emitir. A existência de uma página oficial hoje não garante publicação imediata dos resultados futuros de Austin.

## Contexto opcional FastF1, separado da emissão

FastF1 é um enriquecimento gratuito, manual e pós-sessão para registrar FP1, FP2, FP3 ou Q já públicos. Não há polling, credencial, dado pago, consulta automática nem dependência do dashboard durante uma emissão. O cache explícito fica em `data/operacao_2026/fastf1/cache/`; cada fotografia fica em `data/operacao_2026/fastf1/<id>/` com `sessao.json` e `indice.json`, UTC, fonte, `session_key`, GP/cidade/país/data e SHA-256.

A sessão é resolvida pela rodada e circuito já presentes no snapshot Jolpica informado ao comando; o operador não fornece uma rodada solta. Se FastF1 ainda não publicar a sessão, o comando devolve `aguardando_dados` e encerra sem falha. FP1/FP2/FP3 e Q são snapshots distintos. Para emissão prospectiva, Jolpica continua sendo a única fonte canônica da classificação: um snapshot FastF1 opcional só pode ser `Q`, precisa ter temporada/rodada/circuito iguais ao evento Jolpica e é validado como contexto. Seus dados nunca entram nas 15 variáveis, não alteram a matriz, probabilidades ou favoritos e não permitem emitir sem `QualifyingResults` Jolpica válido.

## Verificações obrigatórias e entrega

Testes sintéticos identificados: alvo/futuro ausentes ou alterados não afetam matriz/probabilidades/favoritos; auditoria de arquivos impede abrir resultado-alvo; fórmulas/janelas comparadas ao v1; novos IDs e janelas vazias; classificação ausente/incompleta/incoerente; fit bloqueado e parâmetros iguais; exclusividade de emissão e correções; prospectivo recusado após largada ou com dados obtidos após corte. Regredir escopo relevante sem executar treino ou coletores antigos reais. Confirmar hashes de etapas1–7/distribuição antes/depois.

Entregar comandos A (coleta/atualização), B (ensaio) e C (coleta/validação/emissão futura após classificação) e limitações realmente verificadas. Austin fica aguardando classificação se ela ainda não existir. Não integrar novas telas ao dashboard/distribuição.

## Fontes primárias consultadas

- F1, evento Austin: https://www.formula1.com/en/racing/2026/united-states
- F1, calendário: https://www.formula1.com/en/racing/2026
- COTA, programação sujeita a alteração: https://circuitoftheamericas.com/event/f1/schedule/
- Jolpica, limites/cache: https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md
- Jolpica, calendário/sessões: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md
- Jolpica, classificação: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/qualifying.md
- Protocolos congelados: [temporal](protocolo_temporal.md), [variáveis](dicionario_variaveis.md) e [modelo](experimento_modelo_v1.md).
