"""Documented real photographs for each fan-journey destination.

Only local metadata is read. Importing this module never fetches assets or data.
"""
import json
import math
from pathlib import Path
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


# Portrait metadata uses `file`, including non-PNG original photographs.
_PORTRAITS = {(item.get('driver_id') or Path(item['file']).stem): item for item in json.loads(
    (PROJECT_ROOT/'dashboard_assets/fan/sources.json').read_text(encoding='utf-8'))
    if item.get('file','').startswith('portraits/')}


def portrait_asset(driver, name=None):
    item = _PORTRAITS.get(driver)
    if not item:
        return None
    override = PORTRAIT_OVERRIDES.get(driver,{})
    label=name or item.get('name') or driver.replace('_',' ').title()
    return dict(path='dashboard_assets/fan/'+item['file'], driver_id=driver,
        name=label, portrait=True,
        credit=label+' · '+(item.get('author') or item.get('source') or 'Formula 1'),
        source=item.get('source_page') or 'https://www.formula1.com/en/drivers',
        position=item.get('object_position') or override.get('position','center top'))


def profile_crop_geometry(spec):
    """Validate an optional source-pixel crop and describe its CSS viewport."""
    if 'focal_crop' not in spec:
        return None
    crop = spec['focal_crop']
    sides = ('top', 'right', 'bottom', 'left')
    if not isinstance(crop, dict) or set(crop) != set(sides):
        raise ValueError('A profile crop requires four numeric insets.')
    values = {}
    for side in sides:
        value = crop[side]
        if type(value) not in (int, float):
            raise ValueError('Profile crop insets must be numbers.')
        try:
            value = float(value)
        except (OverflowError, ValueError):
            raise ValueError('Profile crop insets must be finite.') from None
        if not math.isfinite(value) or not 0 <= value < 100:
            raise ValueError('Profile crop insets must be finite percentages.')
        values[side] = value / 100
    remaining_width = 1 - values['left'] - values['right']
    remaining_height = 1 - values['top'] - values['bottom']
    if remaining_width <= 0 or remaining_height <= 0:
        raise ValueError('Profile crop insets must leave a visible image.')
    width, height = spec['width'], spec['height']
    if type(width) is not int or type(height) is not int or min(width, height) <= 0:
        raise ValueError('Profile crop requires oriented pixel dimensions.')
    try:
        native_width, native_height = width * remaining_width, height * remaining_height
    except OverflowError:
        raise ValueError('Profile crop dimensions must be finite.') from None
    if not math.isfinite(native_width) or not math.isfinite(native_height):
        raise ValueError('Profile crop dimensions must be finite.')
    if min(native_width, native_height) < 1600:
        raise ValueError('Profile crop must retain at least 1600 pixels on each axis.')
    return dict(
        aspect_ratio=native_width / native_height,
        width_percent=100 / remaining_width,
        left_percent=-100 * values['left'] / remaining_width,
        top_percent=-100 * values['top'] / remaining_height,
        native_width=native_width, native_height=native_height,
    )


def profile_asset(driver):
    """A separate editorial photograph for this profile; never a podium image."""
    import hashlib
    import re
    if not isinstance(driver, str) or not re.fullmatch(r'[a-z0-9_]+', driver):
        return None
    try:
        catalogue = PROJECT_ROOT / 'frontend_assets/profile_photos.json'
        if catalogue.is_symlink():
            return None
        data = json.loads(catalogue.read_text(encoding='utf-8'))
        spec = data['photos'][driver]
        digest = spec['sha256']
        expected = 'static/pitwall-profiles/{}-{}.jpg'.format(driver, digest[:12])
        if spec['driver_id'] != driver or not re.fullmatch(r'[a-f0-9]{64}', digest) or spec['path'] != expected:
            return None
        path = PROJECT_ROOT / expected
        if path.is_symlink() or path.parent.is_symlink() or (PROJECT_ROOT/'static').is_symlink():
            return None
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return None
        profile_crop_geometry(spec)
        return dict(spec, src='app/'+expected)
    except (OSError, ValueError, KeyError, TypeError):
        return None
