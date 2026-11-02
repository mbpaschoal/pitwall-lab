"""Bounded, offline search across events, circuits, drivers and teams."""
import json
from pathlib import Path
import unicodedata
from urllib.parse import urlencode
from pitwall.data.driver_conditions import load, DriverConditionsError


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold()) if not unicodedata.combining(c))


def search(root, query, lang="pt", year=None, round_=None):
    query = normalized(query.strip())
    if len(query) < 2:
        return []
    results = []
    context = (dict(temporada=year, gp=round_) if year in (2024, 2025, 2026)
               and type(round_) is int and 1 <= round_ <= 24 else {})
    try:
        events = json.loads((Path(root) / "frontend_assets/contexto_editorial.json").read_text(encoding="utf-8"))["eventos"]
    except (OSError, ValueError, KeyError):
        events = []
    for event in events:
        if query in normalized(" ".join(map(str, event.values()))):
            event_year, event_round = event["temporada"], event["rodada"]
            results.append({"kind": "gp", "label": "{} · {} · {}".format(event_year, event["cidade"], event["corrida"]),
                "value": "{}:{}".format(event_year, event_round),
                "href": "?" + urlencode(dict(tela="Corridas", temporada=event_year, gp=event_round, lang=lang))})
    try:
        asset = load(root)
    except DriverConditionsError:
        return results
    names = {x["driver_id"]: x["driver_name"] for x in asset["resultados"]}
    # A newly observed driver may have a canonical identity but no historical
    # conditions profile yet. The profile route shows that absence explicitly.
    try:
        from pitwall.data.race_weekend import carregar_asset
        identities = carregar_asset(root).get("identidades", {})
        for key, identity in identities.items():
            if identity.get("piloto"):
                names.setdefault(key.rsplit(":", 1)[-1], identity["piloto"])
    except (OSError, ValueError, KeyError):
        pass
    for pid, name in sorted(names.items(), key=lambda x: x[1]):
        if query in normalized(name):
            results.append({"kind": "driver", "label": name,
                "href": "?" + urlencode(dict(tela="Pilotos", piloto=pid, visao="perfil", lang=lang, **context))})
    teams = sorted({x["team_id"] for x in asset["resultados"]})
    last = max(asset["gps"].values(), key=lambda g: (g["temporada"], g["rodada"]))
    for team in teams:
        if query in normalized(team.replace("_", " ")):
            label = {"mclaren": "McLaren", "rb": "RB"}.get(team, team.replace("_", " ").title())
            team_events = [asset["gps"][x["race_id"]] for x in asset["resultados"] if x["team_id"] == team]
            target = context or dict(temporada=last["temporada"], gp=last["rodada"])
            if context and not any(event["temporada"] == context["temporada"] for event in team_events):
                available = max(team_events, key=lambda event: (event["temporada"], event["rodada"]))
                target = dict(temporada=available["temporada"], gp=available["rodada"])
                label += " · {}".format(available["temporada"])
            results.append({"kind": "team", "label": label,
                "href": "?" + urlencode(dict(tela="Campeonato", lang=lang, **target)) + "#equipes-completo"})
    return results
