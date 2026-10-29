"""Observed weather in verified main-race intervals; never prediction inputs.

Race is selected by session name: OpenF1 also uses session_type=Race for Sprint.
Coverage is measured in 60-second bins anchored to each active interval. A
recorded observation covers its bin, not an interpolated gap or a red-flag pause.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics


class RaceWeatherError(ValueError):
    """An identity, timing or integrity assumption was not verified."""


FIELDS = {
    "rainfall": (0, 1),
    "air_temperature": (-80, 80),
    "track_temperature": (-80, 120),
    "humidity": (0, 100),
    "pressure": (300, 1200),
    "wind_speed": (0, 150),
    "wind_direction": (0, 360),
}


def instant(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise RaceWeatherError("Invalid timestamp") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise RaceWeatherError("Timestamp must have an explicit timezone")
    return result.astimezone(timezone.utc)


def main_race_session(sessions):
    races = []
    for session in sessions:
        names = [session[k] for k in ("nome", "session_name") if session.get(k)]
        if len(set(names)) > 1:
            raise RaceWeatherError("Conflicting session names")
        if names and names[0] == "Race":
            races.append(session)
    if len(races) != 1:
        raise RaceWeatherError("Expected exactly one main Race session")
    return races[0]


def race_windows(messages, session_key):
    """Use actual status transitions, not scheduled start or planned restarts."""
    ordered = []
    for index, message in enumerate(messages):
        if int(message.get("session_key", -1)) != int(session_key):
            raise RaceWeatherError("Race-control session identity mismatch")
        ordered.append((instant(message["date"]), index, message))
    ordered.sort(key=lambda x: (x[0], x[1]))
    active, finish = None, None
    intervals, evidence, seen = [], [], set()
    for stamp, index, message in ordered:
        if message.get("category") != "SessionStatus":
            continue
        status = message.get("message")
        signature = (stamp, status)
        if signature in seen:
            continue
        seen.add(signature)
        if finish is not None:
            continue
        if status == "SESSION STARTED":
            if active is not None:
                raise RaceWeatherError("Repeated start without a suspension")
            active = stamp
            evidence.append(index)
        elif status in ("SESSION ABORTED", "SESSION SUSPENDED", "SESSION FINISHED"):
            if active is not None:
                if stamp <= active:
                    raise RaceWeatherError("Non-positive racing interval")
                intervals.append([active, stamp])
                evidence.append(index)
                active = None
            if status == "SESSION FINISHED":
                finish = stamp
    if active is not None or finish is None or not intervals:
        raise RaceWeatherError("Incomplete actual race timeline")
    flags = [
        stamp for stamp, _, message in ordered
        if message.get("flag") == "CHEQUERED"
        and message.get("scope") in (None, "Track")
        and message.get("driver_number") is None
        and stamp >= intervals[0][0]
    ]
    chequered = min(flags) if flags else None
    if chequered is not None:
        if abs((chequered - finish).total_seconds()) > 60:
            raise RaceWeatherError("Chequered flag and finish status disagree")
        if intervals[-1][0] < chequered:
            intervals[-1][1] = chequered
    if any(b <= a for a, b in intervals):
        raise RaceWeatherError("Invalid racing intervals")
    return {
        "session_key": int(session_key),
        "inicio_efetivo_utc": intervals[0][0].isoformat(),
        "fim_status_utc": finish.isoformat(),
        "bandeirada_utc": chequered.isoformat() if chequered else None,
        "criterio_fim": "chequered_flag" if chequered else "session_finished",
        "intervalos_ativos": [[a.isoformat(), b.isoformat()] for a, b in intervals],
        "duracao_ativa_s": sum((b - a).total_seconds() for a, b in intervals),
        "n_suspensoes": len(intervals) - 1,
        "indices_status_fonte": evidence,
    }


def _number(value, field):
    if value in (None, "", "None", "null"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    low, high = FIELDS[field]
    if not math.isfinite(result) or not low <= result <= high:
        return None
    if field == "rainfall" and result not in (0, 1):
        return None
    return result


def summarize_sensors(rows, window, min_coverage=0.95, max_gap_s=180):
    if not 0 < min_coverage <= 1 or max_gap_s <= 0:
        raise RaceWeatherError("Invalid coverage policy")
    intervals = [(instant(a), instant(b)) for a, b in window["intervalos_ativos"]]
    selected, duplicates, by_time = [], 0, {}
    for row in rows:
        if int(row.get("session_key", -1)) != window["session_key"]:
            raise RaceWeatherError("Weather session identity mismatch")
        if row.get("session_name") not in (None, "Race"):
            raise RaceWeatherError("Main-race weather contains a different modality")
        stamp = instant(row["date"])
        if not any(a <= stamp < b for a, b in intervals):
            continue
        values = {f: _number(row.get(f), f) for f in FIELDS}
        if stamp in by_time:
            if by_time[stamp] != values:
                raise RaceWeatherError("Conflicting weather at the same timestamp")
            duplicates += 1
            continue
        by_time[stamp] = values
        selected.append((stamp, values))
    selected.sort(key=lambda x: x[0])
    metrics = {}
    for field in FIELDS:
        covered, total, gaps, values = 0.0, 0.0, [], []
        for start, end in intervals:
            duration = (end - start).total_seconds()
            points = [(t, v[field]) for t, v in selected if start <= t < end and v[field] is not None]
            bins = {int((t - start).total_seconds() // 60) for t, _ in points}
            covered += sum(min(60.0, duration - k * 60) for k in bins)
            total += duration
            edges = [start] + [t for t, _ in points] + [end]
            gaps.extend((b - a).total_seconds() for a, b in zip(edges, edges[1:]))
            values.extend(v for _, v in points)
        coverage = covered / total
        maximum_gap = max(gaps)
        result = {
            "n_medicoes_validas": len(values), "cobertura_bins_60s": coverage,
            "maior_intervalo_sem_medicao_s": maximum_gap,
            "elegivel": coverage >= min_coverage and maximum_gap <= max_gap_s,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "media_amostras": statistics.mean(values) if values and field != "wind_direction" else None,
        }
        if field == "wind_direction" and values:
            x = sum(math.cos(math.radians(v)) for v in values)
            y = sum(math.sin(math.radians(v)) for v in values)
            result["media_circular_graus"] = math.degrees(math.atan2(y, x)) % 360 if math.hypot(x, y) > 1e-10 else None
        metrics[field] = result
    observed_rain = any(values["rainfall"] == 1 for _, values in selected)
    rain_known = metrics["rainfall"]["n_medicoes_validas"] > 0
    label = "desconhecido_cobertura_insuficiente"
    if metrics["rainfall"]["elegivel"]:
        label = "com_chuva_registrada" if observed_rain else "sem_chuva_registrada"
    return {
        **window, "n_medicoes_na_sessao": len(rows), "n_medicoes_ativas": len(selected),
        "n_duplicatas_identicas": duplicates, "campos": metrics,
        "chuva_observada_em_alguma_medicao": observed_rain if rain_known else None,
        "condicao_chuva": label,
        "politica": {"cobertura_minima": min_coverage, "gap_maximo_s": max_gap_s, "bin_s": 60},
        "uso": "contexto historico observado; sem inferir pista seca/molhada e sem uso no v1",
    }


def build_audit(archive_path, normalized_path, acquisition_path, destination):
    archive_path, normalized_path, acquisition_path, destination = map(
        Path, (archive_path, normalized_path, acquisition_path, destination)
    )
    if destination.exists():
        raise FileExistsError("Use a new destination; preserve previous evidence")
    archive = json.loads(archive_path.read_text())
    manifest_path = acquisition_path / "coleta_online.json"
    manifest = json.loads(manifest_path.read_text())
    sources = {x["arquivo"]: x for x in manifest["fontes"] if x.get("status") == 200}
    weather_path = normalized_path / "clima_pista.csv"
    weather = {}
    with weather_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            weather.setdefault(int(row["session_key"]), []).append(row)
    records, hashes = [], {}
    for gp in archive["gps"].values():
        race = main_race_session(gp["sessoes"])
        key = int(race["session_key"])
        relative = "openf1/{}/race_control.json".format(key)
        source = sources.get(relative)
        raw = (acquisition_path / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if source is None or source["sha256"] != digest:
            raise RaceWeatherError("Missing or mismatched race-control receipt")
        window = race_windows(json.loads(raw), key)
        records.append({**gp["identidade"], **summarize_sensors(weather.get(key, []), window),
                        "fonte_controle": relative, "sha256_controle": digest})
        hashes[relative] = digest
    destination.mkdir(parents=True)
    result = {
        "schema": "pitwall-race-weather-v1", "corridas": records,
        "fontes_controle_sha256": hashes,
        "sha256_clima_pista": hashlib.sha256(weather_path.read_bytes()).hexdigest(),
        "sha256_projecao": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "escopo": "corrida principal; intervalos ativos; suspensoes excluidas",
    }
    (destination / "clima_corridas.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    audit = build_audit(args.archive, args.normalized, args.acquisition, args.destination)
    print(json.dumps({"corridas": len(audit["corridas"]), "chuva": sum(x["condicao_chuva"] == "com_chuva_registrada" for x in audit["corridas"])}))
