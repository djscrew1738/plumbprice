"""Supplier price drift detection (c2-dfw-intelligence).

Compares the most recent recorded cost for each active SupplierProduct
against the cost N days ago and flags products whose absolute
percentage delta exceeds a threshold (default 15%).

Designed to be cheap enough to run nightly via the worker:
    drifts = await detect_price_drifts(db, lookback_days=30, threshold_pct=0.15)
    for d in drifts:
        ...

The service is also exposed read-only via the admin router so the
volatility dashboard can pull current state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suppliers import Supplier, SupplierPriceHistory, SupplierProduct


@dataclass
class PriceDrift:
    product_id: int
    canonical_item: str
    supplier_id: int
    supplier_name: Optional[str]
    sku: Optional[str]
    name: str
    current_cost: float
    baseline_cost: float
    baseline_at: Optional[datetime]
    delta_pct: float  # signed: positive = price went up
    direction: str  # "up" | "down"


async def detect_price_drifts(
    db: AsyncSession,
    *,
    lookback_days: int = 30,
    threshold_pct: float = 0.15,
    limit: int = 200,
) -> List[PriceDrift]:
    """Return products whose latest cost has drifted past `threshold_pct`
    vs the most recent history row at least `lookback_days` ago.

    Comparison rules:
      - Use SupplierProduct.cost as the "current" price (canonical).
      - Pull the most recent SupplierPriceHistory row with
        recorded_at <= now - lookback_days as the baseline.
      - If no baseline exists (new product), skip.
      - delta_pct = (current - baseline) / baseline. abs(delta) >=
        threshold flags it.

    Sorted by abs(delta_pct) desc.
    """
    if threshold_pct <= 0:
        raise ValueError("threshold_pct must be > 0")

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    products_res = await db.execute(
        select(SupplierProduct).where(SupplierProduct.is_active == True)  # noqa: E712
    )
    products = list(products_res.scalars().all())
    if not products:
        return []

    suppliers_res = await db.execute(select(Supplier))
    supplier_names = {s.id: s.name for s in suppliers_res.scalars().all()}

    drifts: List[PriceDrift] = []
    for p in products:
        if p.cost is None or p.cost <= 0:
            continue
        hist_res = await db.execute(
            select(SupplierPriceHistory)
            .where(SupplierPriceHistory.product_id == p.id)
            .where(SupplierPriceHistory.recorded_at <= cutoff)
            .order_by(SupplierPriceHistory.recorded_at.desc())
            .limit(1)
        )
        baseline = hist_res.scalar_one_or_none()
        if baseline is None or baseline.cost is None or baseline.cost <= 0:
            continue
        delta = (p.cost - baseline.cost) / baseline.cost
        if abs(delta) < threshold_pct:
            continue
        drifts.append(
            PriceDrift(
                product_id=p.id,
                canonical_item=p.canonical_item,
                supplier_id=p.supplier_id,
                supplier_name=supplier_names.get(p.supplier_id),
                sku=p.sku,
                name=p.name,
                current_cost=float(p.cost),
                baseline_cost=float(baseline.cost),
                baseline_at=baseline.recorded_at,
                delta_pct=round(delta, 4),
                direction="up" if delta > 0 else "down",
            )
        )

    drifts.sort(key=lambda d: abs(d.delta_pct), reverse=True)
    return drifts[:limit]


async def price_history_for_product(
    db: AsyncSession,
    product_id: int,
    *,
    lookback_days: int = 90,
) -> List[dict]:
    """Time-series of recorded prices for a single product."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    res = await db.execute(
        select(SupplierPriceHistory)
        .where(SupplierPriceHistory.product_id == product_id)
        .where(SupplierPriceHistory.recorded_at >= cutoff)
        .order_by(SupplierPriceHistory.recorded_at.asc())
    )
    return [
        {
            "cost": float(row.cost),
            "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
            "source": row.source,
        }
        for row in res.scalars().all()
    ]
