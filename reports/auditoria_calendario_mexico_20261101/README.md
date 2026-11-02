# Auditoria do México e do calendário / Mexico and calendar audit

Created by: MBPaschoal
Status: implemented; publication verification recorded separately
Type: delivery evidence

## Português

A entrega 0.8.1 reúne a coleta observada do México, a correção de identidade visual do calendário e os refinamentos de acessibilidade. A fonte retornou 22 resultados, 1360 registros de voltas, 80 stints, 67 paradas e 205 medições meteorológicas. O campeonato corresponde à rodada 19: 24 pilotos e 11 equipes. Os números descrevem a fonte coletada, sujeitos a revisões oficiais; não alteram as probabilidades emitidas.

O clima usa 101 medições nos intervalos efetivos, exclui a suspensão e audita 12 mensagens anteriores ao início declarado. O ar tem média de 24,2 °C. A leitura do asfalto de 0 °C em 22:01:42 UTC fica entre 37,4 e 37,5 °C; a média bruta é preservada apenas para diagnóstico e retida na interface. A revisão operacional identifica um zero isolado entre vizinhos de pelo menos 20 °C, separados por até 180 segundos e dentro do mesmo intervalo ativo. Não interpola nem substitui valores; a política histórica padrão permanece preservada.

Pendências da fonte: TL3 não tem o perfil 30 e contém paradas sem identidade 30/236; a classificação tem paradas sem identidade 236. Os grupos afetados ficam retidos e os grupos independentes válidos permanecem disponíveis. A avaliação do modelo para o México aguarda admissão própria do resultado; observar o pódio não cria uma nota científica automaticamente.

A automação aguarda a janela gratuita da OpenF1. Restrições 401/403 preservam a captura e o último conteúdo público; o próximo agendamento tenta novamente. Divergências de identidade e catálogo continuam bloqueando a coleta. A extensão do fim programado para 23:00 UTC foi revisada e registrada apenas na configuração de coleta.

A [Fórmula 1 confirma Bahrain in Malaysia em Sepang](https://www.formula1.com/en/racing/2026/bahrain). A interface usa Malásia/Sepang e a bandeira anfitriã, mantendo o nome original no dado. O diagnóstico anterior de anomalia era incorreto. A capa original de Austin permanece em alta resolução; candidatos visualmente inadequados não foram publicados. Não se declara equivalência pixel a pixel com a prancha conceitual.

## English

Release 0.8.1 combines observed Mexico data, host-aware calendar labels and accessibility refinements. Source counts are 22 results, 1360 lap records, 80 stints, 67 pit records and 205 weather samples; round-19 standings have 24 drivers and 11 teams. Recorded probabilities remain unchanged.

Weather uses 101 active-race observations, excludes the suspension and audits 12 pre-session messages. Mean air temperature is 24.2 °C. An isolated 0 °C track reading between 37.4 and 37.5 °C blocks publication of the track mean; the raw diagnostic remains preserved. The operational review flags a zero between neighbours of at least 20 °C, no more than 180 seconds away, within one active interval. It does not interpolate, replace values or change the default historical policy.

Unresolved source gaps: FP3 lacks profile 30 and contains pit identities 30/236; qualifying has unresolved pit identity 236. Only affected groups are withheld. Mexico model evaluation awaits separate result admission. Free-tier live restrictions defer collection; 401/403 responses retain raw evidence and previous public data until the next scheduled attempt. Identity/catalogue disagreements remain errors. The reviewed schedule change affects collection only.

Formula 1 confirms the Bahrain-in-Malaysia event at Sepang. Host-aware labels preserve canonical identity. The previous anomaly diagnosis was wrong. Austin keeps its original high-resolution image; rejected candidates are not published. Pixel-for-pixel identity with conceptual artwork is not claimed.

## Evidências / Evidence

- [Dados, fontes e hashes / Data, sources and hashes](data-audit.json)
- [Revisão do sensor / Sensor review](sensor-review.json)
- [614 artefatos preservados / 614 preserved artifacts](protected.json)
- [Operação PT](../../docs/OPERACAO_FIM_SEMANA.md) · [Operation EN](../../docs/en/WEEKEND_OPERATION.md)

Testes de origem, pacote portátil, navegador PT/EN, CI e versão servida possuem recibos próprios. Uma execução local não prova publicação; o recibo de entrega final distingue essas etapas.

Source tests, portable-package checks, PT/EN browser acceptance, CI and the served version have separate receipts. Local execution alone is not proof of deployment.

Aceite local / Local acceptance: **209** testes de origem / source tests; **133** testes portáteis / portable tests; **24** cenários visuais / visual cases; **4** cenários do México / Mexico cases; **14** cenários de acessibilidade / accessibility cases. [Recibo / Receipt](validation.json).
