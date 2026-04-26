"""
Phase 2.5 — Drawing scale calibration.

Two paths to a `px_per_ft` value on a `BlueprintPage`:

1. **Text-derived** — parse `scale_text` like ``1/4" = 1'-0"`` together with
   the page render DPI to compute pixels-per-foot. This is exact when the
   PDF was rendered at known DPI.

2. **Manual** — the user clicks two endpoints on the page image (typically
   the scale bar) and types in the real-world distance in feet/inches.
   We compute pixel distance and divide.

The takeoff/estimate side reads `px_per_ft` to convert pixel runs (pipe
length detection, ductwork, etc.) into linear feet.
"""

from __future__ import annotations

import math
import re
from typing import Optional


# Default DPI used by `pdf2image` when blueprint_service rasterizes pages.
# If you change the renderer DPI, change this too.
DEFAULT_RENDER_DPI = 200


_SCALE_RE = re.compile(
    r"""
    (?P<paper>\d+(?:[/.]\d+)?|\d+\s+\d+/\d+)      # paper inches: '1/4', '1/8', '3/16', '1.5'
    \s*(?:"|in|″)?\s*=\s*
    (?P<feet>\d+)                                 # whole feet
    \s*(?:'|ft|′)?
    (?:[\s-]+(?P<inches>\d+)\s*(?:"|in|″)?)?      # optional inches, dash- or space-separated
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _parse_fraction(token: str) -> Optional[float]:
    token = token.strip()
    if " " in token:
        whole, frac = token.split(None, 1)
        n, d = frac.split("/")
        return float(whole) + float(n) / float(d)
    if "/" in token:
        n, d = token.split("/")
        return float(n) / float(d)
    try:
        return float(token)
    except ValueError:
        return None


def parse_scale_text(scale_text: str) -> Optional[tuple[float, float]]:
    """
    Parse architectural scale strings.

    Returns (paper_inches, real_feet) or None if unparseable.
    Examples:
        '1/4" = 1\'-0"'   -> (0.25, 1.0)
        "1/8 in = 1 ft"   -> (0.125, 1.0)
        '3/16" = 1\'-6"'  -> (0.1875, 1.5)
    """
    if not scale_text:
        return None
    m = _SCALE_RE.search(scale_text)
    if not m:
        return None
    paper = _parse_fraction(m.group("paper"))
    feet = float(m.group("feet"))
    inches = float(m.group("inches") or 0)
    real_feet = feet + inches / 12.0
    if paper is None or paper <= 0 or real_feet <= 0:
        return None
    return (paper, real_feet)


def px_per_ft_from_text(scale_text: str, dpi: int = DEFAULT_RENDER_DPI) -> Optional[float]:
    """``1/4" = 1'`` at 200 dpi → 0.25 in × 200 px/in / 1 ft = 50 px/ft."""
    parsed = parse_scale_text(scale_text)
    if not parsed:
        return None
    paper_inches, real_feet = parsed
    px = paper_inches * dpi
    return round(px / real_feet, 4)


def px_per_ft_from_points(
    x1: float, y1: float, x2: float, y2: float, real_feet: float,
) -> Optional[float]:
    """Manual two-point calibration. `real_feet` is the real-world distance
    between the two clicked pixels (typically the endpoints of the scale bar
    or any known dimension on the page)."""
    if real_feet <= 0:
        return None
    dx = x2 - x1
    dy = y2 - y1
    pixels = math.hypot(dx, dy)
    if pixels <= 0:
        return None
    return round(pixels / real_feet, 4)
