"""Analytics endpoints: revenue, pipeline, rep performance."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin, get_current_user
from app.core.cache import cache_get, cache_set
from app.database import get_db
from app.models.users import User
from app.services import analytics_service

router = APIRouter()

Period = Literal["30d", "90d", "365d", "all"]

_ANALYTICS_TTL = 300  # 5 minutes


@router.get("/revenue", response_model=dict)
async def revenue(
    period: Period = Query("all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate won revenue with monthly + job-type breakdowns."""
    cache_key = f"analytics:revenue:{current_user.organization_id}:{period}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await analytics_service.compute_revenue(
        db=db,
        organization_id=current_user.organization_id,
        period=period,
    )
    await cache_set(cache_key, result, ttl=_ANALYTICS_TTL)
    return result


@router.get("/pipeline", response_model=dict)
async def pipeline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stage counts, avg residency, and conversion rates."""
    cache_key = f"analytics:pipeline:{current_user.organization_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    base = await analytics_service.compute_pipeline(
        db=db,
        organization_id=current_user.organization_id,
    )
    base["active_pipeline_value"] = round(
        await analytics_service.compute_active_pipeline_value(
            db=db, organization_id=current_user.organization_id
        ),
        2,
    )
    await cache_set(cache_key, base, ttl=_ANALYTICS_TTL)
    return base


@router.get("/rep-performance", response_model=dict)
async def rep_performance(
    period: Period = Query("all"),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Per-rep quotes/won/revenue. Admin only."""
    cache_key = f"analytics:rep-performance:{current_user.organization_id}:{period}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    rows = await analytics_service.compute_rep_performance(
        db=db,
        organization_id=current_user.organization_id,
        period=period,
    )
    result = {"period": period, "reps": rows}
    await cache_set(cache_key, result, ttl=_ANALYTICS_TTL)
    return result
