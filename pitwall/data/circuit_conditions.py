"""Validate visually reviewed, season-specific circuit characteristics."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from pitwall.data.race_weather import main_race_session


def validate_review(row):
    value = dict(row)
    for key in ("temporada", "rodada", "session_key", "curvas", "pagina_mapa"):
        value[key] = int(row[key])
        if value[key] <= 0:
            raise ValueError("Invalid positive circuit-review field: " + key)
    for key in ("comprimento_km", "altitude_m"):
        value[key] = float(row[key])
        if not math.isfinite(value[key]):
            raise ValueError("Nonfinite circuit characteristic")
    if not 1 < value["comprimento_km"] < 10 or not 1 < value["curvas"] < 60:
        raise ValueError("Circuit length/corner count outside declared domain")
    if value["sentido"] not in ("horario", "anti_horario", "misto_oito"):
        raise ValueError("Unknown circuit direction")
    if value["circuito_id"] == "suzuka" and value["sentido"] != "misto_oito":
        raise ValueError("Suzuka cannot enter either binary-direction cohort")
    if value["estado_revisao"] != "conferido_visualmente":
        raise ValueError("Circuit review still pending")
    return value


def build_dataset(review_path, projection_path, acquisition_path, destination):
    review_path, projection_path, acquisition_path, destination = map(
        Path, (review_path, projection_path, acquisition_path, destination)
    )
    if destination.exists():
        raise FileExistsError("Use a new destination; preserve prior review")
    projection = json.loads(projection_path.read_text())
    expected = {(int(g["identidade"]["temporada"]), int(g["identidade"]["rodada"]),
                 g["identidade"]["circuito_id"], int(main_race_session(g["sessoes"])["session_key"]))
                for g in projection["gps"].values()}
    receipts = {x["arquivo"]: x for x in json.loads((acquisition_path / "coleta_online.json").read_text())["fontes"]
                if x.get("status") == 200}
    output, seen = [], set()
    with review_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            value = validate_review(row)
            key = tuple(value[k] for k in ("temporada", "rodada", "circuito_id", "session_key"))
            if key not in expected or key in seen:
                raise ValueError("Unverified or duplicate circuit/race identity")
            seen.add(key)
            relative = value["fonte_mapa"]
            raw = (acquisition_path / relative).read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            receipt = receipts.get(relative)
            if (not raw.startswith(b"%PDF") or receipt is None or digest != value["sha256_pdf"]
                    or digest != receipt["sha256"] or int(receipt["temporada"]) != value["temporada"]
                    or int(receipt["rodada"]) != value["rodada"]):
                raise ValueError("Missing, mismatched or wrong-season circuit map")
            output.append({**value, "url_arquivo_publico": receipt["url"],
                           "obtido_em_utc": receipt["obtido_em_utc"],
                           "uso": "contexto descritivo da edicao; nao altera variaveis congeladas do v1"})
    if seen != expected:
        raise ValueError("Not all races have a season-specific circuit review")
    result = {"schema": "pitwall-circuit-conditions-v1", "corridas": output,
              "sha256_revisao": hashlib.sha256(review_path.read_bytes()).hexdigest(),
              "sha256_projecao": hashlib.sha256(projection_path.read_bytes()).hexdigest(),
              "altitude_limite": "DEM aproximado no ponto do calendario; nao altitude media ou desnivel da pista."}
    destination.mkdir(parents=True)
    (destination / "circuitos_corridas.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("review", "projection", "acquisition", "destination"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    result = build_dataset(args.review, args.projection, args.acquisition, args.destination)
    print(json.dumps({"circuitos_por_edicao": len(result["corridas"])}))
