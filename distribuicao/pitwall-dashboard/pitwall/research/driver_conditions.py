"""Descriptive condition cohorts, opportunity denominators and teammate results.

These are historical associations, not driver-skill estimates or predictions.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import isclose, sqrt


@dataclass(frozen=True)
class Condition:
    key: str
    label: str
    short: str
    variable: str
    field: str
    equals: object = None
    lower: object = None
    upper: object = None

    def includes(self, gp):
        value = gp.get(self.field)
        if value is None:
            return False
        if self.equals is not None:
            return value == self.equals
        return (self.lower is None or value >= self.lower) and (self.upper is None or value < self.upper)


CONDITIONS = (
    Condition("rain", "Com chuva registrada", "Chuva", "Chuva", "rain_condition", equals="recorded"),
    Condition("no_rain", "Sem chuva registrada", "Sem chuva", "Chuva", "rain_condition", equals="not_recorded"),
    Condition("track_hot", "Pista quente · 40°C ou mais", "Pista quente", "Temperatura da pista", "track_temperature", lower=40),
    Condition("track_mild", "Pista entre 25°C e 40°C", "Pista moderada", "Temperatura da pista", "track_temperature", lower=25, upper=40),
    Condition("track_cold", "Pista fria · abaixo de 25°C", "Pista fria", "Temperatura da pista", "track_temperature", upper=25),
    Condition("air_hot", "Ar a 28°C ou mais", "Ar quente", "Temperatura do ar", "air_temperature", lower=28),
    Condition("air_mild", "Ar entre 20°C e 28°C", "Ar moderado", "Temperatura do ar", "air_temperature", lower=20, upper=28),
    Condition("air_cold", "Ar abaixo de 20°C", "Ar frio", "Temperatura do ar", "air_temperature", upper=20),
    Condition("ccw", "Anti-horário", "Anti-horário", "Sentido do circuito", "direction", equals="anti_horario"),
    Condition("cw", "Horário", "Horário", "Sentido do circuito", "direction", equals="horario"),
    Condition("figure_eight", "Traçado em oito", "Em oito", "Sentido do circuito", "direction", equals="misto_oito"),
    Condition("few_corners", "Até 15 curvas", "Até 15 curvas", "Quantidade de curvas", "corners", upper=16),
    Condition("medium_corners", "De 16 a 19 curvas", "16 a 19 curvas", "Quantidade de curvas", "corners", lower=16, upper=20),
    Condition("many_corners", "Muitas curvas · 20 ou mais", "Muitas curvas", "Quantidade de curvas", "corners", lower=20),
    Condition("high_altitude", "Altitude de 500 m ou mais", "Maior altitude", "Altitude", "altitude_m", lower=500),
    Condition("low_altitude", "Altitude abaixo de 500 m", "Menor altitude", "Altitude", "altitude_m", upper=500),
)
BY_KEY = {item.key: item for item in CONDITIONS}
HIGHLIGHTS = ("rain", "track_hot", "ccw", "many_corners", "high_altitude", "track_cold")
METRICS = {"win_rate": "Taxa de vitórias", "wins": "Vitórias", "podium_rate": "Taxa de pódios", "podiums": "Pódios"}


def wilson(successes, n):
    if not n:
        return None
    z = 1.959963984540054
    fraction = successes / n
    denominator = 1 + z * z / n
    center = (fraction + z * z / (2 * n)) / denominator
    margin = z * sqrt(fraction * (1 - fraction) / n + z * z / (4 * n * n)) / denominator
    return max(0, center - margin), min(1, center + margin)


def summarize(rows):
    starters = [x for x in rows if x["started"]]
    classified = [x for x in starters if not x["disqualified"] and x["position"] is not None]
    wins = sum(x["position"] == 1 for x in classified)
    podiums = sum(x["position"] <= 3 for x in classified)
    n = len(starters)
    return {"starts": n, "wins": wins, "podiums": podiums,
            "win_rate": wins / n if n else None, "podium_rate": podiums / n if n else None,
            "win_interval": wilson(wins, n), "podium_interval": wilson(podiums, n),
            "classified_n": len(classified),
            "mean_position": sum(x["position"] for x in classified) / len(classified) if classified else None,
            "dns": sum(not x["started"] for x in rows), "retirements": sum(x["retired"] for x in starters),
            "disqualifications": sum(x["disqualified"] for x in starters)}


def select_rows(asset, years=None, condition=None, driver=None):
    years = set(years) if years is not None else {2024, 2025, 2026}
    cohort = BY_KEY[condition] if condition else None
    return [row for row in asset["resultados"]
            if asset["gps"][row["race_id"]]["temporada"] in years
            and (driver is None or row["driver_id"] == driver)
            and (cohort is None or cohort.includes(asset["gps"][row["race_id"]]))]


def driver_names(asset, years=None):
    return {x["driver_id"]: x["driver_name"] for x in select_rows(asset, years)}


def ranking(asset, condition, metric="win_rate", minimum_starts=5, years=None):
    if metric not in METRICS or minimum_starts < 1:
        raise ValueError("Unknown metric or invalid minimum sample")
    rows = select_rows(asset, years, condition)
    by_driver = defaultdict(list)
    for row in rows:
        by_driver[row["driver_id"]].append(row)
    output = []
    for driver, sample in by_driver.items():
        stats = summarize(sample)
        if stats["starts"] >= minimum_starts:
            output.append({"driver_id": driver, "driver_name": sample[-1]["driver_name"], **stats,
                           "score": stats[metric]})
    output.sort(key=lambda x: (-x["score"], -x["starts"], x["driver_name"]))
    previous, position = None, 0
    for row in output:
        if previous is None or not isclose(row["score"], previous, rel_tol=0, abs_tol=1e-12):
            position += 1
        row["rank"] = position
        previous = row["score"]
    return output


def leaders(ranked):
    # Zero observed wins/podiums are evidence, not an award for alphabetical order.
    if not ranked or ranked[0]["score"] <= 0:
        return []
    return [x for x in ranked if x["rank"] == 1]


def teammate_comparison(asset, driver, years=None, condition=None):
    all_rows = select_rows(asset, years, condition)
    groups = defaultdict(list)
    for row in all_rows:
        groups[(row["race_id"], row["team_id"])].append(row)
    evidence = []
    for group in groups.values():
        if len(group) != 2 or not any(x["driver_id"] == driver for x in group):
            continue
        own = next(x for x in group if x["driver_id"] == driver)
        mate = next(x for x in group if x["driver_id"] != driver)
        if any(not x["started"] or x["disqualified"] or x["position"] is None for x in (own, mate)):
            continue
        evidence.append({"race_id": own["race_id"], "teammate_id": mate["driver_id"],
            "teammate_name": mate["driver_name"], "own_position": own["position"], "teammate_position": mate["position"],
            "outcome": "ahead" if own["position"] < mate["position"] else ("behind" if own["position"] > mate["position"] else "tie")})
    ahead = sum(x["outcome"] == "ahead" for x in evidence)
    return {"comparable": len(evidence), "ahead": ahead,
            "behind": sum(x["outcome"] == "behind" for x in evidence),
            "ties": sum(x["outcome"] == "tie" for x in evidence),
            "ahead_rate": ahead / len(evidence) if evidence else None, "evidence": evidence}


def profile(asset, driver, years=None, conditions=HIGHLIGHTS):
    selected = select_rows(asset, years, driver=driver)
    opportunities = {x["race_id"] for x in selected if x["started"]}
    return {"driver_id": driver, "driver_name": selected[-1]["driver_name"] if selected else driver,
        "summary": summarize(selected), "conditions": [
            {"condition": key, "driver": summarize(select_rows(asset, years, key, driver)),
             "reference": summarize([x for x in select_rows(asset, years, key) if x["driver_id"] != driver and x["race_id"] in opportunities])}
            for key in conditions], "teammates": teammate_comparison(asset, driver, years), "races": selected}
