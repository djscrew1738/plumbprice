"""
Estimates API v3 — Extended estimate endpoints with v3 fields.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.estimates import Estimate
from app.schemas.v3.estimates import EstimateResponseV3

router = APIRouter()


@router.get("/{estimate_id}", response_model=EstimateResponseV3)
async def get_estimate_v3(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single estimate with v3 fields (agent trace, market adjustments, blueprint data)."""
    stmt = select(Estimate).where(Estimate.id == estimate_id)
    result = await db.execute(stmt)
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Ownership check
    if estimate.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    return estimate


@router.get("", response_model=list[EstimateResponseV3])
async def list_estimates_v3(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List estimates with v3 fields. Supports filtering by status, job_type, county."""
    stmt = select(Estimate).where(
        Estimate.deleted_at.is_(None),
        Estimate.created_by == current_user.id,
    )

    if status:
        stmt = stmt.where(Estimate.status == status)
    if job_type:
        stmt = stmt.where(Estimate.job_type == job_type)
    if county:
        stmt = stmt.where(Estimate.county == county)

    stmt = stmt.order_by(Estimate.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
