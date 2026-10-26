"""Speed-solving methods. Each exposes ``name``, ``variants()`` and ``solve(cube, variant)``."""

from .cfop import CFOP, CROSS_COLORS, parse_cross_colors

METHODS = {"CFOP": CFOP}

__all__ = ["CFOP", "CROSS_COLORS", "METHODS", "parse_cross_colors"]
