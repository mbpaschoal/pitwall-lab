"""Read the pinned F1DB archive and build the championship photo inventory."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"DNS", "DNQ", "DNPQ", "DNP", "WD"}
MANUFACTURER_DOCUMENTATION = {
    (1956, "ferrari"): {
        "ferrari-d50": {
            "nome": "Ferrari D50",
            "fonte": "https://www.ferrari.com/content/dam/ferrari-fcom/old/pdf/pr_90_years_eng_fin.pdf",
        },
    },
}


def build(archive, hall, teams):
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != hall["sha256_f1db"]:
        raise ValueError("F1DB archive does not match the Hall of Fame")

    with ZipFile(archive) as source:
        def read(name):
            return json.loads(source.read(f"f1db-{name}.json"))

        constructors = {row["id"]: row["name"] for row in read("constructors")}
        cars = {row["id"]: row for row in read("chassis")}
        driver_titles = read("seasons-driver-standings")
        constructor_titles = read("seasons-constructor-standings")
        season_cars = read("seasons-entrants-chassis")
        season_drivers = read("seasons-entrants-drivers")
        season_entries = read("seasons-entrants-constructors")
        race_results = read("races-race-results")

    campaigns = defaultdict(lambda: {"pilotos": [], "construtores": False})
    hall_titles = {}
    moments = defaultdict(set)
    for key, driver in hall["pilotos"].items():
        events = [driver["estreia"], driver["primeira_vitoria"]]
        for title in driver["titulos"]:
            season = title["ano"]
            hall_titles[season] = key
            events.append(title["decisao"])
            for constructor in title["construtores"]:
                campaigns[season, constructor["id"]]["pilotos"].append(key)
        for event in events:
            moments[event["ano"], event["rodada"], event["gp"]].add(key)
    expected_titles = {row["year"]: row["driverId"] for row in driver_titles if row["championshipWon"]}
    if hall_titles != expected_titles:
        raise ValueError("Driver titles in the Hall of Fame differ from F1DB")
    for row in constructor_titles:
        if row["championshipWon"]:
            campaigns[row["year"], row["constructorId"]]["construtores"] = True

    entered_cars = defaultdict(set)
    for row in season_cars:
        key = (row["year"], row["constructorId"], row["entrantId"], row["engineManufacturerId"])
        entered_cars[key].add(row["chassisId"])
    points = {(row["year"], row["constructorId"], row["engineManufacturerId"], row["driverId"], row["round"])
              for row in race_results if row["positionText"] not in EXCLUDED and (row["points"] or 0) > 0}
    entries_by_driver = defaultdict(list)
    for row in season_drivers:
        if not row["testDriver"] and row["rounds"]:
            entries_by_driver[row["year"], row["constructorId"]].append(row)
    entered_by_constructor = defaultdict(list)
    for row in season_entries:
        entered_by_constructor[row["year"], row["constructorId"]].append(row)

    output = []
    used_cars = set()
    documented_cars = {}
    for (year, constructor), campaign in sorted(campaigns.items()):
        driver_entries = entries_by_driver[year, constructor]
        shortlist = set()
        for row in driver_entries:
            key = (year, constructor, row["entrantId"], row["engineManufacturerId"])
            if row["driverId"] in campaign["pilotos"]:
                shortlist.update(entered_cars[key])
            if campaign["construtores"] and any(
                (year, constructor, row["engineManufacturerId"], row["driverId"], round_) in points
                for round_ in row["rounds"]
            ):
                shortlist.update(entered_cars[key])
        if not shortlist:
            for row in entered_by_constructor[year, constructor]:
                shortlist.update(entered_cars[year, constructor, row["entrantId"], row["engineManufacturerId"]])
        if not shortlist:
            raise ValueError(f"No chassis entries for {year} {constructor}")
        documented = MANUFACTURER_DOCUMENTATION.get((year, constructor), {})
        documented_cars.update({key: entry["nome"] for key, entry in documented.items()})
        shortlist.update(documented)
        used_cars.update(shortlist)
        row = {"ano": year, "equipe": constructor, **campaign, "modelos_candidatos": sorted(shortlist)}
        if documented:
            row["modelos_documentados"] = documented
        output.append(row)

    return {
        "schema": 1,
        "fonte": hall["fonte_dados"],
        "sha256": digest,
        "pilotos": {key: profile["nome"] for key, profile in hall["pilotos"].items()},
        "equipes_campeas": {key: constructors[key] for key in sorted({key for _, key in campaigns})},
        "equipes_atuais": {key: profile["nome"] for key, profile in teams["equipes"].items()},
        "modelos": {key: documented_cars[key] if key in documented_cars else cars[key]["fullName"]
                    for key in sorted(used_cars)},
        "campanhas": output,
        "momentos": [{"ano": year, "rodada": round_, "gp": gp, "pilotos": sorted(keys)}
                     for (year, round_, gp), keys in sorted(moments.items())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("f1db", type=Path)
    parser.add_argument("destino", type=Path)
    args = parser.parse_args()
    hall = json.loads((ROOT / "frontend_assets/hall_da_fama.json").read_text())
    teams = json.loads((ROOT / "frontend_assets/perfis_equipes.json").read_text())
    inventory = build(args.f1db, hall, teams)
    args.destino.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
