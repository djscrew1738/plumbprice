"""Job-cost actuals + variance reconciliation router (Track C5).

Endpoints:
* GET    /api/v1/estimates/{id}/actuals          — fetch (or null)
* PUT    /api/v1/estimates/{id}/actuals          — upsert actuals for an estimate
* GET    /api/v1/estimates/{id}/variance         — single-estimate variance report
* GET    /api/v1/estimates/variance/by-task      — org-wide rollup by task code
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate
from app.models.job_costs import EstimateActuals
from app.models.users import User
from app.services.jobcost_service import (
    estimate_variance,
    variance_by_task_code,
)


logger = structlog.get_logger()
router = APIRouter()


class ActualsBody(BaseModel):
    actual_labor_hours: Optional[float] = Field(default=None, ge=0)
    actual_labor_cost: Optional[float] = Field(default=None, ge=0)
    actual_materials_cost: Optional[float] = Field(default=None, ge=0)
    actual_subcontractor_cost: Optional[float] = Field(default=None, ge=0)
    actual_other_cost: Optional[float] = Field(default=None, ge=0)
    actual_revenue: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=4000)
    closed_at: Optional[datetime] = None


async def _get_estimate(
    db: AsyncSession, estimate_id: int, user: User
) -> Estimate:
    res = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
        )
    )
    est = res.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return est


@router.get("/{estimate_id}/actuals")
async def get_actuals(
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_estimate(db, estimate_id, current_user)
    res = await db.execute(
        select(EstimateActuals).where(EstimateActuals.estimate_id == estimate_id)
    )
    row = res.scalar_one_or_none()
    if not row:
        return None
    return {
        "estimate_id": row.estimate_id,
        "actual_labor_hours": row.actual_labor_hours,
        "actual_labor_cost": row.actual_labor_cost,
        "actual_materials_cost": row.actual_materials_cost,
        "actual_subcontractor_cost": row.actual_subcontractor_cost,
        "actual_other_cost": row.actual_other_cost,
        "actual_revenue": row.actual_revenue,
        "notes": row.notes,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.put("/{estimate_id}/actuals")
async def upsert_actuals(
    estimate_id: int,
    body: ActualsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_estimate(db, estimate_id, current_user)
    res = await db.execute(
        select(EstimateActuals).where(EstimateActuals.estimate_id == estimate_id)
    )
    row = res.scalar_one_or_none()
    if not row:
        row = EstimateActuals(
            estimate_id=estimate_id,
            organization_id=current_user.organization_id,
            recorded_by=current_user.id,
        )
        db.add(row)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.recorded_by = current_user.id
    await db.commit()
    await db.refresh(row)
    logger.info(
        "jobcost.actuals.upsert",
        estimate_id=estimate_id,
        user_id=current_user.id,
    )
    return {"estimate_id": estimate_id, "id": row.id, "closed_at": row.closed_at}


@router.get("/{estimate_id}/variance")
async def get_variance(
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    est = await _get_estimate(db, estimate_id, current_user)
    res = await db.execute(
        select(EstimateActuals).where(EstimateActuals.estimate_id == estimate_id)
    )
    actuals = res.scalar_one_or_none()
    return estimate_variance(est, actuals)


@router.get("/variance/by-task", response_model=list)
async def variance_by_task(
    min_n: int = 3,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if min_n < 1 or min_n > 100:
        raise HTTPException(status_code=400, detail="min_n must be in [1, 100]")
    return await variance_by_task_code(
        db,
        organization_id=current_user.organization_id,
        min_n=min_n,
    )
