"""Documented real photographs for each fan-journey destination.

Only local metadata is read. Importing this module never fetches assets or data.
"""
import json
from pitwall.paths import PROJECT_ROOT

CATALOG_PATH = PROJECT_ROOT / 'dashboard_assets/fan/hero_catalog.json'
_CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
HERO_IMAGES = {name: dict(spec) for name, spec in _CATALOG['heroes'].items()}
for _alias, _canonical in _CATALOG['aliases'].items():
    HERO_IMAGES[_alias] = HERO_IMAGES[_canonical]
PORTRAIT_OVERRIDES = _CATALOG['portrait_overrides']
RESOLUTION_POLICY = _CATALOG['policy']


def hero_asset(name):
    """Return a detached spec; unknown identities/presets fail explicitly."""
    return dict(HERO_IMAGES[name])
