"""Acervo descritivo 2024–2026, independente de modelos e emissões.

Reaproveita fontes locais, captura OpenF1 e Open-Meteo serialmente e preserva
respostas/UTCs/hashes. Não prepara entradas de modelo nem atualiza dashboard.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from pitwall.paths import PROJECT_ROOT
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from operacao2026.fontes import _lock

RAIZ = PROJECT_ROOT
ENDPOINTS = ("drivers", "session_result", "stints", "pit", "weather", "laps")
WEATHER_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("UTC da sessão ausente.")
    return result.astimezone(timezone.utc)


def save_checkpoint(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def event_key(event):
    return int(event["temporada"]), int(event["rodada"]), event["circuito_id"]


def map_sessions(events, catalogs, as_of):
    """Liga GP por data UTC exata de Race, nunca por nome aproximado/rodada."""
    mappings, failures = [], []
    for event in events:
        year, round_, circuit = event_key(event)
        sessions = catalogs.get(year, [])
        matches = [
            s
            for s in sessions
            if s.get("session_name") == "Race"
            and int(s.get("year", -1)) == year
            and instant(s["date_start"]).date().isoformat() == event["data_corrida"]
        ]
        method = "data_utc_exata"
        if not matches and event.get("localidade"):
            # Alguns calendários legados preservam a data local junto ao horário
            # UTC. Admitir esse vínculo exige localidade literal e offset da
            # própria fonte, sem corrigir a fotografia histórica.
            for session in sessions:
                if (
                    session.get("session_name") != "Race"
                    or int(session.get("year", -1)) != year
                    or session.get("location") != event["localidade"]
                ):
                    continue
                offset = session.get("gmt_offset", "")
                if len(offset) != 9 or offset[0] not in "+-":
                    continue
                hours, minutes, seconds = (int(x) for x in offset[1:].split(":"))
                shift = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                local = instant(session["date_start"]) + (
                    shift if offset[0] == "+" else -shift
                )
                if local.date().isoformat() == event["data_corrida"]:
                    matches.append(session)
            method = "data_local_e_localidade_literal"
        if len(matches) != 1:
            failures.append(
                dict(
                    temporada=year,
                    rodada=round_,
                    circuito_id=circuit,
                    estado="identidade_nao_resolvida",
                    races_correspondentes=len(matches),
                )
            )
            continue
        meeting = int(matches[0]["meeting_key"])
        for session in sessions:
            if int(session["meeting_key"]) != meeting:
                continue
            if instant(session["date_end"]) + timedelta(minutes=30) > as_of:
                continue
            mappings.append(
                dict(
                    temporada=year,
                    rodada=round_,
                    circuito_id=circuit,
                    session_key=int(session["session_key"]),
                    meeting_key=meeting,
                    criterio_identidade=method,
                    data_calendario=event["data_corrida"],
                    data_race_utc=instant(matches[0]["date_start"]).date().isoformat(),
                )
            )
    ids = [m["session_key"] for m in mappings]
    if len(ids) != len(set(ids)):
        raise ValueError("Uma sessão foi associada a mais de um GP.")
    return mappings, failures


def weather_window(event):
    dates = [event["data_corrida"]]
    for value in event.get("sessoes_calendario", {}).values():
        if isinstance(value, dict) and value.get("date"):
            dates.append(value["date"])
    if len(dates) == 1:
        dates.append(
            (datetime.fromisoformat(dates[0]) - timedelta(days=2)).date().isoformat()
        )
    dates.extend(event.get("datas_sessoes_observadas_utc", []))
    return min(dates), max(dates)


def weather_coverage(data, start, end):
    if not isinstance(data, dict) or data.get("utc_offset_seconds") != 0:
        return False
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    expected = 24 * (
        (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days + 1
    )
    indices = [i for i, hour in enumerate(times) if start <= hour[:10] <= end]
    if len(indices) != expected or len(set(times)) != len(times):
        return False
    return all(
        isinstance(hourly.get(field), list)
        and len(hourly[field]) == len(times)
        and all(hourly[field][i] is not None for i in indices)
        for field in WEATHER_FIELDS
    )


class CaptureClient:
    def __init__(
        self,
        destination,
        interval=3.1,
        opener=urlopen,
        sleeper=time.sleep,
        clock=time.monotonic,
        retry_errors=False,
    ):
        self.destination = Path(destination)
        self.path = self.destination / "coleta_online.json"
        self.interval, self.opener, self.sleeper, self.clock = (
            interval,
            opener,
            sleeper,
            clock,
        )
        if interval < 3:
            raise ValueError("Intervalo mínimo deste acervo: 3 segundos, serial.")
        self.last = None
        self.retry_errors = retry_errors
        self.requested_paths = set()
        if self.path.exists():
            self.manifest = json.loads(self.path.read_text())
            if self.manifest.get("schema") != "pitwall-acervo-online-v1":
                raise ValueError("Manifesto desconhecido; não sobrescrever.")
        else:
            self.manifest = dict(
                schema="pitwall-acervo-online-v1",
                criado_em_utc=utc_now(),
                estado="em_coleta",
                fontes=[],
                falhas=[],
                limites=dict(
                    intervalo_minimo_s=interval, max_bytes=1024**3, max_requisicoes=1200
                ),
                uso="Acervo retrospectivo descritivo; proibido alterar entradas v1 ou emissões.",
            )
            save_checkpoint(self.path, self.manifest)

    def source_usage(self, relative_path, active, reason=None):
        sources = [
            x
            for x in self.manifest["fontes"]
            if x.get("arquivo_requisicao", x["arquivo"]) == relative_path
        ]
        if not sources:
            return
        source = sources[-1]
        source["normalizar"] = active
        if reason:
            source["motivo_exclusao"] = reason
        elif active:
            source.pop("motivo_exclusao", None)
        save_checkpoint(self.path, self.manifest)

    def _check_retry_after(self, item):
        value = item.get("retry_after")
        if value is None and item["status"] == 429:
            # Compatibilidade com recibos antigos que guardavam o cabeçalho
            # apenas no manifesto da coleta interrompida.
            value = self.manifest.get("retry_after")
        if value in (None, ""):
            return
        try:
            seconds = float(value)
        except (ValueError, TypeError):
            try:
                deadline = parsedate_to_datetime(value)
                if deadline.tzinfo is None:
                    raise ValueError("Retry-After sem fuso.")
                deadline = deadline.astimezone(timezone.utc)
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError(
                    "Retry-After inválido; preservar resposta e conferir o provedor."
                ) from error
        else:
            if not math.isfinite(seconds) or seconds < 0:
                raise ValueError(
                    "Retry-After inválido; preservar resposta e conferir o provedor."
                )
            deadline = instant(item["obtido_em_utc"]) + timedelta(seconds=seconds)
        if datetime.now(timezone.utc) < deadline:
            raise RuntimeError(
                "Retry-After ainda não expirou; retome após {}.".format(
                    deadline.isoformat().replace("+00:00", "Z")
                )
            )

    def capture(self, provider, endpoint, relative_path, url, **metadata):
        response_format = metadata.get("response_format", "json")
        if response_format not in ("json", "bytes"):
            raise ValueError("Formato de resposta não suportado")
        existing = [
            x
            for x in self.manifest["fontes"]
            if x.get("arquivo_requisicao", x["arquivo"]) == relative_path
        ]
        path = self.destination / relative_path
        previous = None
        if existing:
            item = existing[-1]
            saved_path = self.destination / item["arquivo"]
            if (
                item["url"] != url
                or item.get("response_format", "json") != response_format
                or not saved_path.is_file()
                or sha256(saved_path.read_bytes()).hexdigest() != item["sha256"]
            ):
                raise ValueError("Cache divergente: " + relative_path)
            if item["status"] == 200:
                saved = saved_path.read_bytes()
                return saved if response_format == "bytes" else json.loads(saved)
            transient = item["status"] in (408, 425, 429, 500, 502, 503, 504)
            if (
                not self.retry_errors
                or not transient
                or relative_path in self.requested_paths
            ):
                return None
            self._check_retry_after(item)
            previous = item
            attempt = len(existing) + 1
            path = path.with_name(
                "{}.tentativa_{:04d}{}".format(path.stem, attempt, path.suffix)
            )
        if path.exists():
            raise FileExistsError("Arquivo sem recibo preservado: " + str(path))
        if len(self.manifest["fontes"]) >= 1200:
            raise RuntimeError("Teto de requisições alcançado.")
        if self.last is not None:
            self.sleeper(max(0, self.interval - (self.clock() - self.last)))
        self.last = self.clock()
        self.requested_paths.add(relative_path)
        status, error, final_url, retry_after = None, None, url, None
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "PitwallLab/acervo-historico (educational; serial; cached)",
                    "Accept": "application/json",
                },
            )
            with self.opener(request, timeout=60) as response:
                raw, status = response.read(256 * 1024**2 + 1), response.status
                final_url = response.geturl()
        except HTTPError as ex:
            raw, status, error = ex.read(), ex.code, str(ex)
            retry_after = ex.headers.get("Retry-After")
            if status == 429:
                self.manifest["estado"] = "limite_do_provedor"
                self.manifest["retry_after"] = retry_after
        except (URLError, TimeoutError, OSError) as ex:
            self.manifest["falhas"].append(
                dict(
                    provider=provider,
                    endpoint=endpoint,
                    url=url,
                    obtido_em_utc=utc_now(),
                    erro=str(ex),
                    **metadata,
                )
            )
            save_checkpoint(self.path, self.manifest)
            print(
                json.dumps(
                    dict(provider=provider, endpoint=endpoint, erro=str(ex)),
                    ensure_ascii=False,
                ),
                flush=True,
            )
            return None
        if len(raw) > 256 * 1024**2:
            raise ValueError(
                "Resposta excedeu 256 MiB; conservar manifesto e refinar consulta."
            )
        size = sum(x.get("bytes", 0) for x in self.manifest["fontes"]) + len(raw)
        if size > 1024**3:
            raise ValueError("Teto de 1 GiB de respostas excedido.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
        item = dict(
            provider=provider,
            endpoint=endpoint,
            arquivo=str(path.relative_to(self.destination)),
            arquivo_requisicao=relative_path,
            url=url,
            url_real=final_url,
            status=status,
            obtido_em_utc=utc_now(),
            sha256=sha256(raw).hexdigest(),
            bytes=len(raw),
            **metadata,
        )
        if error:
            item["erro"] = error
        if retry_after is not None:
            item["retry_after"] = retry_after
        try:
            payload = raw if response_format == "bytes" else json.loads(raw)
            if isinstance(payload, list):
                item["registros"] = len(payload)
        except (ValueError, UnicodeDecodeError):
            payload = None
            item["erro_formato"] = "Resposta não é JSON válido."
        if previous is not None:
            previous["normalizar"] = False
            previous["motivo_exclusao"] = (
                "Resposta transitória preservada; nova tentativa explícita na retomada."
            )
            previous["substituido_por"] = item["arquivo"]
        self.manifest["fontes"].append(item)
        save_checkpoint(self.path, self.manifest)
        print(
            json.dumps(
                {k: item[k] for k in ("provider", "endpoint", "status", "bytes")}
                | {
                    k: item[k]
                    for k in ("temporada", "rodada", "registros")
                    if k in item
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if status == 429:
            raise RuntimeError(
                "HTTP 429: coleta interrompida, respeitar Retry-After antes de retomada manual."
            )
        return payload if status == 200 else None


def collect_online(destination, events, as_of, interval=3.1, retry_errors=False):
    client, catalogs = (
        CaptureClient(destination, interval, retry_errors=retry_errors),
        {},
    )
    client.manifest["estado"] = "em_coleta"
    client.manifest["cobertura_meteo"] = []
    save_checkpoint(client.path, client.manifest)
    for year in sorted({e["temporada"] for e in events}):
        rows = client.capture(
            "openf1",
            "sessions",
            f"openf1/{year}/sessions.json",
            f"https://api.openf1.org/v1/sessions?year={year}",
            temporada=year,
        )
        if not isinstance(rows, list):
            catalogs[year] = []
            continue
        if any(int(s.get("year", -1)) != year for s in rows):
            raise ValueError("Catálogo mistura anos.")
        catalogs[year] = rows
    mappings, failures = map_sessions(events, catalogs, as_of)
    save_checkpoint(Path(destination) / "mapeamento_sessoes.json", mappings)
    client.manifest["eventos_sem_mapeamento_openf1"] = failures
    save_checkpoint(client.path, client.manifest)
    for year in sorted(catalogs):
        selected = [m for m in mappings if m["temporada"] == year]
        if not selected:
            continue
        # Operadores permanecem na sintaxe documentada: key>=valor, sem um '=' adicional.
        low, high = min(m["session_key"] for m in selected), max(
            m["session_key"] for m in selected
        )
        for endpoint in ENDPOINTS:
            url = f"https://api.openf1.org/v1/{endpoint}?session_key>={low}&session_key<={high}"
            rows = client.capture(
                "openf1",
                endpoint,
                f"openf1/{year}/{endpoint}.json",
                url,
                temporada=year,
            )
            if rows is not None and not isinstance(rows, list):
                raise ValueError("Dataset OpenF1 não é array: " + endpoint)
            if rows is not None and any(
                not low <= int(x.get("session_key", -1)) <= high for x in rows
            ):
                raise ValueError("Dataset OpenF1 contém session_key fora do filtro.")
    for event in events:
        year, round_, circuit = event_key(event)
        observed_keys = {
            m["session_key"]
            for m in mappings
            if (m["temporada"], m["rodada"], m["circuito_id"])
            == (year, round_, circuit)
        }
        event = dict(
            event,
            datas_sessoes_observadas_utc=[
                instant(s["date_start"]).date().isoformat()
                for s in catalogs.get(year, [])
                if s["session_key"] in observed_keys
            ],
        )
        start, end = weather_window(event)
        common = dict(
            latitude=event["latitude"],
            longitude=event["longitude"],
            hourly=",".join(WEATHER_FIELDS),
            timezone="GMT",
            wind_speed_unit="ms",
        )
        params = dict(common, start_date=start, end_date=end, models="ecmwf_ifs")
        url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
        metadata = dict(
            temporada=year,
            rodada=round_,
            circuito_id=circuit,
            start_date=start,
            end_date=end,
            model="ecmwf_ifs",
            origin="historical_atmospheric_model",
        )
        archive_path = f"open_meteo/{year}/{round_:02d}_archive.json"
        data = client.capture("open-meteo", "archive", archive_path, url, **metadata)
        complete = weather_coverage(data, start, end)
        client.source_usage(archive_path, True)
        if (
            not complete
            and (as_of.date() - datetime.fromisoformat(start).date()).days <= 92
        ):
            # Datas explícitas evitam incluir horas futuras no conjunto solicitado.
            fallback = dict(common, start_date=start, end_date=end)
            fallback_meta = dict(
                metadata, model="best_match", origin="archived_forecast"
            )
            forecast_path = f"open_meteo/{year}/{round_:02d}_forecast.json"
            data = client.capture(
                "open-meteo",
                "forecast",
                forecast_path,
                "https://api.open-meteo.com/v1/forecast?" + urlencode(fallback),
                **fallback_meta,
            )
            complete = weather_coverage(data, start, end)
            client.source_usage(
                forecast_path,
                complete,
                (
                    None
                    if complete
                    else "Fallback incompleto; conservar modelo histórico como série parcial."
                ),
            )
            if complete:
                client.source_usage(
                    archive_path,
                    False,
                    "Modelo histórico incompleto; janela integral disponível em previsão arquivada identificada.",
                )
        client.manifest.setdefault("cobertura_meteo", []).append(
            dict(
                temporada=year,
                rodada=round_,
                estado="completo" if complete else "parcial_ou_indisponivel",
            )
        )
        save_checkpoint(client.path, client.manifest)
    partial = (
        failures
        or client.manifest["falhas"]
        or any(
            x.get("status") != 200 or x.get("erro_formato")
            for x in client.manifest["fontes"]
            if x.get("normalizar") is not False
        )
        or any(
            x["estado"] != "completo"
            for x in client.manifest.get("cobertura_meteo", [])
        )
    )
    client.manifest["estado"] = (
        "captura_finalizada_com_lacunas" if partial else "captura_finalizada"
    )
    client.manifest["finalizado_em_utc"] = utc_now()
    save_checkpoint(client.path, client.manifest)
    return client.manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, required=True)
    parser.add_argument(
        "--archive", type=Path, default=(Path.home() / "Downloads" / "archive")
    )
    parser.add_argument("--intervalo", type=float, default=3.1)
    parser.add_argument("--retomar", action="store_true")
    parser.add_argument("--somente-local", action="store_true")
    args = parser.parse_args()
    from pitwall.data.archive_local import preparar_local

    if args.retomar:
        if not (args.destino / "coleta_online.json").is_file():
            raise ValueError("Retomada requer manifesto deste coletor.")
        events_path = args.destino / "eventos.json"
        if not events_path.exists():
            events_path = args.destino / "local/eventos.json"
        events = json.loads(events_path.read_text())
    else:
        args.destino.mkdir(parents=True, exist_ok=False)
        result = preparar_local(
            RAIZ, args.archive, args.destino, datetime.now(timezone.utc)
        )
        events = result["eventos"]
    print(
        json.dumps(
            dict(etapa="local", gps=len(events), destino=str(args.destino)),
            ensure_ascii=False,
        ),
        flush=True,
    )
    if args.somente_local:
        return
    with _lock(RAIZ / "data/operacao_2026/snapshots"):
        collect_online(
            args.destino,
            events,
            datetime.now(timezone.utc),
            args.intervalo,
            retry_errors=args.retomar,
        )
    from pitwall.data.archive_normalization import gerar_derivados

    result = gerar_derivados(args.destino)
    print(
        json.dumps(dict(etapa="derivados", resultado=result), ensure_ascii=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
