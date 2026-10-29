"""Product version; independent of scientific model and snapshot identifiers."""

from pathlib import Path
import re
from pitwall.paths import PROJECT_ROOT


def version(root=PROJECT_ROOT):
    text = (Path(root) / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", text):
        raise ValueError("VERSION must contain exactly MAJOR.MINOR.PATCH")
    return text
