"""Auditoria A1 do archive Kaggle por chaves estrangeiras literais, sem fuzzy matching."""

import csv
import hashlib
import json
from pathlib import Path
from pitwall.paths import PROJECT_ROOT

RAIZ = PROJECT_ROOT
ARCHIVE = (Path.home() / "Downloads" / "archive")


def _ler(nome):
    with (ARCHIVE / nome).open(encoding="utf8", newline="") as f:
        return list(csv.DictReader(f))


def _hash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(path, linhas):
    with path.open("w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


def executar(destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=False)
    races = {
        x["raceId"]: x for x in _ler("races.csv") if 2021 <= int(x["year"]) <= 2025
    }
    drivers = {x["driverId"]: x for x in _ler("drivers.csv")}
    constructors = {x["constructorId"]: x for x in _ler("constructors.csv")}
    circuits = {x["circuitId"]: x for x in _ler("circuits.csv")}
    mapa = []
    for driver_id, d in sorted(drivers.items(), key=lambda x: int(x[0])):
        mapa.append(
            {
                "tipo": "piloto",
                "archive_id": driver_id,
                "canonico_id": d["driverRef"],
                "metodo": "literal_foreign_key",
                "status": "mapeado",
                "motivo": "",
            }
        )
    for cid, c in sorted(constructors.items(), key=lambda x: int(x[0])):
        mapa.append(
            {
                "tipo": "equipe",
                "archive_id": cid,
                "canonico_id": c["constructorRef"],
                "metodo": "literal_foreign_key",
                "status": "mapeado",
                "motivo": "",
            }
        )
    for cid, c in sorted(circuits.items(), key=lambda x: int(x[0])):
        mapa.append(
            {
                "tipo": "circuito",
                "archive_id": cid,
                "canonico_id": c["circuitRef"],
                "metodo": "literal_foreign_key",
                "status": "mapeado",
                "motivo": "",
            }
        )
    _csv(destino / "mapa_identidades_v2.csv", mapa)
    qualifying = _ler("qualifying.csv")
    archive_q = {}
    for x in qualifying:
        race = races.get(x["raceId"])
        if race:
            archive_q[
                (
                    int(race["year"]),
                    int(race["round"]),
                    drivers[x["driverId"]]["driverRef"],
                )
            ] = (
                x["position"] or None
            )
    with (RAIZ / "data/preparado/base_historica.csv").open(
        encoding="utf8", newline=""
    ) as f:
        base = list(csv.DictReader(f))
    conflitos = []
    for x in base:
        k = (int(x["temporada"]), int(x["rodada"]), x["piloto_id"])
        alternativo = archive_q.get(k)
        if alternativo is not None and x["posicao_classificacao"] not in (
            "",
            alternativo,
        ):
            conflitos.append(
                {
                    "temporada": k[0],
                    "rodada": k[1],
                    "piloto_id": k[2],
                    "campo": "posicao_classificacao",
                    "valor_canonico": x["posicao_classificacao"],
                    "fonte_canonica": "v1_jolpica",
                    "valor_alternativo": alternativo,
                    "fonte_alternativa": "archive_kaggle",
                    "status_decisao": "unadjudicated",
                    "justificativa": "divergência preservada; sem adjudicação automática",
                    "evidencia_id": "archive-qualifying-v1",
                }
            )
    _csv(destino / "conflitos_campos_v2.csv", conflitos)
    manifest = []
    for p in sorted(ARCHIVE.glob("*.csv")):
        with p.open(encoding="utf8", newline="") as f:
            rows = sum(1 for _ in f) - 1
        manifest.append(
            {
                "arquivo": p.name,
                "sha256": _hash(p),
                "linhas": rows,
                "capturado_em_utc": "unknown",
                "publicado_em_utc": "unknown",
                "disponivel_em_utc": "unknown",
            }
        )
    (destino / "manifesto_archive_v2.json").write_text(
        json.dumps(
            {
                "schema": "metodologia-v2-archive-a1",
                "fontes": manifest,
                "divergencias_qualifying": len(conflitos),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    return len(mapa), len(conflitos)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--destino", required=True)
    a = p.parse_args()
    print(executar(a.destino))
