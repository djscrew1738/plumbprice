"""Analytics endpoints: revenue, pipeline, rep performance."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_admin, get_current_user
from app.database import get_db
from app.models.users import User
from app.services import analytics_service

router = APIRouter()

Period = Literal["30d", "90d", "365d", "all"]


@router.get("/revenue")
async def revenue(
    period: Period = Query("all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate won revenue with monthly + job-type breakdowns."""
    return await analytics_service.compute_revenue(
        db=db,
        organization_id=current_user.organization_id,
        period=period,
    )


@router.get("/pipeline")
async def pipeline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stage counts, avg residency, and conversion rates."""
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
    return base


@router.get("/rep-performance")
async def rep_performance(
    period: Period = Query("all"),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Per-rep quotes/won/revenue. Admin only."""
    rows = await analytics_service.compute_rep_performance(
        db=db,
        organization_id=current_user.organization_id,
        period=period,
    )
    return {"period": period, "reps": rows}
