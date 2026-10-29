"""Project audited supplements into the editable, descriptive presentation layer."""

from collections import defaultdict
from copy import deepcopy
from datetime import date
import argparse
import json
from pathlib import Path

from pitwall.data.archive import conteudo_sha256, validar
from pitwall.data.driver_conditions import validate


def supplement(archive, drivers):
    validar(archive)
    validate(drivers)
    result = deepcopy(archive)
    extra = drivers["suplementos_acervo"]
    observed = defaultdict(list)
    for row in extra["stints"]:
        observed[row["session_key"], int(row["driver_number"])].append(row)
    counters = {"estrategias_fonte_completa": 0, "compostos_recuperados": 0, "corridas_clima_efetivo": 0}
    for key, gp in result["gps"].items():
        if key in drivers["gps"]:
            gp["clima_corrida_efetiva"] = deepcopy(drivers["gps"][key])
            counters["corridas_clima_efetivo"] += 1
        for strategy in gp["estrategias"]:
            identity = strategy["session_key"], strategy["numero"]
            rows = observed.get(identity)
            if rows:
                strategy.setdefault("qualidade_fonte_original", strategy["qualidade"])
                strategy["sequencia_stints"] = [{"inicio": x["lap_start"], "fim": x["lap_end"],
                    "composto": x["compound"], "idade": None, "stint_number": x["stint_number"]} for x in rows]
                strategy["qualidade"] = [] if all(x["compound_elegivel"] for x in rows) else [{"flags": ["composto_ausente"]}]
                strategy["comparavel"] = not strategy["qualidade"]
                strategy["proveniencia_complementar"] = [{k: x[k] for k in ("fonte_arquivo", "fonte_sha256", "fonte_composto")} for x in rows]
                counters["estrategias_fonte_completa"] += 1
                continue
            for recovery in extra["compostos"]:
                if identity != (int(recovery["session_key"]), int(recovery["driver_number"])):
                    continue
                # Native boundaries identify the exact stint; array order is not an identity.
                candidates = [x for x in strategy["sequencia_stints"] if
                    str(x["inicio"]) == str(recovery["lap_start"]) and str(x["fim"]) == str(recovery["lap_end"])]
                if len(candidates) == 1 and not candidates[0]["composto"]:
                    candidates[0]["composto"] = recovery["compound_complementar"]
                    candidates[0]["proveniencia_complementar"] = recovery
                    counters["compostos_recuperados"] += 1
    result["conteudo_sha256"] = conteudo_sha256(result["gps"])
    result["suplemento_pilotos_sha256"] = drivers["conteudo_sha256"]
    validar(result)
    return result, counters


def circuit_panels(panels, drivers, verified_on):
    """Keep edition facts in edition overrides, never in a timeless circuit value."""
    date.fromisoformat(verified_on)
    validate(drivers)
    result = deepcopy(panels)
    directions = {"horario": "Horário", "anti_horario": "Anti-horário", "misto_oito": "Misto (traçado em oito)"}
    for gp in drivers["gps"].values():
        circuit = result["circuitos"][gp["circuito_id"]]
        circuit["verificado_em"] = verified_on
        circuit["por_temporada"].setdefault(str(gp["temporada"]), {}).update({
            "comprimento_km": gp["length_km"], "curvas": gp["corners"], "sentido": directions[gp["direction"]]})
        url = gp["circuit_source_url"]
        if not any(x["url"] == url for x in circuit["fontes"]):
            circuit["fontes"].append({"titulo": "FIA — mapa do circuito · {}".format(gp["temporada"]),
                "url": url, "campos": ["comprimento_km", "curvas", "sentido"], "sha256": gp["circuit_source_sha256"]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("drivers", "archive", "panels", "verified-on"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    drivers = json.loads(Path(args.drivers).read_text())
    archive, counts = supplement(json.loads(Path(args.archive).read_text()), drivers)
    panels = circuit_panels(json.loads(Path(args.panels).read_text()), drivers, args.verified_on)
    # Both projections are validated/built before either presentation file is written.
    for destination, payload in ((args.archive, archive), (args.panels, panels)):
        path = Path(destination)
        options = {"indent": 2} if destination == args.panels else {"separators": (",", ":")}
        path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, **options) + "\n")
    print(json.dumps(counts))
