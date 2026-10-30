"""Portable, audited inputs for descriptive driver comparisons, separate from v1."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path

ASSET = "frontend_assets/pilotos_condicoes.json"
SCHEMA = "pitwall-driver-conditions-v1"


class DriverConditionsError(ValueError):
    pass


def content_hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate(asset):
    if not isinstance(asset, dict) or asset.get("schema") != SCHEMA:
        raise DriverConditionsError("Unrecognized driver-condition dataset")
    payload = {k: v for k, v in asset.items() if k != "conteudo_sha256"}
    if asset.get("conteudo_sha256") != content_hash(payload):
        raise DriverConditionsError("Driver-condition content hash does not match")
    quality = asset.get("qualidade", {})
    if quality.get("gate_pilotos") is not True or quality.get("pendencias_obrigatorias_sem_tratamento") != 0:
        raise DriverConditionsError("Driver data gate is not satisfied")
    gps = asset.get("gps", {})
    if not gps or len(gps) != quality["corridas"]:
        raise DriverConditionsError("Missing main-race coverage")
    for key, gp in gps.items():
        if key != "{}:{}".format(gp["temporada"], gp["rodada"]) or gp["session_name"] != "Race":
            raise DriverConditionsError("Sprint or mismatched race in driver dataset")
        if gp["rain_condition"] not in ("recorded", "not_recorded"):
            raise DriverConditionsError("Unverified rainfall condition")
        if gp["direction"] not in ("horario", "anti_horario", "misto_oito"):
            raise DriverConditionsError("Unverified circuit direction")
        for field in ("track_temperature", "air_temperature", "humidity", "pressure", "wind_speed", "altitude_m", "corners"):
            if type(gp[field]) not in (float, int) or not math.isfinite(gp[field]):
                raise DriverConditionsError("Missing observed/reference condition: " + field)
        for field in gp.get("available_fields", []):
            if gp.get(field) is None:
                raise DriverConditionsError("Advertised field missing: " + field)
        direction = gp.get("wind_direction")
        if direction is not None and (type(direction) not in (int, float) or not math.isfinite(direction) or not 0 <= direction < 360):
            raise DriverConditionsError("Invalid circular wind direction")
    seen = set()
    for row in asset.get("resultados", []):
        key = row["race_id"], row["driver_id"]
        if key in seen or row["race_id"] not in gps or not row["driver_id"] or not row["team_id"]:
            raise DriverConditionsError("Duplicate or unverified driver/race identity")
        seen.add(key)
        if any(type(row[f]) is not bool for f in ("started", "disqualified", "retired")):
            raise DriverConditionsError("Unknown start/outcome status")
        if row["position"] is not None and (type(row["position"]) is not int or row["position"] < 1):
            raise DriverConditionsError("Invalid classification position")
        if row["grid"] is not None and (type(row["grid"]) is not int or row["grid"] < 1):
            raise DriverConditionsError("Invalid comparable grid position")
    if len(seen) != quality["resultados"] or sum(x["started"] for x in asset["resultados"]) != quality["largadas"]:
        raise DriverConditionsError("Driver denominator differs from audited starts")
    return asset


def load(root):
    root = Path(root).resolve()
    path = root / ASSET
    current = path
    while current != root:
        if current.is_symlink():
            raise DriverConditionsError("O acervo de pilotos não pode usar symlink.")
        current = current.parent
    try:
        if path.stat().st_size > 4 * 1024 * 1024:
            raise DriverConditionsError("Driver dataset exceeds portable size limit")
        return validate(json.loads(path.read_text(encoding="utf-8")))
    except DriverConditionsError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise DriverConditionsError("Dados de pilotos indisponíveis ou inválidos.") from error


def assemble(acquisition_path, gate_path, output):
    base, gate_path, output = map(Path, (acquisition_path, gate_path, output))
    gate = json.loads(gate_path.read_text())
    paths = {"weather": base / "clima_validado_v1/clima_corridas.json",
             "sources": base / "fontes_validadas_v2/fontes_auditadas.json",
             "tyres": base / "pneus_validados_v2/pneus_adjudicados.json",
             "circuits": base / "circuitos_validados_v1/circuitos_corridas.json"}
    hashes = {key: sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
    if set(hashes.values()) != set(gate["fontes_sha256"].values()):
        raise DriverConditionsError("Inputs differ from the reviewed data gate")
    data = {key: json.loads(path.read_text()) for key, path in paths.items()}
    plans = json.loads((base / "plano_corridas.json").read_text())
    weather = {(int(x["temporada"]), int(x["rodada"])): x for x in data["weather"]["corridas"]}
    circuits = {(int(x["temporada"]), int(x["rodada"])): x for x in data["circuits"]["corridas"]}
    gps = {}
    for race in plans:
        key = race["temporada"], race["rodada"]
        w, c = weather[key], circuits[key]
        record = {"temporada": key[0], "rodada": key[1], "circuito_id": race["circuito_id"],
            "session_key": race["session_key"], "session_name": "Race", "name": race["corrida"],
            "date_utc": w["inicio_efetivo_utc"][:10], "race_start_utc": w["inicio_efetivo_utc"],
            "rain_condition": "recorded" if w["condicao_chuva"] == "com_chuva_registrada" else "not_recorded",
            "direction": c["sentido"], "corners": c["curvas"], "length_km": c["comprimento_km"],
            "altitude_m": c["altitude_m"], "circuit_source_url": c["url_arquivo_publico"],
            "circuit_source_sha256": c["sha256_pdf"]}
        record["active_intervals_utc"] = w["intervalos_ativos"]
        record["race_finish_utc"] = w["bandeirada_utc"]
        record["weather_samples"] = w["n_medicoes_ativas"]
        record["atmospheric_context"] = next(x for x in data["sources"]["atmosfera_modelada"]
            if (x["temporada"], x["rodada"]) == key)
        for field in ("track_temperature", "air_temperature", "humidity", "pressure", "wind_speed"):
            if not w["campos"][field]["elegivel"]:
                raise DriverConditionsError("Ineligible sensor field")
            record[field] = w["campos"][field]["media_amostras"]
        record["wind_direction"] = w["campos"]["wind_direction"]["media_circular_graus"]
        record["available_fields"] = [field for field in ("track_temperature", "air_temperature", "humidity", "pressure", "wind_speed", "wind_direction", "corners", "length_km", "altitude_m") if record.get(field) is not None]
        record["wind_direction_status"] = "available" if record["wind_direction"] is not None else "indeterminate"
        gps["{}:{}".format(*key)] = record
    rows = []
    for row in data["sources"]["largadas"]:
        native = row["resultado_nativo"]
        rows.append({"race_id": "{}:{}".format(row["temporada"], row["rodada"]),
            "driver_id": row["piloto_id"], "driver_name": row["piloto"], "team_id": row["equipe_id"],
            "number": int(row["numero"]), "started": row["largou"], "disqualified": native.get("dsq") is True,
            "retired": native.get("dnf") is True, "position": int(row["posicao_final"]) if row["posicao_final"] else None,
            "grid": int(row["grid_resultado_auditoria"]) if int(row["grid_resultado_auditoria"] or 0) > 0 else None,
            "grid_raw": row["grid_resultado_auditoria"], "points": float(row["pontos"]),
            "completed_laps": int(row["voltas"]), "canonical_status": row["status"],
            "start_criterion": row["criterio_largada"]})
    result = {"schema": SCHEMA, "qualidade": {k: gate[k] for k in ("gate_pilotos", "pendencias_obrigatorias_sem_tratamento",
        "completude_fisica_de_todos_os_campos", "compostos_indisponiveis_declarados", "corridas", "chuva_registrada", "resultados", "largadas", "dns")},
        "gps": gps, "resultados": rows, "fontes_sha256": hashes,
        "suplementos_acervo": {"stints": data["tyres"]["stints_complementares_pilotos_afetados"],
            "adjudicacoes_stints": data["tyres"]["adjudicacoes"],
            "compostos": [{k: x[k] for k in ("session_key", "driver_number", "stint_number", "lap_start", "lap_end", "compound_complementar", "fonte_alternativa", "fonte_alternativa_sha256")}
                           for x in data["sources"]["compostos"] if x["compound_complementar"] is not None],
            "voltas": data["sources"]["voltas_corrida_fonte_alternativa"]},
        "escopo": "analise descritiva posterior; sem alteracao do modelo preditivo v1"}
    result["conteudo_sha256"] = content_hash(result)
    validate(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("acquisition", "gate", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    asset = assemble(args.acquisition, args.gate, args.output)
    print(json.dumps({"races": len(asset["gps"]), "results": len(asset["resultados"])}))
