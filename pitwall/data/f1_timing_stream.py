"""Read archived F1 timing updates as data, preserving source line numbers."""

import json
import re


def parse_stream(raw):
    output = []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        match = re.match(r"^(\d{2}:\d{2}:\d{2}\.\d{3})(.+)$", line)
        if not match:
            raise ValueError("Invalid F1 timing-stream line {}".format(number))
        value = json.loads(match.group(2))
        if not isinstance(value, dict):
            raise ValueError("Expected timing-update object")
        output.append({"tempo_relativo": match.group(1), "linha_fonte": number, "dados": value})
    if not output:
        raise ValueError("Empty timing stream")
    return output


def disclosed_compounds(updates):
    """Return explicit per-driver/stint compounds, not inferred tyre colours."""
    found = {}
    for update in updates:
        lines = update["dados"].get("Lines", {})
        for number, driver in lines.items():
            stints = driver.get("Stints", {})
            entries = enumerate(stints) if isinstance(stints, list) else stints.items()
            for index, stint in entries:
                if not isinstance(stint, dict) or "Compound" not in stint:
                    continue
                value = stint["Compound"]
                if value in (None, "", "UNKNOWN"):
                    continue
                key = (str(number), int(index) + 1)
                previous = found.get(key)
                if previous is not None and previous["compound"] != value:
                    raise ValueError("Contradictory disclosed compound for {}".format(key))
                found[key] = {"compound": value, "linha_fonte": update["linha_fonte"],
                              "tempo_relativo": update["tempo_relativo"]}
    return found
