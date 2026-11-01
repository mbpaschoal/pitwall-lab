"""Local tarot artwork catalog, independent of forecasts and team history.

Neutral driver illustrations are reusable across historical teams. Approved
team-specific originals are allowed only for their explicit team and season.
"""
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath

CATALOG_PATH = "dashboard_assets/tarot/catalog.json"
POSE_KEYS = ("helmet_under_arm", "arms_crossed", "helmet_held_front")
APPROVED_OVERRIDES = {
    ("max_verstappen", "red_bull", 0): (
        "verstappen.png", "893f1206e878a4bd30751df4f7d83a0a779a6d6d5445e5dd6e0e77b602d8a3a9"),
    ("hamilton", "ferrari", 1): (
        "hamilton.png", "509138de884b2ce4bb64c1f2ef898fb6661f456467b9f2af64821a32a67e894d"),
    ("russell", "mercedes", 2): (
        "russell.png", "eb5db2342b4be6014f9d1ec58308ffd105baf2a84253e9d42439dfeedf3c7933"),
}
TEAM_LABELS = {
    "alpine": ("Alpine", "Alpine F1 Team"),
    "aston_martin": ("Aston Martin",),
    "audi": ("Audi",),
    "cadillac": ("Cadillac", "Cadillac F1 Team"),
    "ferrari": ("Ferrari",),
    "haas": ("Haas", "Haas F1 Team"),
    "mclaren": ("McLaren",),
    "mercedes": ("Mercedes",),
    "rb": ("RB", "RB F1 Team", "Racing Bulls"),
    "red_bull": ("Red Bull", "Red Bull Racing", "Oracle Red Bull Racing"),
    "sauber": ("Sauber",),
    "williams": ("Williams",),
}
_TEAM_IDS = {label.casefold(): team for team, labels in TEAM_LABELS.items()
             for label in labels}


class TarotCatalogError(ValueError):
    """An invalid or incomplete presentation asset, never a forecast error."""


def team_id(row):
    """Recognize explicit team aliases without guessing from a driver or year."""
    label = " ".join(str(row.get("team") or "").split()).casefold()
    from_label = _TEAM_IDS.get(label)
    explicit = row.get("team_id")
    if explicit and explicit not in TEAM_LABELS:
        return None
    if explicit and from_label and explicit != from_label:
        return None
    return explicit or from_label


def _asset_path(root, relative):
    if not isinstance(relative, str):
        raise TarotCatalogError("Invalid tarot asset path")
    path = PurePosixPath(relative)
    if (path.is_absolute() or ".." in path.parts or "\\" in relative
            or path.parts[:2] != ("dashboard_assets", "tarot")
            or path.suffix != ".png"):
        raise TarotCatalogError("Tarot asset must remain inside dashboard_assets/tarot")
    resolved = (Path(root) / relative).resolve()
    try:
        resolved.relative_to((Path(root) / "dashboard_assets/tarot").resolve())
    except ValueError as error:
        raise TarotCatalogError("Tarot asset escapes its asset directory") from error
    return resolved


