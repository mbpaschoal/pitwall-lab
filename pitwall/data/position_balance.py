"""Audited grid-to-finish observations for the descriptive driver profile."""

import json
from pathlib import Path

from pitwall.data.driver_conditions import DriverConditionsError, content_hash


ASSET = "frontend_assets/pilot_position_balance.json"
SCHEMA = "pitwall-position-balance-v1"


def load(root, archive):
    """Check this snapshot against the identities and finishes in the profile archive."""
    try:
        payload = json.loads((Path(root) / ASSET).read_text(encoding="utf-8"))
        checksum = payload.pop("conteudo_sha256")
        if payload["schema"] != SCHEMA or checksum != content_hash(payload):
            raise ValueError("Snapshot schema or checksum")
        through = payload["through"]
        if through not in archive["gps"] or not payload["rows"]:
            raise ValueError("Snapshot coverage")
        coverage = archive["gps"][through]
        last = coverage["temporada"], coverage["rodada"]
        reference = {(r["race_id"], r["driver_id"]): r for r in archive["resultados"]}
        corrections = payload["grid_corrections"]
        seen = set()
        for gp, driver, grid, finish in payload["rows"]:
            key = gp, driver
            r = reference[key]
            event = archive["gps"][gp]
            correction = corrections.get(f"{gp}:{driver}")
            expected_grid = correction["grid"] if correction else r["grid"]
            if (key in seen or (event["temporada"], event["rodada"]) > last
                    or type(grid) is not int or not 1 <= grid <= 22
                    or type(finish) is not int or not 1 <= finish <= 22
                    or grid != expected_grid or finish != r["position"]
                    or not r["started"] or r["retired"] or r["disqualified"]
                    or r["canonical_status"] not in {"Finished", "Lapped"}):
                raise ValueError("Incompatible grid or finish")
            seen.add(key)
        return payload
    except (OSError, AttributeError, ValueError, TypeError, KeyError) as error:
        raise DriverConditionsError("Histórico de saldo temporariamente indisponível.") from error


def observations(snapshot, archive, driver, years, starting_position=None):
    years = set(years)
    selected = []
    for gp, pid, grid, finish in snapshot["rows"]:
        if pid != driver or (starting_position is not None and grid != starting_position):
            continue
        event = archive["gps"][gp]
        if event["temporada"] in years:
            selected.append((event, grid, finish, grid - finish))
    return sorted(selected, key=lambda row: (row[0]["temporada"], row[0]["rodada"]), reverse=True)
