# Mexico race weekend · 2026

[Português](../OPERACAO_FIM_SEMANA.md)

Track what each source has actually published. Identity: **2026 / 19 / rodriguez**, OpenF1 meeting **1298**. The explicit configuration is [`mexico2026.json`](https://github.com/mbpaschoal/pitwall-lab/blob/main/operacao2026/eventos/mexico2026.json).

| Session | São Paulo time | Session key |
|---|---|---|
| FP1 | Oct 30, 15:30 | 11397 |
| FP2 | Oct 30, 19:00 | 11398 |
| FP3 | Oct 31, 14:30 | 11399 |
| Qualifying | Oct 31, 18:00 | 11400 |
| Race | Nov 1, 17:00 | 11404 |

Sources: [F1 calendar](https://www.formula1.com/en/racing/2026/mexico), [event organizer](https://www.mexicogp.mx/mediacenter/la-guia-mas-completa-para-vivir-el-mexico-gp-2026/) and the public OpenF1 catalog. A scheduled end is not evidence of an actual finish.

## Collection and publication

Use the existing analysis environment and run **one collector at a time**:

```sh
.venv/bin/python -B -m operacao2026.weekend --evento operacao2026/eventos/mexico2026.json --publicar-status --preparar-qualificacao
```

The producer waits until the scheduled end plus ten minutes, then requires `SESSION FINISHED`; qualifying also requires Q3. It preserves raw JSON, URL, HTTP status, UTC and SHA-256. It collects drivers, session results, laps, tyres, pits, sensors and race control. It never queries future telemetry. Incomplete sessions remain partial. HTTP 429 persists a cooldown of at least one hour or the longer `Retry-After`. Completed sessions use a hash-verified cache; `--rever-concluidas` creates a new capture to check revisions.

Originals live in Git-ignored `data/operacao_2026/fins_de_semana/`. `frontend_assets/operacao_fim_semana.json` is the public projection. The app reads it offline; running the collector **does not** deploy Streamlit. Meaningful changes require a version, PT/EN notes, export, tests, commit/push and deployment verification. Query timestamp changes alone do not warrant a release.

Forecasts come from [Open-Meteo](https://open-meteo.com/en/docs/), with their retrieval time. Observations come from OpenF1 sensors within actual race intervals, excluding interruptions; insufficient coverage stays explicit. Air temperature is distinct from track temperature. No paid service was enabled. Free historical access does not guarantee immediate publication after a session.

After the race, official championships use Jolpica endpoints for **round 19**, with complete pagination. Another round is rejected. New observations enter Drivers rankings only after weather, tyre, identity and circuit checks; acquiring files does not approve their interpretation.

## Prediction and evaluation

After Q3, create a new snapshot with `operar_2026.py coletar --id NEW_ID --classificacao-circuito rodriguez`, then check `estado --snapshot NEW_ID --temporada 2026 --rodada 19 --circuito rodriguez`. Prefer canonical qualifying. If unavailable, the preserved OpenF1 bundle requires explicit `--openf1-evento operacao2026/eventos/mexico2026.json` and `--openf1-diretorio BUNDLE`, validated identity and UTCs. See `operar_2026.py emitir --help` for all arguments.

Emission requires committed operational code, the frozen model, complete admitted history and a cutoff after all sources but before lights out. **Without proven emission and publication before Nov 1 at 20:00 UTC, Mexico has no prospective forecast.** Never backdate or reuse Austin. Add the real emission to `operacao2026/eventos/emissoes_registradas.json`, preserving previous declarations. `preparar_dashboard_race_weekend.py --snapshot NEW_ID` selects the new snapshot without changing Austin's historical default.

The 2026 Lab score includes only registered predictions with validated later outcomes. Retrospective trials are excluded; small samples do not establish superiority. Frozen v1, its 15 inputs and existing probabilities remain unchanged.

## Hosted automation

The [collection workflow](https://github.com/mbpaschoal/pitwall-lab/actions/workflows/coletar-dados.yml) replaces local follow-up: it runs on GitHub servers every half-hour, at minutes 7 and 37. It requires neither the personal computer nor chat reminders. Scheduler delays are possible; this is not a real-time guarantee.

`operacao2026/cloud.py` uses the explicit Mexico configuration and discovers subsequent 2026 events using the canonical calendar, exact dates and OpenF1 meetings. Sprint sessions are preserved. Collection runs from the day before first practice through 48 hours after the race; no telemetry is acquired outside that window. Revisions are checked after 16 hours past the scheduled race end. Ambiguous identity stops collection.

Runs are serialized, preserve cache and cooldowns, and retry delayed sources. GitHub may evict execution caches; a replacement capture receives its own UTC. Original captures also accompany automatic releases as `capturas-originais.tar.gz`, independently of the cache. Persisted state is capped at 128 MiB and compressed captures at 32 MiB. No credentials are stored in captures.

Only substantive changes create a version, PT/EN notes, export, tests, navigation checks, commit/tag and release. Query timestamps and forecast-only changes do not create releases; hourly forecasts refresh alongside new session data. The app shows the last published verification and links to the workflow. Previous weekends remain in a public archive without borrowing the next GP's data. The same workflow validates delivery because `GITHUB_TOKEN` pushes do not trigger further push workflows. Failures remain visible in Actions; displayed timestamps are never artificially advanced.

This uses standard Linux runners for a public repository, without enabling paid services or increasing storage limits. Cache and logs have their own limits. Product browser evidence is retained for three days. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

The automation collects and publishes descriptive context. It neither trains models nor emits probabilities: prospective emission rules above remain mandatory.
