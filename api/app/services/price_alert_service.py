"""Price alert service — detects and records significant price changes (E1.3).

After each supplier refresh, compares new prices to the most recent
supplier_price_history row. If the delta exceeds the configured threshold
(default ±10%), a SupplierPriceAlert record is created.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.suppliers import SupplierProduct, SupplierPriceHistory
from app.models.pricing_intelligence import SupplierPriceAlert

logger = structlog.get_logger()


async def check_price_alerts(
    db: AsyncSession,
    *,
    supplier_id: Optional[int] = None,
    threshold: Optional[float] = None,
) -> list[SupplierPriceAlert]:
    """Compare current supplier product prices to the previous price history entry.

    Creates SupplierPriceAlert records for any product whose price changed by
    more than ``threshold`` (fraction, default from settings).

    Returns newly created alert records.
    """
    alert_threshold = threshold if threshold is not None else settings.price_change_alert_threshold

    query = select(SupplierProduct)
    if supplier_id:
        query = query.where(SupplierProduct.supplier_id == supplier_id)

    products = (await db.execute(query)).scalars().all()
    new_alerts: list[SupplierPriceAlert] = []

    for product in products:
        if product.cost is None or product.cost <= 0:
            continue

        # Find the previous price history entry (the one before the latest)
        history = (
            await db.execute(
                select(SupplierPriceHistory)
                .where(SupplierPriceHistory.product_id == product.id)
                .order_by(SupplierPriceHistory.recorded_at.desc())
                .limit(2)
            )
        ).scalars().all()

        if len(history) < 2:
            # Not enough history to compute a delta
            continue

        # history[0] is newest (just updated), history[1] is previous
        new_price = history[0].cost
        old_price = history[1].cost

        if old_price <= 0:
            continue

        delta_pct = (new_price - old_price) / old_price

        if abs(delta_pct) < alert_threshold:
            continue

        # Check for duplicate unacknowledged alert for same product today
        existing = (
            await db.execute(
                select(SupplierPriceAlert)
                .where(
                    SupplierPriceAlert.supplier_id == product.supplier_id,
                    SupplierPriceAlert.canonical_item == product.canonical_item,
                    SupplierPriceAlert.acknowledged == False,  # noqa: E712
                )
                .order_by(SupplierPriceAlert.alerted_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if existing:
            # Update the existing alert instead of creating a duplicate
            existing.old_price = old_price
            existing.new_price = new_price
            existing.delta_pct = round(delta_pct * 100, 2)
            existing.alerted_at = datetime.now(timezone.utc)
            continue

        alert = SupplierPriceAlert(
            supplier_id=product.supplier_id,
            canonical_item=product.canonical_item,
            old_price=old_price,
            new_price=new_price,
            delta_pct=round(delta_pct * 100, 2),
        )
        db.add(alert)
        new_alerts.append(alert)

        logger.info(
            "price_alert.created",
            canonical_item=product.canonical_item,
            delta_pct=round(delta_pct * 100, 2),
            old_price=old_price,
            new_price=new_price,
        )

    if new_alerts or True:
        await db.commit()

    return new_alerts
