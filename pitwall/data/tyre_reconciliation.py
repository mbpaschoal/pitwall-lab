"""Reconcile tyre-bound gaps using pinned lap data without changing raw sources.

TracingInsights and OpenF1 can share the upstream F1 timing feed. Agreement
therefore verifies the join, not independent scientific confirmation.
"""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


class TyreReconciliationError(ValueError):
    pass


def parse_fastf1_utc(value):
    """LapStartDate uses the UTC telemetry clock; pandas can serialize it naive."""
    serialized = re.sub(r"(\.\d{6})\d+", r"\1", value.replace("Z", "+00:00"))
    result = datetime.fromisoformat(serialized)
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def columnar_rows(data):
    required = {"lap", "stint", "compound", "drv", "dNum", "ff1G", "time"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise TyreReconciliationError("Missing alternative-lap columns")
    if not all(isinstance(v, list) for v in data.values()) or len({len(v) for v in data.values()}) != 1:
        raise TyreReconciliationError("Unequal or invalid column lengths")
    return [dict(zip(data, values)) for values in zip(*data.values())]


def positive_integer(value):
    if isinstance(value, bool):
        raise TyreReconciliationError("Boolean lap/stint number")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise TyreReconciliationError("Invalid lap/stint number")
    if not math.isfinite(number) or number < 1 or not number.is_integer():
        raise TyreReconciliationError("Invalid lap/stint number")
    return int(number)


def compound(value):
    return None if value in (None, "", "None", "UNKNOWN", "null") else value


def observed_stints(rows, native_stints):
    """Keep observed rows; compound and bounds retain field-level provenance."""
    groups, seen = defaultdict(list), set()
    for row in rows:
        if row["ff1G"] is not False:
            continue
        lap, stint = positive_integer(row["lap"]), positive_integer(row["stint"])
        if lap in seen:
            raise TyreReconciliationError("Repeated observed lap for driver")
        seen.add(lap)
        groups[stint].append((lap, compound(row["compound"])))
    ordinal_compatible = True
    for stint, values in groups.items():
        known = {v for _, v in values if v is not None}
        original = native_stints.get(stint)
        original_compound = compound(original["compound"]) if original else None
        if known and original_compound and known != {original_compound}:
            ordinal_compatible = False
    output = {}
    for stint, values in groups.items():
        native = native_stints.get(stint)
        known = {v for _, v in values if v is not None}
        native_compound = compound(native["compound"]) if native else None
        if len(known) > 1:
            raise TyreReconciliationError("Contradictory alternative compound inside stint")
        conflict = bool(known and native_compound and known != {native_compound})
        fallback = native_compound if ordinal_compatible else None
        selected = next(iter(known)) if known else fallback
        laps = sorted(v[0] for v in values)
        if laps != list(range(laps[0], laps[-1] + 1)):
            raise TyreReconciliationError("Unobserved lap inside reconstructed bounds")
        output[stint] = {
            "stint_number": stint, "lap_start": laps[0], "lap_end": laps[-1],
            "compound": selected, "compound_elegivel": selected is not None, "n_voltas_observadas": len(laps),
            "composto_nativo": native_compound, "conflito_composto_nativo": conflict,
            "mapa_ordinais_compativel": ordinal_compatible,
            "fonte_limites": "tracinginsights_lap_number", "linhas_geradas_usadas": 0,
            "fonte_composto": "tracinginsights" if known else ("openf1_stints" if fallback else None),
        }
    ordered = sorted(output.values(), key=lambda x: x["stint_number"])
    if any(a["lap_end"] >= b["lap_start"] for a, b in zip(ordered, ordered[1:])):
        raise TyreReconciliationError("Nonchronological or overlapping stints")
    return output


def absence_status(result):
    if not result or result.get("number_of_laps") != 0:
        raise TyreReconciliationError("Missing observed bounds without zero-lap evidence")
    if result.get("dns") is True:
        return "nao_largou_limites_nao_aplicaveis"
    if result.get("dnf") is True:
        return "zero_voltas_completadas_limites_nao_aplicaveis"
    raise TyreReconciliationError("Zero laps do not establish DNS or retirement")


def verify_identity(rows, drivers, native_drivers, native_laps):
    metadata = {x["driver"]: x for x in drivers["drivers"]}
    if len(metadata) != len(drivers["drivers"]):
        raise TyreReconciliationError("Duplicate alternative-driver identity")
    compared = matched = 0
    for row in rows:
        number = str(row["dNum"])
        native = native_drivers.get(number)
        extra = metadata.get(row["drv"])
        if (native is None or row["drv"] != native["name_acronym"] or extra is None
                or (extra.get("dn") is not None and str(extra["dn"]) != number)):
            raise TyreReconciliationError("Unverified literal driver-number/acronym join")
        lap = positive_integer(row["lap"])
        original = native_laps.get((number, lap))
        duration = row["time"]
        if original and original["lap_duration"] and type(duration) in (int, float) and row["ff1G"] is False:
            compared += 1
            matched += abs(float(original["lap_duration"]) - duration) <= .2
    original_compared, original_matched = compared, matched
    method, number_differences = "numero_volta_e_duracao", []
    if compared < 10 or matched / compared < .95:
        # Lap counters can drift in an upstream adapter. Never shift a whole
        # session by assumption: require a unique timestamp AND duration match
        # for each observed lap, within the already verified driver identity.
        method = "piloto_horario_utc_e_duracao_unicos"
        compared = matched = 0
        used = set()
        for row in rows:
            if row["ff1G"] is not False or type(row["time"]) not in (int, float) or row.get("lSD") in (None, "None", ""):
                continue
            compared += 1
            source_time = parse_fastf1_utc(row["lSD"])
            candidates = []
            for (number, lap), original in native_laps.items():
                if number != str(row["dNum"]) or not original["date_start"] or not original["lap_duration"]:
                    continue
                native_time = datetime.fromisoformat(original["date_start"].replace("Z", "+00:00"))
                if native_time.tzinfo is None:
                    raise TyreReconciliationError("Native timestamp lacks UTC offset")
                if abs((native_time - source_time).total_seconds()) <= 3 and abs(float(original["lap_duration"]) - row["time"]) <= .2:
                    candidates.append((number, lap))
            if len(candidates) == 1 and candidates[0] not in used:
                selected = candidates[0]
                used.add(selected)
                matched += 1
                if selected[1] != int(row["lap"]):
                    number_differences.append({"driver_number": selected[0], "volta_nativa": selected[1],
                        "volta_alternativa": int(row["lap"]), "inicio_nativo": native_laps[selected]["date_start"],
                        "inicio_alternativo_utc": source_time.isoformat(), "duracao_alternativa_s": row["time"]})
        if compared < 10 or matched / compared < .95:
            raise TyreReconciliationError("Session timestamp/duration fingerprint does not match")
    return {"identidades_literais_verificadas": len(rows),
            "metadados_sem_numero": sum(x.get("dn") is None for x in metadata.values()), "tempos_comparados": compared,
            "tempos_concordantes_tolerancia_02s": matched, "fracao_concordante": matched / compared,
            "metodo_correspondencia": method, "numeros_voltas_divergentes": number_differences,
            "comparacao_numeracao_original": {"comparados": original_compared, "concordantes": original_matched}}


def build_reconciliation(archive_path, normalized_path, acquisition_path, destination):
    archive_path, normalized_path, acquisition_path, destination = map(
        Path, (archive_path, normalized_path, acquisition_path, destination)
    )
    if destination.exists():
        raise FileExistsError("Use a new destination; preserve prior evidence")
    plan = json.loads((acquisition_path / "plano_fontes_pneus.json").read_text())
    manifest = json.loads((acquisition_path / "coleta_online.json").read_text())
    receipts = {x["arquivo"]: x for x in manifest["fontes"] if x.get("status") == 200}
    sources = {}

    def read_csv(name):
        path = normalized_path / name
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream))

    def captured(relative, commit):
        raw = (acquisition_path / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        receipt = receipts.get(relative)
        if receipt is None or receipt["sha256"] != digest or "/" + commit + "/" not in receipt["url"]:
            raise TyreReconciliationError("Missing, mismatched or unpinned source receipt")
        sources[relative] = digest
        return json.loads(raw)

    stints = read_csv("stints.csv")
    identities, laps = read_csv("pilotos_sessoes.csv"), read_csv("laps_sessoes.csv")
    bad = [x for x in stints if x["limites_voltas_comparaveis"] == "False"]
    results = {}
    for year in {x["temporada"] for x in plan}:
        path = archive_path / "openf1" / str(year) / "session_result.json"
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for row in json.loads(path.read_text()):
            results[(int(row["session_key"]), str(row["driver_number"]))] = row
    decisions, supplemental, sessions = [], [], []
    for item in plan:
        key = item["session_key"]
        relative = item["directory"] + "/session_laptimes.json"
        rows = columnar_rows(captured(relative, item["commit"]))
        drivers = captured(item["directory"] + "/drivers.json", item["commit"])
        native_drivers = {x["driver_number"]: x for x in identities if int(x["session_key"]) == key}
        native_laps = {(x["driver_number"], int(x["lap_number"])): x for x in laps if int(x["session_key"]) == key}
        fingerprint = verify_identity(rows, drivers, native_drivers, native_laps)
        sessions.append({**item, **fingerprint, "fonte_sha256": sources[relative]})
        targets = [x for x in bad if int(x["session_key"]) == key]
        for number in sorted({x["driver_number"] for x in targets}, key=int):
            original = {int(x["stint_number"]): x for x in stints if int(x["session_key"]) == key and x["driver_number"] == number}
            observed = observed_stints([x for x in rows if str(x["dNum"]) == number], original)
            identity = native_drivers[number]
            for stint in observed.values():
                supplemental.append({"session_key": key, "driver_number": number,
                    "piloto_id": identity["piloto_id"], "temporada": item["temporada"],
                    "rodada": item["rodada"], "session_name": item["session_name"],
                    **stint, "fonte_arquivo": relative, "fonte_sha256": sources[relative]})
            for target in [x for x in targets if x["driver_number"] == number]:
                recovered = observed.get(int(target["stint_number"]))
                if recovered and recovered["conflito_composto_nativo"]:
                    raise TyreReconciliationError("Cannot repair target using conflicting compound/stint join")
                status = "limites_recuperados_fonte_alternativa" if recovered else absence_status(results.get((key, number)))
                decisions.append({"session_key": key, "driver_number": number,
                    "piloto_id": identity["piloto_id"], "stint_number": int(target["stint_number"]),
                    "limites_originais": [target["lap_start"], target["lap_end"]],
                    "status": status, "limites_complementares": recovered,
                    "fonte_alternativa": relative, "fonte_sha256": sources[relative],
                    "resultado_sessao": results.get((key, number))})
    if len(decisions) != len(bad):
        raise TyreReconciliationError("Not all original tyre-bound issues adjudicated")
    output = {"schema": "pitwall-tyre-bounds-v1", "adjudicacoes": decisions,
              "stints_complementares_pilotos_afetados": supplemental,
              "sessoes_verificadas": sessions, "fontes_sha256": sources,
              "limite": "Ausencias justificadas nao recuperam limites nativos; linhas FastF1Generated excluidas."}
    destination.mkdir(parents=True)
    (destination / "pneus_adjudicados.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--normalized", required=True)
    parser.add_argument("--acquisition", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    result = build_reconciliation(args.archive, args.normalized, args.acquisition, args.destination)
    print(json.dumps({"adjudicacoes": len(result["adjudicacoes"]),
                      "recuperados": sum(x["status"] == "limites_recuperados_fonte_alternativa" for x in result["adjudicacoes"])}))
