"""
Variance analytics endpoints — /api/v3/analytics/variance

Returns aggregated estimated vs. actual job cost data and exposes
approve/reject actions for pricing recommendations.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.auth import get_current_admin
from app.database import get_db
from app.models.outcomes import EstimateOutcome
from app.models.pricing_intelligence import PricingRecommendation
from app.models.users import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics/variance", tags=["variance"])


# ─── Response schemas ─────────────────────────────────────────────────────────


class VarianceRow(BaseModel):
    task_code: str
    sample_count: int
    avg_estimated: float
    avg_actual: float
    avg_variance_pct: float


class RecommendationOut(BaseModel):
    id: int
    task_code: str
    recommendation_type: str
    suggested_value: float
    current_value: float
    avg_variance_pct: float
    sample_count: int
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class VarianceResponse(BaseModel):
    rows: list[VarianceRow]
    recommendations: list[RecommendationOut]


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=VarianceResponse)
async def get_variance_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> VarianceResponse:
    """Aggregate estimated vs. actual costs by task_code for closed jobs."""
    # Variance rows from closed outcomes with actual_total set
    rows_result = await db.execute(
        select(
            EstimateOutcome.job_type.label("task_code"),
            func.count(EstimateOutcome.id).label("sample_count"),
            func.avg(EstimateOutcome.final_price).label("avg_estimated"),
            func.avg(EstimateOutcome.actual_total).label("avg_actual"),
            func.avg(EstimateOutcome.variance_pct).label("avg_variance_pct"),
        )
        .where(
            EstimateOutcome.actual_total.isnot(None),
            EstimateOutcome.job_type.isnot(None),
        )
        .group_by(EstimateOutcome.job_type)
        .order_by(func.abs(func.avg(EstimateOutcome.variance_pct)).desc())
    )
    variance_rows = [
        VarianceRow(
            task_code=r.task_code,
            sample_count=r.sample_count,
            avg_estimated=float(r.avg_estimated or 0),
            avg_actual=float(r.avg_actual or 0),
            avg_variance_pct=float(r.avg_variance_pct or 0),
        )
        for r in rows_result.all()
    ]

    # Pending and recent recommendations
    recs_result = await db.execute(
        select(PricingRecommendation)
        .where(PricingRecommendation.status == "pending")
        .order_by(PricingRecommendation.created_at.desc())
        .limit(50)
    )
    recs = recs_result.scalars().all()
    rec_out = [
        RecommendationOut(
            id=r.id,
            task_code=r.task_code,
            recommendation_type=r.recommendation_type,
            suggested_value=float(r.suggested_adjustment),
            current_value=0.0,  # current value context is in the pricing engine
            avg_variance_pct=float(r.avg_variance_pct),
            sample_count=r.sample_count,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in recs
    ]

    return VarianceResponse(rows=variance_rows, recommendations=rec_out)


@router.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """Approve a pricing recommendation, marking it for application."""
    result = await db.execute(
        select(PricingRecommendation).where(PricingRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Recommendation is already '{rec.status}'")

    rec.status = "approved"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "pricing_recommendation_approved",
        rec_id=rec_id,
        task_code=rec.task_code,
        admin_id=current_user.id,
    )
    return {"status": "approved"}


@router.post("/recommendations/{rec_id}/reject")
async def reject_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """Reject a pricing recommendation."""
    result = await db.execute(
        select(PricingRecommendation).where(PricingRecommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Recommendation is already '{rec.status}'")

    rec.status = "rejected"
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "pricing_recommendation_rejected",
        rec_id=rec_id,
        task_code=rec.task_code,
        admin_id=current_user.id,
    )
    return {"status": "rejected"}
