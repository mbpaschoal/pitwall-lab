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
CHASSIS_WITHOUT_TITLE_CONTRIBUTION = {
    (1952, "ferrari"): {
        "ferrari-375s": (
            "Ascari abandonou em Indianápolis e não marcou pontos com o 375.",
            "Ascari retired at Indianapolis and scored no points in the 375.",
            "https://www.formula1.com/en/results/1952/races/110/indianapolis-500/race-result",
        ),
    },
    (1953, "ferrari"): {
        "ferrari-553": (
            "Maglioli e Carini disputaram Monza com o 553. Ascari correu com o Ferrari 500.",
            "Maglioli and Carini raced the 553 at Monza. Ascari drove the Ferrari 500.",
            "https://www.motorsportmagazine.com/archive/article/october-1953/11/the-italian-grand/",
        ),
    },
    (1954, "maserati"): {
        "maserati-a6gcm": (
            "Fangio venceu as duas corridas que disputou pela Maserati com o 250F.",
            "Fangio won both of his championship races for Maserati in the 250F.",
            "https://www.museofangio.com/es/juan-manuel-fangio/autos/6/",
        ),
    },
    (1956, "ferrari"): {
        "ferrari-555": (
            "Gendebien correu com o 555 na Argentina. Fangio venceu em um Lancia-Ferrari D50 compartilhado com Musso.",
            "Gendebien raced the 555 in Argentina. Fangio won in a Lancia-Ferrari D50 shared with Musso.",
            "https://www.oldracingcars.com/results/result.php?RaceID=RA56",
        ),
    },
    (1962, "brm"): {
        "brm-p48-57": (
            "Ginther abandonou as duas provas que disputou com o P48/57, nos Países Baixos e em Mônaco.",
            "Ginther retired from both of his races in the P48/57, in the Netherlands and Monaco.",
            "https://www.statsf1.com/en/richie-ginther/grand-prix.aspx",
        ),
    },
    (1969, "matra"): {
        "matra-ms7": (
            "O MS7 disputou a classe de Fórmula 2 no GP da Alemanha, sem pontuar no Mundial de F1.",
            "The MS7 ran in the Formula 2 class at the German Grand Prix and scored no F1 World Championship points.",
            "https://www.motorsportmagazine.com/database/races/1969-german-grand-prix-f2-class/",
        ),
    },
    (1976, "mclaren"): {
        "mclaren-m26": (
            "Jochen Mass estreou o M26 em Zandvoort. James Hunt disputou o título com o M23.",
            "Jochen Mass debuted the M26 at Zandvoort. James Hunt won the title in the M23.",
            "https://www.mclaren.com/racing/heritage/formula-1/cars/1977-formula-1-mclaren-m26/overlooked-mclaren-m26/",
        ),
    },
    (1982, "williams"): {
        "williams-fw07d": (
            "O FW07D de seis rodas foi um protótipo de testes.",
            "The six-wheeled FW07D was a test prototype.",
            "https://www.williamsf1.com/articles/5c209d53-a930-4af2-b624-fc69190f1463/six-unbelievable-facts-you-might-not-have-known-about-williams",
        ),
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
        grands_prix = {row["id"]: row["fullName"] for row in read("grands-prix")}
        races = read("races")
        cars = {row["id"]: row for row in read("chassis")}
        driver_titles = read("seasons-driver-standings")
        constructor_titles = read("seasons-constructor-standings")
        season_cars = read("seasons-entrants-chassis")
        season_drivers = read("seasons-entrants-drivers")
        season_entries = read("seasons-entrants-constructors")
        race_results = read("races-race-results")

    campaigns = defaultdict(lambda: {"pilotos": [], "construtores": False})
    hall_titles = {}
    moments = {}
    for key, driver in hall["pilotos"].items():
        events = [driver["estreia"], driver["primeira_vitoria"]]
        for title in driver["titulos"]:
            season = title["ano"]
            hall_titles[season] = key
            events.append(title["decisao"])
            for constructor in title["construtores"]:
                campaigns[season, constructor["id"]]["pilotos"].append(key)
        for event in events:
            year, round_ = event["ano"], event["rodada"]
            moment = moments.setdefault((year, round_), {
                "ano": year, "rodada": round_, "gp": event["gp"], "pilotos": set(),
            })
            moment["pilotos"].add(key)
    expected_titles = {row["year"]: row["driverId"] for row in driver_titles if row["championshipWon"]}
    if hall_titles != expected_titles:
        raise ValueError("Driver titles in the Hall of Fame differ from F1DB")
    team_champions = {row["year"]: row["constructorId"] for row in constructor_titles if row["championshipWon"]}
    deciders = [race for race in races if race["constructorsChampionshipDecider"]]
    if sorted(race["year"] for race in deciders) != sorted(team_champions):
        raise ValueError("Expected one constructors' championship decider per completed championship")
    for race in deciders:
        year, round_ = race["year"], race["round"]
        team = team_champions[year]
        campaigns[year, team]["construtores"] = True
        moment = moments.setdefault((year, round_), {
            "ano": year, "rodada": round_, "gp": grands_prix[race["grandPrixId"]], "pilotos": set(),
        })
        moment["equipes"] = [team]

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
        excluded = CHASSIS_WITHOUT_TITLE_CONTRIBUTION.get((year, constructor), {})
        if not set(excluded).issubset(shortlist):
            raise ValueError(f"Historical chassis review differs from the source entries for {year} {constructor}")
        shortlist.difference_update(excluded)
        if not shortlist:
            raise ValueError(f"No championship chassis candidates remain for {year} {constructor}")
        used_cars.update(shortlist)
        row = {"ano": year, "equipe": constructor, **campaign, "modelos_candidatos": sorted(shortlist)}
        if documented:
            row["modelos_documentados"] = documented
        if excluded:
            row["modelos_sem_contribuicao"] = {
                key: {"nome": cars[key]["fullName"], "motivo": {"pt": pt, "en": en}, "fonte": source}
                for key, (pt, en, source) in excluded.items()
            }
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
        "momentos": [{**moment, "pilotos": sorted(moment["pilotos"])}
                     for _, moment in sorted(moments.items())],
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
