"""v4.1 Geo API — GPS-based county detection (E6.6).

GET /api/v3/geo/county?lat={lat}&lng={lng}
"""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.geo_service import county_from_coordinates

router = APIRouter(prefix="/geo", tags=["geo"])


class CountyResponse(BaseModel):
    county: Optional[str]
    lat: float
    lng: float
    in_dfw: bool


@router.get("/county", response_model=CountyResponse)
async def detect_county(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Return the DFW county name for the given GPS coordinates.

    Returns `county: null` if the coordinates are outside the DFW service area.
    """
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=422, detail="Invalid coordinates")

    county = county_from_coordinates(lat, lng)
    return CountyResponse(
        county=county,
        lat=lat,
        lng=lng,
        in_dfw=county is not None,
    )
