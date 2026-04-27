"""Supplier price drift admin router (c2-dfw-intelligence).

Endpoints (all admin-only):
* GET /api/v1/admin/supplier-prices/drift
    - List products whose price has drifted past the threshold.
    - Query: lookback_days (default 30), threshold_pct (default 0.15),
      limit (default 200).
* GET /api/v1/admin/supplier-prices/{product_id}/history
    - Time-series of recorded prices for a single product.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.users import User
from app.services.price_drift import (
    detect_price_drifts,
    price_history_for_product,
)

logger = structlog.get_logger()
router = APIRouter()


def _require_admin(user: User) -> None:
    role = (getattr(user, "role", None) or "").lower()
    if role not in ("admin", "owner", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/drift")
async def list_price_drifts(
    lookback_days: int = Query(30, ge=1, le=365),
    threshold_pct: float = Query(0.15, gt=0, le=1.0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    drifts = await detect_price_drifts(
        db,
        lookback_days=lookback_days,
        threshold_pct=threshold_pct,
        limit=limit,
    )
    return {
        "lookback_days": lookback_days,
        "threshold_pct": threshold_pct,
        "count": len(drifts),
        "drifts": [
            {
                "product_id": d.product_id,
                "canonical_item": d.canonical_item,
                "supplier_id": d.supplier_id,
                "supplier_name": d.supplier_name,
                "sku": d.sku,
                "name": d.name,
                "current_cost": d.current_cost,
                "baseline_cost": d.baseline_cost,
                "baseline_at": d.baseline_at.isoformat() if d.baseline_at else None,
                "delta_pct": d.delta_pct,
                "direction": d.direction,
            }
            for d in drifts
        ],
    }


@router.get("/{product_id}/history")
async def product_price_history(
    product_id: int,
    lookback_days: int = Query(90, ge=1, le=730),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    series = await price_history_for_product(db, product_id, lookback_days=lookback_days)
    return {"product_id": product_id, "lookback_days": lookback_days, "series": series}
