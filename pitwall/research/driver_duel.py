"""Historical comparisons on shared starts, with explicit result eligibility."""
from pitwall.research.driver_conditions import select_rows, summarize


def duel(asset, left, right, years=None, condition=None):
    if left == right:
        raise ValueError("Choose two different drivers")
    samples = {driver: {x["race_id"]: x for x in select_rows(asset, years, condition, driver) if x["started"]}
               for driver in (left, right)}
    common = sorted(set(samples[left]) & set(samples[right]),
                    key=lambda key: (asset["gps"][key]["temporada"], asset["gps"][key]["rodada"]))
    evidence = []
    for key in common:
        a, b = samples[left][key], samples[right][key]
        comparable = all(not x["disqualified"] and x["position"] is not None for x in (a, b))
        ahead = (left if a["position"] < b["position"] else right if b["position"] < a["position"] else None) if comparable else None
        evidence.append({"race_id": key, "left": a, "right": b, "comparable": comparable, "ahead": ahead})
    return {"common_starts": len(common), "comparable_results": sum(x["comparable"] for x in evidence),
            "left": summarize([samples[left][key] for key in common]),
            "right": summarize([samples[right][key] for key in common]),
            "left_ahead": sum(x["ahead"] == left for x in evidence),
            "right_ahead": sum(x["ahead"] == right for x in evidence), "evidence": evidence}
