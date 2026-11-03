# São Paulo: preparation, alerts and forecast

[Português](../PREPARACAO_SAO_PAULO.md) · English

## Prepared operation

São Paulo is configured as **2026/20/interlagos**, OpenF1 meeting **1299**, with five conventional sessions. Jolpica calendar, OpenF1 catalogue and [F1's official programme](https://www.formula1.com/en/racing/2026/brazil) were rechecked on 3 November 2026. Race start is 8 November, 14:00 local / 17:00 UTC. FP1 is Friday 12:30; FP2 16:00; FP3 Saturday 11:30; qualifying 15:00 (UTC−3).

The existing collector's active window begins on 5 November at 12:30 local, 24 hours before FP1. GitHub scheduling is best effort, not an exact execution-time guarantee. Free-access deferral and observed session completion remain required; Mexico stays in the event archive. Scheduled duration does not establish an observed finish.

GP Tempo was verified as an alternative: **source event 21**, compared with canonical round 20. Matching requires exact country, location, event date and session. All five sessions had unavailable results in the 3 November capture; this is neither a forecast input nor a guarantee of future data availability. [Sources, hashes and review](https://github.com/mbpaschoal/pitwall-lab/tree/main/reports/saopaulo_readiness_20261103).

## Quiet incident alerts

`maintenance.yml` monitors collection after completed workflows and hourly. A failed latest completed run or more than six hours without a completed run opens one bilingual GitHub incident assigned to the owner. Repeated conditions do not add comments or issues. A recent healthy execution comments on recovery and closes the incident. Manually created issues are untouched.

Provider HTTP access restrictions outside normal deferral now explicitly fail the workflow while retaining captures and previous public data. Waiting for future sessions, free-tier windows, cooldown and unchanged data remain normal states. GitHub account preferences control issue notifications; code sends no email or messages through another service.

## Offline preparation check

```sh
python -B -m operacao2026.readiness \
  --evento operacao2026/eventos/saopaulo2026.json \
  --report /private/tmp/saopaulo-preparation-NEW-ID.json
```

Use a new destination. This command performs no HTTP, acquisition, training or prediction. It checks calendar identity, windows, available observed timing and SHA-256 of three distinct team-coloured artworks for each 2026 driver/team pair in the catalogue. This is an artwork inventory, not the GP entry list or favourite selection. Actual entrants and their teams must be checked again after Q. Cards stay optional, with different poses and no percentages on the artwork.

`aguardando_classificacao` is expected before Q. Received descriptive qualifying data only leads to `classificacao_recebida_snapshot_preditivo_pendente`, never predictive readiness. Mexico or another session cannot unlock São Paulo; future/inconsistent finish receipts fail. The prospective window closes at race start.

## After main qualifying

Free access is scheduled after 7 November, 16:30 local / 19:30 UTC, subject to actual session or provider delays. Do not collect predictive inputs before observed session completion. Create a new snapshot, then ask the existing producer to determine readiness:

```sh
SNAPSHOT="saopaulo-pos-q-$(date -u +%Y%m%dT%H%M%SZ)"
python -B operar_2026.py coletar --id "$SNAPSHOT" --atualizar --classificacao-circuito interlagos
python -B operar_2026.py estado --snapshot "$SNAPSHOT" --temporada 2026 --rodada 20 --circuito interlagos
```

Stop unless status is `pronto`. Check final canonical Mexico history, v1 historical-window receipts/UTCs and the actual qualifying population. Descriptive supplements do not automatically repair model inputs. The OpenF1 route requires São Paulo's explicit configuration (`--openf1-evento operacao2026/eventos/saopaulo2026.json`), preserved inventory and adapter admission; do not reuse the adapter's Austin default. GP Tempo is not an admitted predictive substitute.

Only with real data and readiness, provide `--temporada 2026 --rodada 20 --circuito interlagos` to `emitir`, with a new ID, observed finish, evidence URL and current UTC cutoff. Follow the [operational chain](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/comandos_operacao_2026.md): validate, register, generate the asset, verify actual favourites' team artwork, increment version, export, publish and verify the live revision **before race start**. Missing dependencies or a closed window remain explicit. Neither this document nor the preparation checker schedules or automatically emits a forecast.

## Latest release

New releases do not immediately replace `Latest`. Once assets finish uploading, maintenance selects the highest published stable version with a complete, hash-bearing ZIP, capped at `main`'s `VERSION`. Workflow completion order does not decide version precedence. A slower old release cannot demote a newer one, nor can an assetless release be promoted. Job receipts record the selection and confirmation after a change.
