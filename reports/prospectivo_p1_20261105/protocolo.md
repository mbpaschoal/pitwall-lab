# P1 — avaliação prospectiva v1 × classificação probabilística

Created by: MBPaschoal
Status: fixed local protocol; no new event forecast; public registration pending
Type: prospective evaluation protocol
Date: 2026-11-05

[English](protocol.en.md). Preparação autorizada pelo proprietário após DL1/GB1/HR1, todos sem promoção. O timestamp local e hashes identificam esta fotografia; **não constituem registro público independente**. Publicar protocolo, código de comparação e hashes antes do primeiro corte admitido; sem isso, identificar a etapa como piloto/documentação e não alegar estudo publicamente pré-registrado.

## Pergunta e modelos congelados

Avaliar a qualidade de probabilidades individuais de pódio do v1 em eventos futuros, contra uma referência probabilística de qualifying. Não pretende demonstrar melhor modelo universal, ordem P1/P2/P3, lucro ou causalidade.

V1 original: treino2021–2023, 15 entradas e hashes exatos em `registration.json`, sem reestimar transformadores/coefs. Referência **Q-logistic-2021-2023**: três entradas (posição, indicador de posição ausente e repetida), mediana/StandardScaler/logística L2 C1 já ajustados em2021–2023,1.319 linhas. Reutilizar parâmetros do fold2024 de GB1, sem ajuste novo nem dados2026. Parâmetros, fonte e hash em `q-baseline-frozen.json`, pinados no comparador. Não converter ranking em probabilidade arbitrária.

Não usar DL1/GB1/HR1 como candidatas operacionais. Sem seleção de features, hiperparâmetros, limiares, ensemble ou recalibração durante P1. A soma das probabilidades individuais não é forçada a três. Atualizar apenas as janelas históricas permitidas do v1 com eventos anteriores e fontes admitidas antes do corte; isso não é reajuste de pesos. Resultados atuais, grid retrospectivo, estratégia/clima realizados e status da própria corrida não entram.

## Janela fixa e cobertura

P1 considera os **primeiros20 GPs principais realizados do calendário oficial após o registro deste protocolo**, começando pelo primeiro cuja referência temporal ainda seja futura. São Paulo2026 é o piloto operacional previsto. Cancelamento sem corrida é registrado e não conta como GP realizado. Suspensão, mudança de data e reinício exigem manter a identidade e a decisão oficial, sem mover o evento para fora por desempenho.

Registrar todos os20 GPs, inclusive evento não admitido, classificação ausente, fonte bloqueada, indisponibilidade, atraso e falha de publicação. Não substituir um GP perdido por outro posterior para obter um resultado favorável. A política automática atual admite somente2026/20/interlagos; este protocolo **não amplia automaticamente a admissão** a outros eventos/temporadas. Cada extensão exige calendário/roster/fontes e configuração revisados antes do corte.

As duas emissões prospectivas antigas e todos os ensaios retrospectivos permanecem fora da amostra P1; podem ser auditados como evidência anterior, sem renomear ou recalcular o passado como previsão nova.20GPs é horizonte de planejamento, não garantia de poder estatístico.

## Corte e emissão por GP

Depois do encerramento **observado** da classificação principal, executar a cadeia científica já existente. Horário programado não comprova encerramento. Exigir identidade exata de temporada/rodada/circuito/sessão, população completa, IDs de piloto/equipe, paginação, hashes, UTCs e histórico final admitido. As equipes vêm da classificação; não inferir IDs por nomes/número de outro evento.

Manter a cadeia `inícioQ <= fim observado <= captura de cada páginaQ <= corte <= emissão`, fontes históricas admitidas não posteriores ao corte, publicação com margem operacional. A regra de liberação administrativa dos GPs anteriores não comprova publicação histórica; na operação real, o produtor exige UTCs reais das dependências relevantes. Sem resultado atual no conjunto de entradas.

O v1 é produzido e validado pelo código operacional congelado, registrado com ID novo; o comparador P1 só prepara Q usando a mesma matriz elegível e as mesmas chaves. Ele recusa fonte retrospectiva, mudança de modelo/matriz, arquivos divergentes, alvos atuais e execução tardia. Não oferece opção CLI para retrodatação. A coluna de probabilidade v1 é copiada e conferida, nunca reescrita.

Exigir preparação e evidência pública dos **dois** arquivos antes de `largada oficial −60min`, limite exclusivo, conferido de novo após o cálculo. O horário de emissão local não prova publicação. Manter evidência externa de disponibilidade (URL, SHA-256, horário verificável de criação/observação no servidor); provar separadamente que o dashboard serviu a versão e as probabilidades corretas antes da largada. CI/build/ZIP isolados não comprovam o host. Se só v1 for publicado no prazo, é emissão operacional v1 válida sob suas regras, mas **não é par P1 admissível**.

