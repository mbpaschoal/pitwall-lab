# Mexico race weekend · 2026

[São Paulo, alerts and release ordering](SAO_PAULO_PREPARATION.md) · 0.8.21

## Publication and concurrency

Publication checks remote main before commit/tag creation and after an atomic push rejection. A proven branch advance dispatches a fresh run on main, reusing preserved captures and repeating all validation with current code and version. Generated packages are never rebased or force-pushed. A lineage permits at most two recoveries; authentication failures and limits remain explicit. [PT/EN runbook](https://github.com/mbpaschoal/pitwall-lab/blob/main/docs/runbooks/automatic-publication.md).

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

Runs are serialized, preserve cache and cooldowns, and retry delayed sources. During late review, a completed session or standings table already checked after the 16-hour cutoff is reused while outstanding checks are retried. GitHub may evict execution caches. A replacement capture receives its own UTC. Original captures also accompany automatic releases as `capturas-originais.tar.gz`. Persisted state is capped at 256 MiB and compressed captures at 32 MiB. No credentials are stored in captures.

Only substantive changes create a version, PT/EN notes, export, tests, navigation checks, commit/tag and release. Query timestamps and forecast-only changes do not create releases; hourly forecasts refresh alongside new session data. The app shows the last published verification and links to the workflow. Previous weekends remain in a public archive without borrowing the next GP's data. The same workflow validates delivery because `GITHUB_TOKEN` pushes do not trigger further push workflows. Failures remain visible in Actions; displayed timestamps are never artificially advanced.

This uses standard Linux runners for a public repository, without enabling paid services or increasing storage limits. Cache and logs have their own limits. Product browser evidence is retained for three days. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

The automation collects and publishes descriptive context. It neither trains models nor emits probabilities: prospective emission rules above remain mandatory.

## Missing session driver profile

If a number appears in results, laps, tyres or stops but has no driver profile, the session stays partial and only the tables/projections depending on that profile are withheld. Original captures, receipts and the unresolved number are preserved. Other sessions continue without borrowing names from another session or GP. Partial sessions are retried on later runs. Duplicates, conflicting laps and foreign sessions still stop collection; the exception is limited to a missing driver profile.

### Incident verified on Nov 1, 2026

FP3 (`11399`) returned 22 results but 21 driver profiles: number 30 appears in results/laps/tyres but is absent from `drivers`; its specific query returned 404. FP3 and qualifying (`11400`) pit records also contain number 236 without a profile. Qualifying retains its 22 valid results, laps and tyres; only its pit projection is withheld. Affected FP3 groups stay withheld, with numbers and groups recorded in `qualidade_identidade`. No name was inferred or borrowed from another session. Published coverage distinguishes partial sessions from the upcoming race.

Regression checks cover missing profiles, continuation to qualifying, preservation of valid results, duplicates and conflicting laps. Mexico forecast evaluation awaits a validated later race result; this recovery never reissues probabilities.

Sources: [FP3 profiles](https://api.openf1.org/v1/drivers?session_key=11399), [FP3 results](https://api.openf1.org/v1/session_result?session_key=11399), [qualifying pit records](https://api.openf1.org/v1/pit?session_key=11400). Availability may change after the recorded captures.

## Post-race review — 0.8.1

[OpenF1's access policy](https://openf1.org/#faq) treats the 30 minutes before and after each session as live. Free collection now waits through that window without paid authentication. This explains the scheduled runs' observed 401 responses, rather than establishing missing historical data. Identity and catalogue failures outside the window still stop collection.

If the catalogue still returns 401/403, the run reports `provider_access_restricted`, preserves the raw response and retains the previous public data. The next scheduled run retries; there is no immediate retry loop or automatic subscription. Restricted access is not treated as successful collection or evidence of missing results.

Mexico's catalogue extended Race's scheduled end from 22:00 to 23:00 UTC; the configuration records the reviewed change and source SHA. This changes collection timing only. The actual observed finish was 22:23:54 UTC, not the scheduled end.

The race returned 205 weather observations and 1360 lap records. The feed also contained 12 messages predating the declared session start with the race's IDs. The weather window records their indices and excludes them through temporal context, without deleting raw data or substituting the schedule for actual lights out. Actual starts and restarts remain required; repeated starts within the session without a suspension remain invalid. The 21:06–21:45 UTC suspension is excluded. Mean active-race air temperature is 24.2 °C. The raw track mean (40.3 °C) is withheld pending review because it includes an isolated 0 °C reading between 37.4 and 37.5 °C.

Three of five sessions are complete. FP3 remains partial because profile 30 and pit identity 236 are missing; qualifying retains results/laps/tyres while withholding affected pit data. Observed OpenF1 results and round-19 standings are posterior context. Mexico's recorded prediction and probabilities remain unchanged; admission to model evaluation is a separate step.

Calendar review also checked Formula 1's [official Bahrain-in-Malaysia announcement for Sepang](https://www.formula1.com/en/latest/article/formula-1-and-fia-confirm-that-malaysia-will-join-the-2026-calendar-as-host-venue-for-the-bahrain-grand-prix.6lL7vjFEM2VVynRHvg1TCf). Event name, host country and circuit are distinct fields; presentation does not change canonical identity.

## Alternative sources — release 0.8.3

Documentary review recovers all 22 FP3 times and identifies Lawson by number, name and team in this event's official entry list. Temporal scope excludes one pre-FP3 pit record and 84 pre-qualifying records; originals remain preserved. The final classification and stewards' decision establish Lawson as DSQ, without a numeric position or valid times.

The track mean now uses 100 valid readings: 40.7 °C, 98.0% coverage, without interpolation. The FIA report also records the anomalous zero; it does not reveal that minute's real temperature. Lawson's initial FP3 compound (laps 1–8) remains unavailable and is not inferred from later stints. Reviews reach both cache and automatic collection. [Sources, decisions and remaining gaps](https://github.com/mbpaschoal/pitwall-lab/blob/main/reports/mexico_fontes_alternativas_20261101/README.md).


Completed GPs enter Drivers analysis through the [automatic review workflow](DRIVER_UPDATES.md). An edition-specific circuit reference is required; missing prerequisites retain the last valid state and trigger the monitor after six hours.

## Resuming after failure — 0.12.4

Each attempt's `estado.json` retains partial diagnostics with its raw captures and receipts. The GP directory's `estado.json` is the resume checkpoint: it receives a new state only after normal completion, including weather-series validation. A late failure retains the previous state; without one, it does not create a usable resume checkpoint.

HTTP 429 follows the same rule and adds `retry_after_utc` to the previous state, or records only that deadline when there is no previous state. The restriction survives restarts without promoting an incomplete attempt. An unavailable calendar or catalogue raises an explicit source error; the original failure remains in the manifest. There is no data filling, immediate retry or change to forecasts.
