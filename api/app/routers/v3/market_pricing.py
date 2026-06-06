"""
Market Pricing API v3 — Admin CRUD for dynamic pricing adjustments.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.market_adjustments import MarketAdjustment
from app.schemas.v3.market_pricing import MarketAdjustmentCreate, MarketAdjustmentResponse, MarketAdjustmentPreviewRequest
from app.services.market_pricing import market_pricing_engine

router = APIRouter()


def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/adjustments", response_model=list[MarketAdjustmentResponse])
async def list_adjustments(
    active_only: bool = True,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List market pricing adjustments."""
    _require_admin(current_user)

    stmt = select(MarketAdjustment)
    if active_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(
            MarketAdjustment.is_active == True,
            MarketAdjustment.effective_from <= now,
            MarketAdjustment.effective_until >= now,
        )
    if category:
        stmt = stmt.where(MarketAdjustment.category == category)

    stmt = stmt.order_by(MarketAdjustment.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/adjustments", response_model=MarketAdjustmentResponse)
async def create_adjustment(
    req: MarketAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new market pricing adjustment."""
    _require_admin(current_user)

    adj = MarketAdjustment(
        name=req.name,
        factor=req.factor,
        category=req.category,
        applies_to=req.applies_to,
        counties=req.counties,
        effective_from=req.effective_from,
        effective_until=req.effective_until,
        source=req.source,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(adj)
    await db.commit()
    await db.refresh(adj)
    await market_pricing_engine.invalidate_cache()
    return adj


@router.patch("/adjustments/{adjustment_id}", response_model=MarketAdjustmentResponse)
async def update_adjustment(
    adjustment_id: int,
    req: MarketAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing market pricing adjustment."""
    _require_admin(current_user)

    stmt = select(MarketAdjustment).where(MarketAdjustment.id == adjustment_id)
    result = await db.execute(stmt)
    adj = result.scalar_one_or_none()
    if not adj:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    adj.name = req.name
    adj.factor = req.factor
    adj.category = req.category
    adj.applies_to = req.applies_to
    adj.counties = req.counties
    adj.effective_from = req.effective_from
    adj.effective_until = req.effective_until
    adj.source = req.source

    await db.commit()
    await db.refresh(adj)
    await market_pricing_engine.invalidate_cache()
    return adj


@router.delete("/adjustments/{adjustment_id}")
async def delete_adjustment(
    adjustment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a market pricing adjustment (mark inactive)."""
    _require_admin(current_user)

    result = await db.execute(
        update(MarketAdjustment)
        .where(MarketAdjustment.id == adjustment_id)
        .values(is_active=False)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    await db.commit()
    await market_pricing_engine.invalidate_cache()
    return {"status": "deleted"}


@router.post("/adjustments/preview")
async def preview_adjustments(
    req: MarketAdjustmentPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview what active adjustments would do to a sample estimate."""
    _require_admin(current_user)

    base_estimate = {
        "labor_total": req.base_labor,
        "materials_total": req.base_materials,
        "markup_total": req.base_markup,
        "misc_total": req.base_misc,
        "trip_charge": req.base_trip,
        "tax_rate": req.tax_rate,
        "tax_total": round(req.base_materials * req.tax_rate, 2),
        "subtotal": req.base_labor + req.base_materials + req.base_markup + req.base_misc + req.base_trip,
        "grand_total": req.base_labor + req.base_materials + req.base_markup + req.base_misc + req.base_trip + round(req.base_materials * req.tax_rate, 2),
        "county": req.county,
        "confidence_components": {},
    }

    preview = await market_pricing_engine.preview_adjustments(db, req.county, base_estimate)
    return preview
