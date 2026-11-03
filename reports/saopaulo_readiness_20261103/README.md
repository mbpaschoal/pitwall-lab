# São Paulo: operação e versões / São Paulo operations and releases

Created by: MBPaschoal
Status: implemented; publication verification pending
Type: operational delivery report

## Português

A entrega 0.8.21 corrige a inversão de destaque entre releases e prepara a operação de São Paulo sem antecipar uma previsão. A criação das releases deixa de disputar o destaque antes do ZIP terminar; um workflow serial de manutenção escolhe a maior versão estável com asset carregado e SHA-256, limitada à VERSION de main. O término tardio de uma versão antiga não define a precedência. Recebimento e destaque são conferidos separadamente.

O monitor consulta a última coleta concluída em main. Falha ou seis horas sem conclusão abre uma única ocorrência PT/EN atribuída ao proprietário; repetição não gera mensagens. Recuperação recente comenta e encerra a ocorrência do bot, sem tocar ocorrências manuais. As notificações dependem das preferências da conta GitHub. Espera por sessão futura, janela gratuita, cooldown e ausência de mudança permanecem normais; restrição de acesso HTTP real fora da espera falha no workflow, preservando originais e dados publicados.

[Quatro aquisições seriais](acquisition.json), [fontes JSON preservadas](admitted-sources/) e [conferência](source-review.json): OpenF1 e Jolpica concordam com o cadastro 2026/20/interlagos, meeting 1299, e com a programação oficial F1. O GP Tempo identifica o evento como 21; país, localidade, data e nomes de sessão conferem. Nenhuma das cinco sessões alternativas tem resultados disponíveis; não foram consultados resultados futuros nem admitidos inputs preditivos por essa fonte. O HTML e recibos brutos ficam no acervo local, com hashes no relatório.

[Conferência offline](preflight.json): 25 pares piloto/equipe do catálogo de artes 2026, 75 arquivos com hash e três variantes distintas por par. Isso não é o elenco do GP: a população e equipes reais de Q precisam de nova conferência. O estado permanece aguardando_classificacao; nenhuma tentativa de emissão, favorito ou probabilidade foi criada. O [guia PT/EN](../../docs/PREPARACAO_SAO_PAULO.md) documenta a coleta pós-Q, identidade explícita e os bloqueios temporais. A fonte alternativa descritiva não substitui a admissão de snapshots pelo produtor v1.

A [rechecagem canônica do México](history-review.json), com [captura própria](history-acquisition.json), já coincide com as 17 posições classificadas e com pontos/voltas dos 22 pilotos da revisão final FIA. Os cinco abandonos mantêm a diferença entre ordem numérica nativa e posição oficial ausente. Não houve promoção dessa captura a snapshot preditivo; o snapshot efetivo será conferido após Q.

Validação e recibos públicos serão acrescentados somente após execução. Os modelos, previsões registradas e capturas preexistentes permanecem preservados. Implementação em cópia isolada, sem incorporar os rascunhos de UI e pesquisa existentes na raiz.

## English

Version 0.8.21 repairs out-of-order release highlights and prepares São Paulo without an early forecast. New releases no longer claim Latest before ZIP upload; serial maintenance selects the highest stable published version with an uploaded hash-bearing package, capped at main's VERSION, then verifies the highlight.

Collection monitoring opens one bilingual, owner-assigned GitHub incident on failure or six hours without a completed run. Repeated failures stay quiet; recent recovery comments and closes only the bot-owned incident. GitHub account settings control notifications. Expected future-session/free-window/cooldown/no-change deferrals remain normal, while actual HTTP provider restrictions fail the workflow with originals and previous public data preserved.

Four sequential public acquisitions revalidate canonical identity 2026/20/interlagos, OpenF1 meeting 1299 and the official F1 schedule. GP Tempo uses event 21, mapped through exact country/location/date/session, not numeric round equality. All five alternative sessions currently lack results; no future results or predictive inputs were admitted. Original receipts and JSON sources are linked above; HTML remains in the local archive with its hash.

Offline checks verify 75 artworks across 25 catalogue driver/team pairs, with three distinct variants per pair. This is not a certified race entry list: actual Q participants and teams must be rechecked. State remains awaiting qualifying, with no emission attempt, favourites or probabilities. The bilingual guide documents explicit event identity, post-Q snapshot validation and temporal gates. Descriptive alternatives do not bypass v1 admission. Validation/public receipts are added only after real execution. Existing frozen artefacts and unrelated local drafts remain preserved.

The separate [Mexico history review](history-review.json) now matches all 17 classified positions and points/laps for all 22 drivers in the final FIA review. Five retirements retain the distinction between native numeric ordering and missing official finish position. This review capture was not promoted to predictive input; the actual post-Q snapshot must be checked.

## Fontes / Sources

- [F1, programação de São Paulo](https://www.formula1.com/en/racing/2026/brazil).
- [OpenF1, catálogo do Brasil](https://api.openf1.org/v1/sessions?year=2026&country_name=Brazil).
- [Jolpica, rodada 20](https://api.jolpi.ca/ergast/f1/2026/20/?limit=100&offset=0).
- [GP Tempo, catálogo 2026](https://www.gp-tempo.com/api/events?year=2026&pastOnly=false).
- [GitHub, make_latest](https://docs.github.com/en/rest/releases/releases#update-a-release).
- [GitHub, workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run).
