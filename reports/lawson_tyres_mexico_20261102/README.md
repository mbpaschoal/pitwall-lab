# Pneus de Lawson no TL3 do México / Lawson Mexico FP3 tyres

Created by: MBPaschoal
Status: implemented; publication verification pending
Type: source adjudication and delivery report

## Português

O primeiro trecho de Lawson foi recuperado como **MEDIUM nas voltas 1–8**, por cruzamento documental. O GP Tempo registra MEDIUM diretamente nas voltas 2–8. A análise oficial da FIA confirma o primeiro trecho contínuo de oito voltas, entre 11:42:06 e 11:55:03 locais (17:42:06–17:55:03 UTC). A atribuição do composto à volta 1 é uma reconstrução por continuidade desse trecho sem passagem pelos boxes, identificada na interface. O tempo dessa volta e a idade inicial continuam ausentes.

Fontes admitidas:

- [Catálogo do GP Tempo](https://www.gp-tempo.com/api/events?year=2026&pastOnly=true): evento 20, México, 01/11/2026, FP3. Esse identificador pertence à fonte e corresponde à rodada 19 do Pitwall; não se faz junção pelo número de rodada isolado.
- [Classificação do GP Tempo](https://www.gp-tempo.com/api/results?year=2026&event=20&session=3): LAW, carro 30, P9, entre os 22 participantes.
- [Voltas de Lawson no GP Tempo](https://www.gp-tempo.com/api/laps?year=2026&event=20&session=3&driver=LAW): sete observações diretas de MEDIUM no stint 1. Todos os 25 tempos não ausentes coincidem com a OpenF1; a fonte alternativa omite as durações das voltas 12 e 20, que permanecem preservadas da fonte nativa.
- [FIA, análise em pista do TL3, página 2](https://www.fia.com/sites/default/files/2026_19_mex_f1_p3_timing_thirdpracticesessionontrackanalysis_v01.pdf): identidade, primeiro trecho, quantidade de voltas e limites dos boxes. O PDF não publica compostos; não é usado sozinho para atribuí-los.

[Conferência](evidence-check.json), [aquisição admitida](tempo-mexico-acquisition.json), [catálogo capturado](tempo-events-acquisition.json) e [reprojeção sem nova coleta](reprojection.json). A [adjudicação anterior](adjudication-before.json) permanece preservada. O novo tratamento é aplicado na projeção, nunca nos bytes capturados.

O produtor exige identidade, tempos verificados e horários dentro do trecho aprovado; rejeita stints nativos conflitantes ou sobrepostos. Um registro nativo compatível é preservado, inclusive idade zero; a recuperação documental não atribui idade zero. A primeira estratégia é ordenada por volta e mantém URLs, hashes e distinção entre observação direta e continuidade documental.

O seletor de pneus passa a expor as sessões já disponíveis, com Corrida como padrão. Treinos e classificação têm seus próprios stints e passagens pelos boxes. O TL3 chega a `dados_recebidos`: 77 stints na projeção validada, mantendo 76 no inventário original. As cinco sessões recebem dados, sem certificar que todos os campos das fontes são completos.

Outras verificações, sem dados admitidos: OpenF1 ainda omite o primeiro stint; o arquivo da F1 retorna 401; o espelho documentado pelo FastF1 retorna 404 para a sessão; DeltaTrace respondeu 429 e não foi novamente consultado; F1 Tempo antigo limita o ano a 2025. The Field usa OpenF1 e não forneceu comprovação adicional na página consultada. As respostas e os hashes das tentativas estão nos recibos desta pasta; uma falha de acesso não prova que o dado não existe.

Validação: [315 testes de fonte e 141 do pacote aprovados](validation.json), além dos 41 focais iniciais. O [aceite local em navegador](browser-local-r2/acceptance.json) passou em PT/EN, computador/celular, com oito CSVs realmente baixados. Testes novos conferem imutabilidade dos registros, conflito de composto, tempo/horário divergente, idempotência, idade nativa preservada e separação das sessões. Os recibos de CI e publicação são acrescentados após execução real. Modelo, probabilidades e resultados registrados não são recalculados.

## English

Lawson's opening run is recovered as **MEDIUM on laps 1–8 through documentary reconstruction**. GP Tempo directly identifies MEDIUM on laps 2–8; FIA's on-track analysis confirms an uninterrupted eight-lap first run between 17:42:06 and 17:55:03 UTC. Lap 1's compound follows the continuity of that run and is explicitly marked as reconstructed. Its missing lap time and initial tyre age remain unknown.

GP Tempo event 20 is mapped to Pitwall round 19 through country, circuit, event date and session, rather than by round number alone. Driver LAW/#30 and P9 match. All 25 non-null alternative lap times match the native source; its missing lap-12/lap-20 times do not replace existing native values. FIA establishes run boundaries, not compounds by itself. The linked receipts retain URLs, UTCs and hashes, and the previous adjudication is preserved.

The normalizer rejects conflicting compounds, unexpected lap evidence and overlaps. It leaves raw bytes unchanged and retains a compatible native age, including zero. Documentary recovery does not invent initial age. The tyre selector now exposes available practices/qualifying as well as Race, keeping Race as default and filtering pit-lane passages by session. FP3 has 77 reviewed stints versus 76 original records; received-data status for all five sessions does not certify complete fields in every source.

Other public probes were not admitted as evidence: unchanged OpenF1 gap, authenticated F1 archive, missing FastF1 mirror session, a DeltaTrace rate-limit response, and the old F1 Tempo API's 2025 year limit. Attempts are retained and bounded. Validation passed 315 source tests, 141 portable tests and four local PT/EN desktop/mobile browser cases, with eight actual CSV downloads. CI and fresh public acceptance receipts are recorded only after execution. Frozen scientific artifacts and registered probabilities remain unchanged.

## Catálogo da automação / Automation catalogue — 0.8.19

A revisão do recebimento público da 0.8.18 encontrou uma falha anterior a essa entrega: [execução 41550196046](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41550196046), ainda na 0.8.17, bloqueada por mudança no catálogo. A [conferência das diferenças](catalogue-diff.json) encontrou somente `Race.date_end`: de 23:00 para 22:00 UTC. A resposta original está [preservada](admitted-sources/catalogue-reviewed.json), com [recibo](catalogue-check-acquisition.json), e a [configuração anterior](event-before-catalogue-review.json) foi mantida.

A 0.8.19 atualiza esse término **programado** mediante conferência explícita, sem relaxar a validação do catálogo. A espera conservadora anterior até 23:30 UTC permanece em `consulta_publica_apos_utc`; testes garantem que esse campo não pode encurtar os 30 minutos de proteção do acesso gratuito. [Regra de acesso OpenF1](https://openf1.org/#faq). Largada, identidade e encerramento observado continuam preservados. A reprojeção de todas as sessões também restaura as chaves opcionais de piloto dos caches legados de TL1/TL2; os nomes, números, tempos, voltas e o clima observado permanecem iguais. A recuperação documental de Lawson permanece a mesma. O fim programado não substitui os sinais observados de encerramento nem limita artificialmente a janela meteorológica da corrida.

English: a pre-existing 0.8.17 collection failure was caused solely by a catalogue change to the scheduled race end, from 23:00 to 22:00 UTC. Version 0.8.19 explicitly reviews and updates that configuration, retaining strict catalogue checks. Start time, identity, observed finish and observed weather remain unchanged. Reprojection also restores optional driver-ID keys from legacy FP1/FP2 caches while preserving names, numbers, lap times and laps. The 0.8.18 Lawson documentary recovery is retained. Original responses, hashes, UTCs and the previous configuration are linked above; scheduled end does not substitute for observed race-control events.

The previous conservative 23:30 UTC free-access deferral is retained in a separate field. Tests forbid shortening the default live-access buffer. Catalogue timing, observed finish and API-access deferral have distinct roles.
