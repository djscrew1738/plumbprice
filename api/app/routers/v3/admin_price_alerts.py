"""Admin price alerts — surface significant supplier price changes.

Queries SupplierPriceHistory for deviations above the configured threshold
so admins can review and decide whether to update estimates or investigate.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.suppliers import SupplierProduct, SupplierPriceHistory, Supplier
from app.core.auth import get_current_admin

router = APIRouter(prefix="/admin/price-alerts", tags=["admin"])


class PriceAlertItem(BaseModel):
    id: int
    product_id: int
    canonical_item: str
    product_name: str
    supplier_name: str
    old_cost: float
    new_cost: float
    pct_change: float
    source: str
    recorded_at: str


class PriceAlertListResponse(BaseModel):
    alerts: list[PriceAlertItem]
    total: int
    threshold_pct: float


@router.get("", response_model=PriceAlertListResponse)
async def list_price_alerts(
    days: int = Query(7, ge=1, le=90, description="Lookback window in days"),
    threshold_pct: float = Query(10.0, ge=0.1, le=100.0, description="Minimum % change to include"),
    supplier_slug: Optional[str] = Query(None, description="Filter by supplier slug"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> PriceAlertListResponse:
    """List significant supplier price changes over the lookback window.

    Compares each history entry to the previous cost for that product
    and returns entries where the absolute pct change >= threshold.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Subquery: find the most recent history entry per product in the window
    latest_hist_subq = (
        select(
            SupplierPriceHistory.product_id,
            func.max(SupplierPriceHistory.recorded_at).label("latest_at"),
        )
        .where(SupplierPriceHistory.recorded_at >= since)
        .group_by(SupplierPriceHistory.product_id)
        .subquery()
    )

    # Main query: join history + products + suppliers
    stmt = (
        select(
            SupplierPriceHistory,
            SupplierProduct.canonical_item,
            SupplierProduct.name.label("product_name"),
            Supplier.name.label("supplier_name"),
            Supplier.slug.label("supplier_slug"),
        )
        .join(SupplierProduct, SupplierPriceHistory.product_id == SupplierProduct.id)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .join(
            latest_hist_subq,
            (SupplierPriceHistory.product_id == latest_hist_subq.c.product_id)
            & (SupplierPriceHistory.recorded_at == latest_hist_subq.c.latest_at),
        )
        .where(SupplierPriceHistory.recorded_at >= since)
        .order_by(SupplierPriceHistory.recorded_at.desc())
    )

    if supplier_slug:
        stmt = stmt.where(Supplier.slug == supplier_slug)

    result = await db.execute(stmt)
    rows = result.all()

    alerts: list[PriceAlertItem] = []
    for hist, canonical_item, product_name, supplier_name, slug in rows:
        # Find previous cost for this product (before this history entry)
        prev_stmt = (
            select(SupplierPriceHistory.cost)
            .where(
                SupplierPriceHistory.product_id == hist.product_id,
                SupplierPriceHistory.recorded_at < hist.recorded_at,
            )
            .order_by(SupplierPriceHistory.recorded_at.desc())
            .limit(1)
        )
        prev_result = await db.execute(prev_stmt)
        prev_row = prev_result.scalar_one_or_none()
        old_cost = prev_row if prev_row is not None else hist.cost

        if old_cost <= 0:
            continue
        pct_change = abs(hist.cost - old_cost) / old_cost * 100
        if pct_change < threshold_pct:
            continue

        alerts.append(
            PriceAlertItem(
                id=hist.id,
                product_id=hist.product_id,
                canonical_item=canonical_item or "",
                product_name=product_name or "",
                supplier_name=supplier_name or "",
                old_cost=round(old_cost, 2),
                new_cost=round(hist.cost, 2),
                pct_change=round(pct_change, 1),
                source=hist.source or "",
                recorded_at=hist.recorded_at.isoformat() if hist.recorded_at else "",
            )
        )

    # Apply limit/offset after filtering
    total = len(alerts)
    alerts = alerts[offset : offset + limit]

    return PriceAlertListResponse(
        alerts=alerts,
        total=total,
        threshold_pct=threshold_pct,
    )
