"""Win/loss outcome tracking for estimates."""

from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate
from app.models.outcomes import EstimateOutcome
from app.models.users import User
from app.services.winrate_service import (
    DEFAULT_BAND_PP,
    winrate_by_markup_band,
    winrate_by_task_code,
)

logger = structlog.get_logger()
router = APIRouter()

OutcomeValue = Literal["won", "lost", "pending", "no_bid"]


class RecordOutcomeRequest(BaseModel):
    outcome: OutcomeValue
    final_price: Optional[float] = None
    notes: Optional[str] = Field(None, max_length=2000)


@router.post("/{estimate_id}/outcome", response_model=dict)
async def record_outcome(
    estimate_id: int,
    body: RecordOutcomeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record whether an estimate was won, lost, or not bid."""
    # Verify the estimate belongs to this org or user
    user_org = getattr(current_user, "organization_id", None)
    if user_org is not None:
        est_result = await db.execute(
            select(Estimate).where(
                Estimate.id == estimate_id,
                Estimate.organization_id == user_org,
            )
        )
    else:
        est_result = await db.execute(
            select(Estimate).where(
                Estimate.id == estimate_id,
                Estimate.created_by == current_user.id,
            )
        )
    estimate = est_result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Upsert: one outcome record per estimate
    existing = await db.execute(
        select(EstimateOutcome).where(EstimateOutcome.estimate_id == estimate_id)
    )
    outcome_row = existing.scalar_one_or_none()

    if outcome_row:
        outcome_row.outcome = body.outcome
        outcome_row.final_price = body.final_price
        outcome_row.notes = body.notes
        outcome_row.recorded_by = current_user.id
    else:
        outcome_row = EstimateOutcome(
            estimate_id=estimate_id,
            outcome=body.outcome,
            final_price=body.final_price,
            notes=body.notes,
            recorded_by=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(outcome_row)

    await db.commit()
    await db.refresh(outcome_row)

    logger.info(
        "outcome.recorded",
        estimate_id=estimate_id,
        outcome=body.outcome,
        user_id=current_user.id,
    )
    return {
        "id": outcome_row.id,
        "estimate_id": estimate_id,
        "outcome": outcome_row.outcome,
        "final_price": outcome_row.final_price,
        "notes": outcome_row.notes,
        "created_at": outcome_row.created_at,
        "updated_at": outcome_row.updated_at,
    }


@router.get("/list", response_model=list)
async def list_outcomes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all recorded outcomes for the org or user, joined with estimate data."""
    user_org = getattr(current_user, "organization_id", None)
    stmt = (
        select(
            EstimateOutcome.id,
            EstimateOutcome.estimate_id,
            EstimateOutcome.outcome,
            EstimateOutcome.final_price,
            EstimateOutcome.notes,
            EstimateOutcome.created_at,
            EstimateOutcome.updated_at,
            Estimate.title.label("estimate_title"),
            Estimate.grand_total.label("estimate_grand_total"),
            Estimate.job_type,
            Estimate.confidence_score,
            Estimate.county,
        )
        .join(Estimate, EstimateOutcome.estimate_id == Estimate.id)
    )
    if user_org is not None:
        stmt = stmt.where(EstimateOutcome.organization_id == user_org)
    else:
        stmt = stmt.where(Estimate.created_by == current_user.id)
    stmt = stmt.order_by(EstimateOutcome.updated_at.desc())
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": r.id,
            "estimate_id": r.estimate_id,
            "outcome": r.outcome,
            "final_price": r.final_price,
            "notes": r.notes,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "estimate_title": r.estimate_title,
            "estimate_grand_total": r.estimate_grand_total,
            "job_type": r.job_type,
            "confidence_score": r.confidence_score,
            "county": r.county,
        }
        for r in rows
    ]


