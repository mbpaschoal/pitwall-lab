"""Audit driver-analysis sources; no ranking, training or dashboard publication."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pitwall.data.race_weather import instant, main_race_session
from pitwall.data.tyre_reconciliation import columnar_rows, compound, parse_fastf1_utc, verify_identity

WMO_CODES = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
             71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}


def classify_start(result, canonical_laps, timed_laps):
    if not result:
        raise ValueError("Missing native session result for start audit")
    if result.get("dns") is True:
        if canonical_laps > 0 or timed_laps > 0:
            raise ValueError("DNS conflicts with observed/classified race laps")
        return False, "dns_explicito"
    if canonical_laps > 0 or (result.get("number_of_laps") or 0) > 0 or timed_laps > 0:
        return True, "voltas_observadas_ou_classificadas"
    if result.get("dnf") is True and result.get("dns") is False:
        return True, "abandono_zero_voltas_dns_false"
    raise ValueError("Insufficient evidence of race start")


def atmospheric_samples(data, window):
    if data.get("utc_offset_seconds") != 0 or data.get("timezone") not in ("GMT", "UTC", "Etc/GMT"):
        raise ValueError("Expected explicitly UTC atmospheric data")
    hourly, units = data["hourly"], data["hourly_units"]
    if units.get("cloud_cover") != "%" or units.get("weather_code") != "wmo code":
        raise ValueError("Unverified atmospheric units")
    if len({len(hourly[k]) for k in ("time", "cloud_cover", "weather_code")}) != 1:
        raise ValueError("Unequal atmospheric arrays")
    intervals = [(instant(a), instant(b)) for a, b in window["intervalos_ativos"]]
    samples, seen = [], set()
    for time, cloud, code in zip(hourly["time"], hourly["cloud_cover"], hourly["weather_code"]):
        dt = datetime.fromisoformat(time)
        dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        if dt in seen:
            raise ValueError("Duplicate atmospheric timestamp")
        seen.add(dt)
        if type(cloud) not in (int, float) or not 0 <= cloud <= 100 or type(code) is not int or code not in WMO_CODES:
            raise ValueError("Missing or invalid modeled cloud/WMO code")
        if any(a <= dt < b for a, b in intervals):
            samples.append({"time_utc": dt.isoformat(), "cloud_cover": cloud, "weather_code": code})
    if not samples:
        raise ValueError("No hourly model sample during active race intervals")
    return samples


def build_audit(archive_path, acquisition_path, dashboard_path, destination):
    archive_path, acquisition_path, dashboard_path, destination = map(
        Path, (archive_path, acquisition_path, dashboard_path, destination)
    )
    if destination.exists():
        raise FileExistsError("Use a new destination; preserve previous evidence")
    manifest = json.loads((acquisition_path / "coleta_online.json").read_text())
    receipts = {x["arquivo"]: x for x in manifest["fontes"] if x.get("status") == 200}
    hashes = {}

    def load(path):
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def captured(relative):
        path = acquisition_path / relative
        value = load(path)
        if relative not in receipts or hashes[str(path)] != receipts[relative]["sha256"]:
            raise ValueError("Missing or mismatched capture receipt: " + relative)
        return value

    def table(path):
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream))

    projection = load(dashboard_path)
    sessions = {(int(g["identidade"]["temporada"]), int(g["identidade"]["rodada"])):
                int(main_race_session(g["sessoes"])["session_key"]) for g in projection["gps"].values()}
    native = {}
    for year in sorted({k[0] for k in sessions}):
        for row in load(archive_path / "openf1" / str(year) / "session_result.json"):
            native[(row["session_key"], str(row["driver_number"]))] = row
    norm = archive_path / "normalizado"
    laps = table(norm / "laps_sessoes.csv")
    drivers = table(norm / "pilotos_sessoes.csv")
    timed = Counter((int(x["session_key"]), x["driver_number"]) for x in laps if x["lap_duration"] and float(x["lap_duration"]) > 0)
    starts = []
    for row in table(archive_path / "local/resultados.csv"):
        key = (sessions[(int(row["temporada"]), int(row["rodada"]))], row["numero"])
        started, method = classify_start(native.get(key), int(row["voltas"]), timed[key])
        starts.append({**row, "session_key": key[0], "largou": started, "criterio_largada": method,
                       "resultado_nativo": native[key], "voltas_cronometradas_nativas": timed[key],
                       "divergencia_status_dns": (row["status"] == "Did not start") != (not started)})
    weather = load(acquisition_path / "clima_validado_v1/clima_corridas.json")
    atmosphere = []
    for race in weather["corridas"]:
        relative = "atmosfera/{}/{}/cloud_weather_code.json".format(race["temporada"], race["rodada"])
        data = captured(relative)
        samples = atmospheric_samples(data, race)
        atmosphere.append({"temporada": race["temporada"], "rodada": race["rodada"],
            "session_key": race["session_key"], "circuito_id": race["circuito_id"],
            "fonte": relative, "sha256": receipts[relative]["sha256"], "amostras": samples,
            "media_amostras_horarias_cloud_cover": sum(x["cloud_cover"] for x in samples) / len(samples),
            "tipo": "reconstrucao_atmosferica_em_grade_ecmwf_ifs",
            "limite": "Amostras horarias dentro dos intervalos ativos; nao medem chuva ou pista molhada."})
    stints = table(norm / "stints.csv")
    plans = load(acquisition_path / "plano_compostos_alternativos.json")
    compounds, verifications, alternative_laps = [], [], []
    for plan in plans:
        key = plan["session_key"]
        relative = plan["directory"] + "/session_laptimes.json"
        rows = columnar_rows(captured(relative))
        extra_drivers = captured(plan["directory"] + "/drivers.json")
        session_drivers = {x["driver_number"]: x for x in drivers if int(x["session_key"]) == key}
        session_laps = {(x["driver_number"], int(x["lap_number"])): x for x in laps if int(x["session_key"]) == key}
        verification = verify_identity(rows, extra_drivers, session_drivers, session_laps)
        verifications.append({"session_key": key, **verification})
        if verification["numeros_voltas_divergentes"]:
            mapping = {(x["driver_number"], x["volta_alternativa"]): x for x in verification["numeros_voltas_divergentes"]}
            for row in rows:
                if row["ff1G"] is not False:
                    continue
                number, lap = str(row["dNum"]), int(row["lap"])
                duration = row["time"] if type(row["time"]) in (int, float) else None
                date = parse_fastf1_utc(row["lSD"]).isoformat() if row["lSD"] not in (None, "None", "") else None
                matched = mapping.get((number, lap))
                alternative_laps.append({"temporada": plan["temporada"], "rodada": plan["rodada"],
                    "session_key": key, "session_name": plan["session_name"], "driver_number": number,
                    "piloto_id": session_drivers[number]["piloto_id"], "lap_number": lap,
                    "lap_duration": duration, "date_start": date, "compound": compound(row["compound"]),
                    "stint_number": row["stint"], "is_accurate": row["iacc"] is True,
                    "is_generated": False, "lap_number_nativo_vinculado": matched["volta_nativa"] if matched else None,
                    "fonte_arquivo": relative, "fonte_sha256": receipts[relative]["sha256"]})
        for original in [x for x in stints if int(x["session_key"]) == key and x["compound"] in ("", "None", "UNKNOWN")]:
            number, stint = original["driver_number"], int(original["stint_number"])
            observed = [x for x in rows if str(x["dNum"]) == number and x["stint"] == stint and x["ff1G"] is False]
            known = {x["compound"] for x in observed if x["compound"] not in (None, "None", "UNKNOWN", "")}
            if len(known) > 1:
                raise ValueError("Conflicting alternative compounds")
            if known:
                status = "composto_recuperado_fonte_alternativa"
            elif number not in session_drivers:
                if any(str(x["dNum"]) == number for x in rows):
                    raise ValueError("Alternative driver lacks native-session identity")
                status = "registro_orfao_excluido_dos_cruzamentos"
            elif not observed and native.get((key, number), {}).get("number_of_laps") == 0:
                status = "zero_voltas_completadas_composto_nao_aplicavel"
            else:
                status = "indisponivel_nas_duas_fontes_consultadas"
            compounds.append({**original, "status_adjudicacao": status,
                "compound_complementar": next(iter(known)) if known else None,
                "n_voltas_alternativas_observadas": len(observed), "fonte_alternativa": relative,
                "fonte_alternativa_sha256": receipts[relative]["sha256"]})
    result = {"schema": "pitwall-driver-source-audit-v1", "largadas": starts,
              "atmosfera_modelada": atmosphere, "compostos": compounds,
              "sessoes_compostos_verificadas": verifications, "fontes_sha256": hashes,
              "voltas_corrida_fonte_alternativa": alternative_laps,
              "politica_numeracao": "Selecionar a fonte alternativa integral da sessao; nao deslocar linhas nativas sem correspondencia unica.",
              "limite": "Fontes novas nao alteram resultados originais ou modelo v1."}
    destination.mkdir(parents=True)
    (destination / "fontes_auditadas.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if alternative_laps:
        with (destination / "voltas_corrida_complementares.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(alternative_laps[0]))
            writer.writeheader()
            writer.writerows(alternative_laps)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "acquisition", "dashboard", "destination"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    value = build_audit(args.archive, args.acquisition, args.dashboard, args.destination)
    print(json.dumps({"largadas": sum(x["largou"] for x in value["largadas"]),
        "corridas_com_atmosfera": len(value["atmosfera_modelada"]),
        "compostos": dict(Counter(x["status_adjudicacao"] for x in value["compostos"]))}))
