"""A browser-local favourite: no account, analytics or network persistence."""
from pathlib import Path
import streamlit.components.v1 as components
from pitwall.i18n import language


_favorite = components.declare_component("pitwall_favorite", path=str(Path(__file__).resolve().parents[2] / "frontend_assets/favorite"))


def render(names, initial=None):
    selected = _favorite(names=names, initial=initial, lang=language(), default=initial, key="browser_favorite")
    return selected if isinstance(selected, str) and selected in names else None
