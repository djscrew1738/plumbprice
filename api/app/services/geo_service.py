"""GPS-based county auto-detection service (E6.6).

Uses static bounding boxes for DFW counties — no external API dependency.
Returns the county name for a given (lat, lng) coordinate.

Coverage: Tarrant, Dallas, Collin, Denton, Rockwall, Ellis, Johnson, Parker counties.
Points outside the DFW bounding box return None (fall back to user-selected county).
"""
from __future__ import annotations

from typing import Optional

# County bounding boxes: (min_lat, max_lat, min_lng, max_lng)
# All coordinates in decimal degrees. Source: Texas county boundary data.
_COUNTY_BOXES: list[tuple[str, float, float, float, float]] = [
    # name, min_lat, max_lat, min_lng, max_lng
    ("Tarrant",  32.5484, 32.9807, -97.6408, -97.0294),
    ("Dallas",   32.5461, 33.0177, -97.0394, -96.5313),
    ("Collin",   33.0009, 33.6543, -96.9836, -96.3053),
    ("Denton",   32.9946, 33.6540, -97.6503, -96.8447),
    ("Rockwall", 32.7868, 33.1003, -96.4849, -96.2313),
    ("Ellis",    32.0890, 32.5566, -97.0504, -96.4707),
    ("Johnson",  32.1725, 32.6411, -97.7206, -97.0294),
    ("Parker",   32.5457, 33.0008, -98.2000, -97.5794),
    ("Kaufman",  32.5484, 32.9996, -96.5329, -96.0516),
    ("Hunt",     32.9927, 33.3848, -96.5952, -95.8622),
]

# Overall DFW bounding box — anything outside this is definitely not DFW
_DFW_MIN_LAT = 32.0
_DFW_MAX_LAT = 34.0
_DFW_MIN_LNG = -98.5
_DFW_MAX_LNG = -95.8


def county_from_coordinates(lat: float, lng: float) -> Optional[str]:
    """Return the DFW county name for the given coordinates, or None if outside DFW."""
    if not (_DFW_MIN_LAT <= lat <= _DFW_MAX_LAT and _DFW_MIN_LNG <= lng <= _DFW_MAX_LNG):
        return None

    for name, min_lat, max_lat, min_lng, max_lng in _COUNTY_BOXES:
        if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
            return name

    return None  # Inside DFW bounds but not in any known county box — return None