@router.get("/stats", response_model=dict)
async def outcome_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return win/loss statistics for the current organization or user.

    Includes:
    - Total recorded, won, lost, pending, no_bid counts
    - Win rate (won / (won + lost))
    - Average quoted price for won vs lost estimates
    - Confidence tier breakdown (do HIGH confidence estimates win more?)
    """
    from sqlalchemy import case, and_

    org_id = getattr(current_user, "organization_id", None)

    if org_id is None:
        return {
            "total": 0,
            "won": 0,
            "lost": 0,
            "pending": 0,
            "no_bid": 0,
            "win_rate": None,
            "confidence_breakdown": {},
        }

    # Aggregate outcomes
    result = await db.execute(
        select(
            func.count(EstimateOutcome.id).label("total"),
            func.sum(case((EstimateOutcome.outcome == "won",  1), else_=0)).label("won"),
            func.sum(case((EstimateOutcome.outcome == "lost", 1), else_=0)).label("lost"),
            func.sum(case((EstimateOutcome.outcome == "pending", 1), else_=0)).label("pending"),
            func.sum(case((EstimateOutcome.outcome == "no_bid", 1), else_=0)).label("no_bid"),
        ).where(EstimateOutcome.organization_id == org_id)
    )
    row = result.one()
    total, won, lost, pending, no_bid = row.total, row.won or 0, row.lost or 0, row.pending or 0, row.no_bid or 0
    decided = won + lost
    win_rate = round(won / decided, 4) if decided > 0 else None

    # Win rate by confidence label
    conf_result = await db.execute(
        select(
            Estimate.confidence_label,
            func.count(EstimateOutcome.id).label("count"),
            func.sum(case((EstimateOutcome.outcome == "won", 1), else_=0)).label("won"),
        )
        .join(Estimate, EstimateOutcome.estimate_id == Estimate.id)
        .where(
            EstimateOutcome.organization_id == org_id,
            EstimateOutcome.outcome.in_(["won", "lost"]),
        )
        .group_by(Estimate.confidence_label)
    )
    confidence_breakdown = {}
    for cr in conf_result.all():
        label = cr.confidence_label or "UNKNOWN"
        confidence_breakdown[label] = {
            "count": cr.count,
            "won": cr.won or 0,
            "win_rate": round((cr.won or 0) / cr.count, 4) if cr.count > 0 else None,
        }

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "no_bid": no_bid,
        "win_rate": win_rate,
        "confidence_breakdown": confidence_breakdown,
    }


@router.get("/winrate/markup", response_model=dict)
async def winrate_markup(
    markup_pct: float,
    band_pp: float = DEFAULT_BAND_PP,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Win-rate around a target markup-% band (e.g. ?markup_pct=0.28&band_pp=5)."""
    if markup_pct < 0 or markup_pct > 5:
        raise HTTPException(status_code=400, detail="markup_pct must be a fraction between 0 and 5")
    if band_pp <= 0 or band_pp > 50:
        raise HTTPException(status_code=400, detail="band_pp must be in (0, 50]")
    user_org = getattr(current_user, "organization_id", None)
    return await winrate_by_markup_band(
        db,
        organization_id=user_org,
        target_markup_pct=markup_pct,
        band_pp=band_pp,
    )


class WinRateByTaskRequest(BaseModel):
    task_codes: Optional[list[str]] = None
    min_n: int = Field(default=3, ge=1, le=100)


@router.post("/winrate/by-task", response_model=list)
async def winrate_by_task(
    body: WinRateByTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-task-code win-rate. Pass `task_codes` to scope to the current estimate."""
    user_org = getattr(current_user, "organization_id", None)
    return await winrate_by_task_code(
        db,
        organization_id=user_org,
        task_codes=body.task_codes,
        min_n=body.min_n,
    )


# ── v4.1: Actual cost capture (E2.1) ─────────────────────────────────────────

class CloseJobRequest(BaseModel):
    actual_materials_cost: Optional[float] = None
    actual_labor_hours: Optional[float] = None
    actual_labor_cost: Optional[float] = None
    actual_total: float
    notes: Optional[str] = Field(None, max_length=2000)


@router.patch("/{estimate_id}/close", response_model=dict)
async def close_job_with_actuals(
    estimate_id: int,
    body: CloseJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record actual costs for a completed job and compute variance.

    Sets outcome to 'won' and stores actual cost figures for variance analysis.
    """
    from datetime import datetime, timezone

    user_org = getattr(current_user, "organization_id", None)
    if user_org is not None:
        estimate = (
            await db.execute(
                select(Estimate).where(
                    Estimate.id == estimate_id,
                    Estimate.organization_id == user_org,
                )
            )
        ).scalar_one_or_none()
    else:
        estimate = (
            await db.execute(
                select(Estimate).where(
                    Estimate.id == estimate_id,
                    Estimate.created_by == current_user.id,
                )
            )
        ).scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Upsert outcome record
    outcome_row = (
        await db.execute(
            select(EstimateOutcome).where(EstimateOutcome.estimate_id == estimate_id)
        )
    ).scalar_one_or_none()

    if not outcome_row:
        outcome_row = EstimateOutcome(
            estimate_id=estimate_id,
            outcome="won",
            organization_id=user_org,
            recorded_by=current_user.id,
        )
        db.add(outcome_row)

    outcome_row.outcome = "won"
    outcome_row.actual_materials_cost = body.actual_materials_cost
    outcome_row.actual_labor_hours = body.actual_labor_hours
    outcome_row.actual_labor_cost = body.actual_labor_cost
    outcome_row.actual_total = body.actual_total
    outcome_row.closed_by_user_id = current_user.id
    outcome_row.closed_at = datetime.now(timezone.utc)
    if body.notes:
        outcome_row.notes = body.notes

    # Compute variance percentage
    estimated_total = estimate.grand_total or 0.0
    if estimated_total > 0:
        outcome_row.variance_pct = round(
            ((body.actual_total - estimated_total) / estimated_total) * 100, 2
        )

    await db.commit()

    logger.info(
        "job_closed.actuals_recorded",
        estimate_id=estimate_id,
        actual_total=body.actual_total,
        variance_pct=outcome_row.variance_pct,
        user_id=current_user.id,
    )
    return {
        "status": "closed",
        "estimate_id": estimate_id,
        "actual_total": body.actual_total,
        "estimated_total": estimated_total,
        "variance_pct": outcome_row.variance_pct,
    }
