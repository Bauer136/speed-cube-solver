"""User settings remembered between launches (``~/.config/speedsolver/settings.json``)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .methods.cfop import CROSS_COLORS


def _path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "speedsolver" / "settings.json"


def load_cross_colors() -> tuple[str, ...]:
    """Saved cross colors, or all six if nothing valid is saved."""
    try:
        saved = json.loads(_path().read_text())["cross_colors"]
    except (OSError, ValueError, KeyError, TypeError):
        return CROSS_COLORS
    colors = tuple(c for c in CROSS_COLORS if isinstance(saved, list) and c in saved)
    return colors or CROSS_COLORS


def save_cross_colors(colors: tuple[str, ...]) -> None:
    path = _path()
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data["cross_colors"] = list(colors)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(path)
    except OSError:
        pass  # remembering the choice is a convenience; the setting still applies now
