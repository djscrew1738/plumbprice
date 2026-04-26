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
    # Verify the estimate belongs to this org
    est_result = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.organization_id == current_user.organization_id,
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


@router.get("/stats", response_model=dict)
async def outcome_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return win/loss statistics for the current organization.

    Includes:
    - Total recorded, won, lost, pending, no_bid counts
    - Win rate (won / (won + lost))
    - Average quoted price for won vs lost estimates
    - Confidence tier breakdown (do HIGH confidence estimates win more?)
    """
    from sqlalchemy import case, and_

    org_id = current_user.organization_id

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
    return await winrate_by_markup_band(
        db,
        organization_id=current_user.organization_id,
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
    return await winrate_by_task_code(
        db,
        organization_id=current_user.organization_id,
        task_codes=body.task_codes,
        min_n=body.min_n,
    )
