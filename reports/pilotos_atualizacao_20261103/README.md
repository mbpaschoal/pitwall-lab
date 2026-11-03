# Pilotos: México, atualização automática e aceite

Created by: MBPaschoal
Status: released and public build verified; mobile export limits documented
Type: delivery report

Português · [English](README.en.md)

O México 2026 entra nas análises de Pilotos: **67 GPs, 1.376 resultados e 1.362 largadas**. Perfis, filtros, duelos, busca e cartões usam o complemento validado, preservando a base de 66 GPs até Austin. As cinco posições NC do México continuam ausentes; largadas entram no denominador, mas posições desconhecidas não entram no placar do duelo.

A versão pública confirmada é **0.8.25**, build `5e6f3c3be744311d0ecda31df1dcf640923e0f4351ed9b33221147b7c67ed7e7`. [Build servido](public-build-025/public-build.json) · [Pacote e comparação](package.json). O código e os dados de runtime são idênticos aos da 0.8.24; a 0.8.25 corrige o aceite e sua organização no CI. Modelo v1, probabilidades registradas e entradas preditivas permanecem preservados.

## O que atualiza sozinho

A coleta serial do GitHub Actions acrescenta GPs encerrados após conferir identidade, população, largadas, resultados, clima efetivo e referência do circuito da edição. Isso funciona mesmo quando só Pilotos muda. Repetições idênticas não geram novas versões. Divergências mantêm a última contribuição válida, mostram pendência e acionam o monitor após seis horas. Retry-After persiste entre execuções.

A recuperação real foi comprovada na execução [41705250105](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41705250105): Jolpica HTTP 200, 67 GPs, nenhuma pendência ou alteração substantiva. A execução [41706516200](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41706516200) reconfirmou esse estado. O monitor fechou sozinho a [ocorrência 1](https://github.com/mbpaschoal/pitwall-lab/issues/1). [Recibo](collector-recovery.json) · [Contrato PT/EN](../../docs/PILOTOS_ATUALIZACAO.md).

## Fontes e preservação

- Resultado canônico [Jolpica já capturado](../saopaulo_readiness_20261103/admitted-sources/mexico-results.json) e capturas nativas da 0.8.20 foram reutilizados, sem reescrever os originais. [Reuso e hash](captures-acquisition.json).
- Mapa FIA 2026, Doc. 7, página 2: 17 curvas, sentido horário, 4,304 km. [URL, UTC e SHA da captura](acquisition.json). A altitude de 2.234 m é aproximação pontual Open-Meteo, não a amplitude de elevações do traçado.
- Clima usa intervalos efetivamente disputados, sem pausas de bandeira vermelha e sem a leitura anômala já adjudicada. O complemento não inventa nuvens ou código WMO para o México.
- A base permanece com SHA `dfc760dfb9a78e2cf087c89b7175ab671070bc2b6eed3dab70297a2df7ae2535`. Foram conferidos 231 arquivos protegidos sem alteração. [Integridade](protected-integrity-final.json). Rascunhos da raiz original não foram incorporados; trabalho em checkout isolado.

## Verificação e aprendizados

352 testes de código e 144 do pacote passaram localmente. As 11 suítes Chromium/WebKit foram mantidas e divididas em dois grupos; ambos são exigidos pela release. [Matriz](browser-matrix.json) · [Testes](source-tests.json) · [Pacote](package-tests.json).

| Problema encontrado | Correção verificável |
|---|---|
| Consulta sem cache falhou antes de gravar o manifesto | A 0.8.23 cria a pasta e testa o construtor real, respostas HTTP e 429. Coleta hospedada recuperada. |
| Perfis perderam retratos antigos sem `driver_id` explícito | A 0.8.24 preserva a identidade literal dos arquivos e verifica os 29 retratos; Hirakawa usa o JPEG original e seu crédito correto. |
| Um teste exigia Audi na rodada 18 após o México | A 0.8.25 exige a última corrida validada da equipe. [Falha reproduzida](search-context-stale-reproduction/interactions.json) e [quatro casos corrigidos](search-context-corrected/interactions.json), sem retirar verificações. |

Tags, erros anteriores e recibos foram preservados. A lição é verificar consumidores e estados reais, testar o cliente sem cache e evitar expectativas de UI presas a uma rodada histórica.

## Prova pública e limites

[Conferência pública](public-acceptance.json): dados, retratos reais e duelos verificados em PT/EN, desktop e largura de celular. CSV/SVG nativos foram salvos nos dois idiomas no desktop e em português no Pixel 7 emulado. O inglês em 390 px usou inicialização desktop e verificações de leitura; o salvamento nativo do SVG em inglês móvel não foi certificado. Houve sessões de carregamento intermitente e eventos de download cancelados; as tentativas anteriores estão preservadas no cofre local, com amostras publicadas de [bootstrap interrompido](browser-public-025-mobile-en-r3/mobile-en-failure.json) e [download cancelado](browser-public-025-responsive-en/mobile-en-failure.json). Não foi testado aparelho físico. O recibo distingue esses casos e as versões 0.8.24/0.8.25, cujo runtime é idêntico.

O registro atual admite o mapa do México 2026. **Mapas de próximas edições ainda exigem conferência**; sem ela, o GP fica pendente e o monitor avisa. As 17 lacunas de compostos na auditoria da base permanecem declaradas e não entram nos rankings. A previsão de São Paulo continua aguardando Q e snapshot preditivo validado; não houve nova emissão ou treino.

## Publicação final

[Release 0.8.25](https://github.com/mbpaschoal/pitwall-lab/releases/tag/v0.8.25) publicada e destacada como Latest. As etapas da [CI da tag](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41710817366) terminaram com sucesso: 352 testes de fonte, 144 do pacote e 11 suítes de navegador. ZIP de 665.854.558 bytes, SHA-256 `d927d471984e0c42d1306f7282c646ce14465f8546904ea9134f33cc5eaf11cd`, igual ao pacote local. [Recibo final](delivery-final.json). A [CI separada da main](https://github.com/mbpaschoal/pitwall-lab/actions/runs/41710817082) também passou nas verificações; a publicação nela é ignorada por ser exclusiva da tag.
