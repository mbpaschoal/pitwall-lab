"""Bounded, offline search across events, circuits, drivers and teams."""
import json
from pathlib import Path
import unicodedata
from urllib.parse import urlencode
from pitwall.data.driver_conditions import load, DriverConditionsError


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold()) if not unicodedata.combining(c))


def search(root, query, lang="pt"):
    query = normalized(query.strip())
    if len(query) < 2:
        return []
    results = []
    try:
        events = json.loads((Path(root) / "frontend_assets/contexto_editorial.json").read_text(encoding="utf-8"))["eventos"]
    except (OSError, ValueError, KeyError):
        events = []
    for event in events:
        if query in normalized(" ".join(map(str, event.values()))):
            year, round_ = event["temporada"], event["rodada"]
            results.append({"kind": "gp", "label": "{} · {} · {}".format(year, event["cidade"], event["corrida"]),
                "value": "{}:{}".format(year, round_),
                "href": "?" + urlencode(dict(tela="Corridas", temporada=year, gp=round_, lang=lang))})
    try:
        asset = load(root)
    except DriverConditionsError:
        return results
    names = {x["driver_id"]: x["driver_name"] for x in asset["resultados"]}
    for pid, name in sorted(names.items(), key=lambda x: x[1]):
        if query in normalized(name):
            results.append({"kind": "driver", "label": name,
                "href": "?" + urlencode(dict(tela="Pilotos", piloto=pid, visao="perfil", lang=lang))})
    teams = sorted({x["team_id"] for x in asset["resultados"]})
    last = max(asset["gps"].values(), key=lambda g: (g["temporada"], g["rodada"]))
    for team in teams:
        if query in normalized(team.replace("_", " ")):
            results.append({"kind": "team", "label": {"mclaren": "McLaren", "rb": "RB"}.get(team, team.replace("_", " ").title()),
                "href": "?" + urlencode(dict(tela="Campeonato", temporada=last["temporada"], gp=last["rodada"], lang=lang)) + "#equipes-completo"})
    return results
