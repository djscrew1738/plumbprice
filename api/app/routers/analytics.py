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
    org_id = getattr(current_user, "organization_id", None)
    if org_id is None:
        return {
            "total_won": 0,
            "deal_count": 0,
            "avg_deal_size": 0,
            "by_month": [],
            "by_job_type": [],
        }
    cache_key = f"analytics:revenue:{org_id}:{period}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await analytics_service.compute_revenue(
        db=db,
        organization_id=org_id,
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
    org_id = getattr(current_user, "organization_id", None)
    if org_id is None:
        return {
            "stage_counts": {
                "lead": 0, "qualified": 0, "estimate_sent": 0,
                "negotiation": 0, "won": 0, "lost": 0,
            },
            "avg_time_in_stage_hours": {
                "lead": 0.0, "qualified": 0.0, "estimate_sent": 0.0,
                "negotiation": 0.0,
            },
            "conversion": {
                "lead_to_quoted": 0.0,
                "quoted_to_won": 0.0,
                "overall": 0.0,
            },
            "active_pipeline_value": 0.0,
        }
    cache_key = f"analytics:pipeline:{org_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    base = await analytics_service.compute_pipeline(
        db=db,
        organization_id=org_id,
    )
    base["active_pipeline_value"] = round(
        await analytics_service.compute_active_pipeline_value(
            db=db, organization_id=org_id
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
    org_id = getattr(current_user, "organization_id", None)
    if org_id is None:
        return {"period": period, "reps": []}
    cache_key = f"analytics:rep-performance:{org_id}:{period}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    rows = await analytics_service.compute_rep_performance(
        db=db,
        organization_id=org_id,
        period=period,
    )
    result = {"period": period, "reps": rows}
    await cache_set(cache_key, result, ttl=_ANALYTICS_TTL)
    return result
