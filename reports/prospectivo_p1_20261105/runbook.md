# P1 — roteiro do primeiro par prospectivo

Created by: MBPaschoal
Status: prepared; execution waits for real qualifying and publication evidence
Type: operational runbook
Date: 2026-11-05

[Protocolo](protocolo.md) · [English protocol](protocol.en.md)

## 1. Antes do corte

Conferir a versão pública fixada por hash do protocolo, da referênciaQ e dos dois comparadores. Usar a revisão registrada, não editar pesos/receita ao preparar o evento. Manter ambiente científico existente. A auditoria está em `native-audit.json`; readiness offline e testes não liberam previsão.

Confirmar calendário oficial novamente em caso de alteração: [São Paulo](https://www.formula1.com/en/racing/2026/brazil), identidade2026/20/interlagos. Na configuração auditada, Q começa07/11/2026 às18hUTC e corrida08/11 às17hUTC. A coleta tem janela a partir05/11 às15h30UTC; não iniciar coletor manual em paralelo ao workflow hospedado. O acesso gratuito pós-Q tem espera mínima até19h30UTC07/11, sujeita ao encerramento observado e à fonte.

O anúncio de Câmara não fornece autorização para inventar ID/número. Após Q, conferir o registro canônico real, equipe Haas e ausência do substituído, conforme política. Se a rota Jolpica estiver indisponível e OpenF1 continuar sem mapeamento literal revisado, registrar bloqueio. Não reaproveitar ID de Ocon/Hirakawa ou um número de outro GP.

## 2. Após Q observado

Deixar o fluxo nativo admitido coletar e preparar a emissão v1. Ele exige `SESSION FINISHED` de Q3 e fontes/UTC reais, com tentativas limitadas e cooldown. Conferir manifesto, snapshots, histórico final do México, dependências das janelas e registro. Se o estado não estiver pronto ou o registry não validar a emissão, parar e preservar a falha. Este roteiro não instrui emitir manualmente em paralelo, nem recriar um ID existente.

Registrar o ID real e usar um checkout íntegro atual com as fontes originais publicadas/preservadas. O registro deve conter `PROSPECTIVO` para o evento certo; não escolher uma emissão por semelhança de nome. A cópia de evidências local deve corresponder ao mesmo manifesto/hash.

## 3. Preparar o par, sem refazer v1

De dentro da pasta deste pacote, trocar os valores abaixo pelos caminhos/ID reais. `FONTE_P1` precisa ser um checkout íntegro, não uma pasta com placeholders. `DESTINO_P1` deve ser novo.

```sh
FONTE_P1=/caminho/checkout-integro-atual
EMISSAO_P1=ID_PROSPECTIVO_REAL
DESTINO_P1=/caminho/novo-par-p1
python -B pair_predictions.py --source-root "$FONTE_P1" \
  --emission-id "$EMISSAO_P1" --destination "$DESTINO_P1"
```

O comando valida registry/capturas/UTC pelo leitor nativo, hashes do v1 e arquivos, identidade, matriz, população e prazo. Prepara Q com parâmetros já congelados. Não treina, coleta, altera v1 ou publica. O resultado inicial é **`prepared_not_published`**.

## 4. Publicar e comprovar os bytes no prazo

Publicar o arquivo imutável `paired-probabilities.json` como asset de uma release pública do repositório. A publicação do par exige execução explícita, preservação do nome/ID anterior e observância da política de publicação; este pacote não faz upload automaticamente. Não editar o JSON para marcar publicação. Antes de **08/11 às16hUTC** na configuração atual (largada−60min, exclusivo), tanto as probabilidades v1 quantoQ precisam estar publicamente acessíveis, com digest/tamanho e horário do servidor verificáveis.

Com o ID numérico real do asset, criar recibo separado:

```sh
python -B verify_published_pair.py \
  --pair-file "$DESTINO_P1/paired-probabilities.json" \
  --asset-id ID_NUMERICO_REAL \
  --destination "$DESTINO_P1/public-receipt.json"
```

Esse verificador faz uma consulta pública, sem chave, à API de assets do repositório. Exige upload completo, SHA-256/tamanho iguais, criação/atualização no servidor anteriores ao prazo e coerência do par. Ele pode conferir a evidência depois da corrida, pois valida bytes publicados antes do limite; não cria uma previsão tardia. Hash ausente, reupload/atualização tardia ou bytes diferentes impedem o aceite.

Conferir separadamente o dashboard público: versão/build, evento, roster e probabilidades reais em PT/EN, computador/celular, antes da largada. A prova do asset não prova o host; a prova do host não substitui os raws/UTC do produtor. Preservar tentativas/falhas e não declarar entrega pública por CI verde.

## 5. Depois da corrida

Adicionar observados em diretório novo, sem editar os arquivos de previsão. Juntar por identidade exata; manter ausência desconhecida e DNF/DNS/DSQ conforme alvo v1. Pontuar apenas pares admissíveis e alvos conhecidos, conservar falhas de cobertura no ledger. Não recalcular o par que faltou antes do prazo. Registrar métricas descritivas a cada GP; checkpoints e decisão são os do protocolo20GPs, sem tuning com2026.

## Limites operacionais presentes

O workflow atual publica v1 e não chama `pair_predictions.py`. Assim, P1 requer execução/publicação manual do acompanhante ou uma futura integração revisada; não presumir comparação automática. Sem operador/recibo, contar o GP na cobertura como par ausente. O anúncio está revisado, mas o ID canônico real e o fallback de Câmara dependem das fontes/da revisão após Q. Nenhuma previsão de São Paulo ou par real foi criado nesta preparação.

## English

Freeze/publicly register protocol/code/model hashes before the first future cutoff. Use the existing scientific environment and a healthy source checkout. Wait for observed mainQ and validated nativev1 emission; never run parallel collectors or infer Camara's canonical ID/car mapping from announcements. CanonicalQ unavailable plus unresolved OpenF1 mapping means block.

Run the companion commands above with the actual registered prospective emissionID and a new destination. It checks original model/file hashes,registry,native UTCs/identity/coverage and the60minute publication margin, then prepares unchangedv1 plus frozenQ probabilities without fitting/collecting/publishing. The initial status is prepared_not_published.

Explicitly publish the immutable pair as a public GitHub release asset before race−60min (currently08Nov16UTC). Use the actual assetID with verify_published_pair.py to preserve a separate read-only server-digest/time receipt. Later auditing can validate earlier public bytes; it cannot turn a late calculation/upload into a prospective pair. Verify served dashboard forecast separately before race start across languages/viewports. CI/package proof alone is insufficient.

After the race, keep targets separate,match exact identities,retain unknowns/outcomes and record every missing/blocked GP. Never backfill a missing pair after the deadline. Follow the fixed20GP protocol/checkpoints. Existing hosted automation does not invoke this manualP1 companion; integration would be a separate reviewed product change. No real event forecast or upload occurred in this preparation.