O comparador retorna `prepared_not_published` e `publication_verified=false`; ele não publica, agenda ou altera o registry do v1. Um par preparado só entra na avaliação quando a evidência pública for validada. Arquivo criado depois do prazo não vira prospectivo por possuir entrada antiga. Se uma mudança de largada for anunciada, preservar prova oficial e aplicar a restrição mais conservadora até revisão explícita, sem ampliar a janela silenciosamente.

## População, alvos e avaliação

Mesma lista elegível no corte, IDs e equipes para ambos. Em2026, a operação exige22 participantes canônicos; números futuros dependem de política revisada, não de pressupor sempre22. DNF/DNS/DSQ com resultado conhecido permanecem segundo a regra de alvo do v1. Ausência de resultado continua alvo desconhecido, jamais zero. Pós-corrida não apagar participante, redefinir elegibilidade nem corrigir probabilidade. Correções usam versão nova e motivo; conservar primeira emissão e analisar sensibilidade em separado, sem selecionar a correção que melhora o score.

Guardar alvos e auditoria posteriores em diretório separado e juntar por `(temporada,rodada,piloto_id)`, verificando circuito/data/roster. Pontuar apenas casos com ambas as probabilidades admissíveis e alvo conhecido, conservando contagens de ausentes. Métricas principais: **Brier e log loss**, média das perdas por GP com peso igual entre GPs; médias por linha secundárias. Log loss usa clip fixo[1e-15,1−1e-15]. Calibração: dez bins fixos,ECE e inclinação/intercepto diagnósticos fora do ajuste, sem aplicar transformação. Ranking top3 secundário apenas com GP completo,elegível,todos os alvos conhecidos e três positivos; desempate lexical de ID. Reportar cobertura de GPs/participantes, alvos desconhecidos, falhas e condições de uso.

Após cada GP, registrar métricas descritivas e integridade, sem alterar receitas. Checkpoints operacionais após5/10/15GPs realizados; não selecionar modelo, parar por sucesso ou reajustar pelos scores. Checkpoint comparativo fixo após20GPs realizados. Diferenças v1−Q pareadas por GP, bootstrap em blocos móveis de quatro GPs dentro de temporada,10.000 repetições,seed20261105. Não tratar pilotos correlacionados como20corridas independentes. Se faltar par admissível em algum dos20, continuar reportando todas as contagens/métricas, mas a conclusão comparativa formal deste checkpoint será **inconclusiva por cobertura**. Não estender a amostra silenciosamente.

Com20GPs pareados, chamar evidência favorável ao v1 somente se os limites superiores dos IC95% de ΔBrier e Δlog loss forem negativos. Se ambos os limites inferiores forem positivos, registrar evidência favorável a Q e necessidade de revisar o v1 em estudo separado; nenhuma substituição automática. Demais resultados: inconclusivo. Qualquer violação temporal/integridade anula a admissibilidade do par, sem apagar o registro. Não extrapolar um sinal favorável a ótimo global ou garantia futura.

## São Paulo — pré-condições explícitas

Calendário oficial reconferido nesta auditoria: Q07/11 e corrida08/11, com configuração2026/20/interlagos/session11408/meeting1299. O encerramento e roster reais ainda são futuros. A revisão do anúncio de Rafael Câmara exige que a classificação canônica contenha seu ID real/equipe Haas e não contenha o substituído. A rota OpenF1 requer mapeamento literal revisado; hoje Câmara não consta do mapa. Se a fonte canônica falhar e o mapa não estiver revisto, **bloquear**, sem usar ID/número de outro piloto. Artes são opcionais e não alteram o alvo.

Antes da publicação: validar México/históricos relevantes, snapshots/UTC, população real de Q, emissão v1, parQ, registro público e confirmação do host. O êxito de testes com fixtures ou readiness offline não prova coleta real pós-Q ou previsão futura. Nenhuma previsão de São Paulo foi emitida nesta preparação.

## Entrega e limites desta etapa

Protocolo PT/EN, referênciaQ congelada, comparador manual, testes, auditoria nativa atual, workflows/logs e checklist. O workflow hospedado atual **não chama o comparador P1**. Usar o roteiro manual `runbook.md` após Q; ausência de operador/publicação do par fica registrada como perda de cobertura, não é preenchida depois da corrida. Integração automática futura é mudança de produto separada, com versão/CI/aceite próprios. Nenhum coletor, agendamento, emissão ou publicação foi executado pela preparação deste protocolo.