def load_catalog(root):
    """Read explicit metadata only; readiness is verified against actual bytes."""
    try:
        catalog = json.loads((Path(root) / CATALOG_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise TarotCatalogError("Tarot catalog unavailable or invalid") from error
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise TarotCatalogError("Unsupported tarot catalog schema")
    if not isinstance(catalog.get("cards"), list) or not isinstance(catalog.get("overrides"), list):
        raise TarotCatalogError("Tarot catalog needs neutral cards and explicit overrides")
    for group, neutral in (("cards", True), ("overrides", False)):
        seen = set()
        for entry in catalog[group]:
            if not isinstance(entry, dict):
                raise TarotCatalogError("Invalid tarot card entry")
            driver = entry.get("driver_id")
            pose = entry.get("pose_id")
            if (not isinstance(driver, str) or not driver
                    or not driver.replace("_", "").isalnum()
                    or isinstance(pose, bool) or not isinstance(pose, int) or pose not in (0, 1, 2)
                    or entry.get("pose_key") != POSE_KEYS[pose]
                    or entry.get("team_neutral") is not neutral):
                raise TarotCatalogError("Invalid tarot driver, pose or team neutrality")
            if neutral:
                key = (driver, pose)
                expected = "dashboard_assets/tarot/variants/{}/pose-{}.png".format(driver, pose)
                if entry.get("path") != expected or entry.get("team_id") is not None:
                    raise TarotCatalogError("Neutral card path or team does not match its driver")
            else:
                team = entry.get("team_id")
                years = entry.get("years")
                if (team not in TEAM_LABELS or not isinstance(years, list) or not years
                        or any(isinstance(y, bool) or not isinstance(y, int) for y in years)):
                    raise TarotCatalogError("Team-specific artwork needs a team and explicit years")
                key = (driver, team, pose)
                approved = APPROVED_OVERRIDES.get(key)
                if (approved is None
                        or entry.get("path") != "dashboard_assets/tarot/" + approved[0]
                        or entry.get("sha256") != approved[1]):
                    raise TarotCatalogError("Team override does not match an approved original")
            if key in seen:
                raise TarotCatalogError("Duplicate tarot driver/pose identity")
            seen.add(key)
            _asset_path(root, entry.get("path"))
            digest = entry.get("sha256")
            if entry.get("status") not in ("planned", "ready"):
                raise TarotCatalogError("Invalid tarot artwork status")
            if entry["status"] == "ready" and (
                    not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                raise TarotCatalogError("Ready artwork needs a SHA-256 digest")
    drivers = {entry["driver_id"] for entry in catalog["cards"]}
    for driver in drivers:
        if {entry["pose_id"] for entry in catalog["cards"]
                if entry["driver_id"] == driver} != {0, 1, 2}:
            raise TarotCatalogError("Each driver needs three explicit planned or ready poses")
    return catalog


def read_artwork(root, entry):
    """Return verified PNG bytes, or None for absent/unverified artwork."""
    if not entry or entry.get("status") != "ready":
        return None
    try:
        content = _asset_path(root, entry["path"]).read_bytes()
    except (OSError, TarotCatalogError):
        return None
    if (not content.startswith(b"\x89PNG\r\n\x1a\n")
            or hashlib.sha256(content).hexdigest() != entry.get("sha256")):
        return None
    return content


def artwork_for(catalog, row, pose_id, year=None):
    """Select only the requested driver and pose, then the matching team override."""
    driver = row.get("driver_id")
    team = team_id(row)
    for entry in catalog["overrides"]:
        if (entry["driver_id"] == driver and entry["pose_id"] == pose_id
                and entry["team_id"] == team
                and (year is None or year in entry["years"])
                and entry["status"] == "ready"):
            return entry
    return next((entry for entry in catalog["cards"]
                 if entry["driver_id"] == driver and entry["pose_id"] == pose_id), None)


def select_cards(rows, root, year=None, round_=None, catalog=None):
    """Keep forecast row order while assigning three distinct deterministic poses.

Artwork availability can prefer another permutation during staged delivery;
once all neutral artworks exist, the GP seed alone selects the permutation.
Ties retain every row and repeat balanced cycles instead of dropping drivers.
"""
    catalog = load_catalog(root) if catalog is None else catalog
    drivers = [row["driver_id"] for row in rows]
    if len(set(drivers)) != len(drivers):
        raise TarotCatalogError("Repeated driver identity in tarot composition")
    by_driver = {row["driver_id"]: row for row in rows}
    # Preserve each displayed trio as a group, including extra tied favorites.
    # Sorting identities within a group gives stable assignments on a trio reorder.
    ordered = [driver for start in range(0, len(drivers), 3)
               for driver in sorted(drivers[start:start + 3])]
    permutations = list(itertools.permutations((0, 1, 2)))
    seed = hashlib.sha256("{}:{}:{}".format(year, round_, ",".join(sorted(drivers))).encode()).digest()
    offset = int.from_bytes(seed[:4], "big") % len(permutations)
    permutations = permutations[offset:] + permutations[:offset]
    # An explicitly approved GP composition keeps its art after the deck expands.
    # Other rounds continue to rotate through the deterministic pose permutations.
    for approved in catalog.get("approved_compositions", []):
        poses=approved.get("driver_poses", {})
        if (approved.get("year")==year and approved.get("round")==round_
                and set(poses)==set(drivers) and len(drivers)==3
                and sorted(poses.values())==[0,1,2]):
            preferred=tuple(poses[driver] for driver in ordered)
            permutations=[preferred]+[item for item in permutations if item!=preferred]
            break
    available = {}
    for driver in ordered:
        for pose in (0, 1, 2):
            entry = artwork_for(catalog, by_driver[driver], pose, year)
            content = read_artwork(root, entry)
            # A corrupt optional override does not hide a valid neutral card.
            if content is None and entry and not entry["team_neutral"]:
                entry = next((card for card in catalog["cards"]
                              if card["driver_id"] == driver and card["pose_id"] == pose), None)
                content = read_artwork(root, entry)
            available[driver, pose] = (entry, content)
    def score(permutation):
        return sum(available[driver, permutation[index % 3]][1] is not None
                   for index, driver in enumerate(ordered))
    permutation = max(permutations, key=score)
    selected = {}
    for index, driver in enumerate(ordered):
        pose = permutation[index % 3]
        entry, content = available[driver, pose]
        selected[driver] = dict(pose_id=pose, entry=entry, content=content)
    return [dict(row=row, **selected[row["driver_id"]]) for row in rows]


def coverage(root, catalog=None):
    """Audit actual neutral-art coverage without claiming planned files exist."""
    catalog = load_catalog(root) if catalog is None else catalog
    ready, missing = [], []
    digests = {}
    duplicates = []
    for entry in catalog["cards"]:
        content = read_artwork(root, entry)
        identity = "{}:{}".format(entry["driver_id"], entry["pose_id"])
        if content is None:
            missing.append(identity)
            continue
        ready.append(identity)
        digest = hashlib.sha256(content).hexdigest()
        if digest in digests:
            duplicates.append([digests[digest], identity])
        digests[digest] = identity
    return dict(required=len(catalog["cards"]), ready=len(ready), missing=missing,
                duplicate_artworks=duplicates,
                complete=bool(catalog["cards"]) and not missing and not duplicates)
