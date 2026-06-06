"""Celery task: Compute price trend labels for supplier products (E1.4).

Uses linear regression over the last 90 days of supplier_price_history to
label each canonical item as "rising", "stable", or "falling". Results are
stored on supplier_products.price_trend.

Scheduled weekly via Celery Beat on the ml queue.
"""
from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.suppliers import SupplierProduct, SupplierPriceHistory
from worker.worker import app

logger = structlog.get_logger()

# Minimum number of price history points required to compute a trend
_MIN_HISTORY_POINTS = 5
# History window in days
_HISTORY_DAYS = 90
# Slope threshold (fraction per day) above which we label as rising/falling
_SLOPE_THRESHOLD = 0.001  # 0.1% per day


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    """Compute slope of OLS regression line (y = a + bx). Returns b."""
    n = len(xs)
    if n < 2:
        return 0.0
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x ** 2
    if math.isclose(denom, 0.0):
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


async def _async_compute_price_trends() -> dict:
    """Compute price trend labels for all supplier products with sufficient history."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_HISTORY_DAYS)
    updated = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        try:
            products = (await db.execute(select(SupplierProduct))).scalars().all()

            for product in products:
                # Fetch price history for this product within the window
                rows = (
                    await db.execute(
                        select(SupplierPriceHistory)
                        .where(
                            SupplierPriceHistory.product_id == product.id,
                            SupplierPriceHistory.recorded_at >= cutoff,
                        )
                        .order_by(SupplierPriceHistory.recorded_at)
                    )
                ).scalars().all()

                if len(rows) < _MIN_HISTORY_POINTS:
                    skipped += 1
                    continue

                # xs = days since first point, ys = unit_cost
                t0 = rows[0].recorded_at.timestamp()
                xs = [(r.recorded_at.timestamp() - t0) / 86400 for r in rows]
                ys = [r.cost for r in rows]

                # Normalise slope relative to mean price to get a fraction-per-day
                mean_price = sum(ys) / len(ys)
                if mean_price <= 0:
                    skipped += 1
                    continue

                slope = _linear_slope(xs, ys)
                relative_slope = slope / mean_price  # fraction per day

                if relative_slope > _SLOPE_THRESHOLD:
                    trend = "rising"
                elif relative_slope < -_SLOPE_THRESHOLD:
                    trend = "falling"
                else:
                    trend = "stable"

                product.price_trend = trend
                product.price_trend_computed_at = datetime.now(timezone.utc)
                updated += 1

            await db.commit()

        except Exception as exc:
            logger.error("price_forecast.failed", error=str(exc))
            await db.rollback()
            raise

    logger.info("price_forecast.complete", updated=updated, skipped=skipped)
    return {"updated": updated, "skipped": skipped}


@app.task(name="worker.tasks.price_forecast.compute_price_trends", bind=True, max_retries=2)
def compute_price_trends(self):
    """Celery entry point for weekly price trend computation."""
    try:
        return asyncio.run(_async_compute_price_trends())
    except Exception as exc:
        logger.error("price_forecast.task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=3600)
