"""
Market Pricing Engine — v3

Applies dynamic pricing adjustments to estimates based on market conditions.
All adjustments are transparent: the UI shows each factor and its rationale.

Examples:
- Copper price surge: +3.2% on materials
- Summer demand spike: +5% on labor in Dallas county
- Fuel surcharge: +1.5% on trip charges
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import structlog

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_adjustments import MarketAdjustment
from app.core.cache import cache_get, cache_set, cache_invalidate

logger = structlog.get_logger()


@dataclass
class AppliedAdjustment:
    name: str
    category: str
    factor: float
    applies_to: list[str]
    source: str


class MarketPricingEngine:
    """Dynamic pricing adjustment engine for v3 estimates."""

    _CACHE_TTL = 300  # 5 minutes

    async def get_active_adjustments(
        self,
        db: AsyncSession,
        county: str,
        categories: Optional[list[str]] = None,
    ) -> list[MarketAdjustment]:
        """Fetch all active market adjustments applicable to a county.

        Results are cached in Redis for 5 minutes to reduce DB load.
        """
        cache_key = f"market_adj:{county.lower()}:{','.join(sorted(categories or []))}"
        cached = await cache_get(cache_key)
        if cached is not None:
            # Rehydrate MarketAdjustment objects from cached dicts
            return [
                MarketAdjustment(
                    id=c["id"],
                    name=c["name"],
                    factor=c["factor"],
                    category=c["category"],
                    applies_to=c["applies_to"],
                    counties=c.get("counties"),
                    effective_from=c["effective_from"],
                    effective_until=c["effective_until"],
                    source=c.get("source", "admin"),
                    is_active=c.get("is_active", True),
                    created_by=c.get("created_by"),
                )
                for c in cached
            ]

        now = datetime.now(timezone.utc)

        stmt = select(MarketAdjustment).where(
            and_(
                MarketAdjustment.is_active == True,
                MarketAdjustment.effective_from <= now,
                MarketAdjustment.effective_until >= now,
            )
        )

        result = await db.execute(stmt)
        rows = result.scalars().all()

        # Filter by county (NULL counties = all counties)
        applicable = []
        for adj in rows:
            if adj.counties is None or county in adj.counties:
                if categories is None or any(cat in categories for cat in adj.applies_to):
                    applicable.append(adj)

        # Serialize and cache
        serializable = [
            {
                "id": a.id,
                "name": a.name,
                "factor": a.factor,
                "category": a.category,
                "applies_to": a.applies_to,
                "counties": a.counties,
                "effective_from": a.effective_from.isoformat() if a.effective_from else None,
                "effective_until": a.effective_until.isoformat() if a.effective_until else None,
                "source": a.source,
                "is_active": a.is_active,
                "created_by": a.created_by,
            }
            for a in applicable
        ]
        await cache_set(cache_key, serializable, ttl=self._CACHE_TTL)
        return applicable

    def apply_adjustments(
        self,
        estimate: dict,
        adjustments: list[MarketAdjustment],
    ) -> tuple[dict, list[AppliedAdjustment]]:
        """Apply market adjustments to an estimate and return the modified estimate + trace.

        The estimate dict must contain:
            labor_total, materials_total, markup_total, tax_total, misc_total,
            subtotal, grand_total, county
        """
        if not adjustments:
            estimate["market_adjustment_applied"] = 1.0
            estimate["confidence_components"] = estimate.get("confidence_components", {})
            return estimate, []

        applied: list[AppliedAdjustment] = []

        # Track per-category multipliers
        labor_factor = 1.0
        materials_factor = 1.0
        markup_factor = 1.0
        misc_factor = 1.0
        trip_factor = 1.0

        for adj in adjustments:
            factor = adj.factor
            applies = adj.applies_to or ["materials"]

            if "labor" in applies:
                labor_factor *= factor
            if "materials" in applies:
                materials_factor *= factor
            if "markup" in applies:
                markup_factor *= factor
            if "misc" in applies:
                misc_factor *= factor
            if "trip" in applies:
                trip_factor *= factor

            applied.append(AppliedAdjustment(
                name=adj.name,
                category=adj.category,
                factor=factor,
                applies_to=applies,
                source=adj.source,
            ))

        # Apply factors
        original_labor = estimate.get("labor_total", 0.0)
        original_materials = estimate.get("materials_total", 0.0)
        original_markup = estimate.get("markup_total", 0.0)
        original_misc = estimate.get("misc_total", 0.0)
        original_tax = estimate.get("tax_total", 0.0)
        original_trip = estimate.get("trip_charge", 0.0)

        estimate["labor_total"] = round(original_labor * labor_factor, 2)
        estimate["materials_total"] = round(original_materials * materials_factor, 2)
        estimate["markup_total"] = round(original_markup * markup_factor, 2)
        estimate["misc_total"] = round(original_misc * misc_factor, 2)
        estimate["trip_charge"] = round(original_trip * trip_factor, 2)

        # Recalculate tax (materials only in TX)
        tax_rate = estimate.get("tax_rate", 0.0825)
        estimate["tax_total"] = round(estimate["materials_total"] * tax_rate, 2)

        # Recalculate subtotal and grand_total
        estimate["subtotal"] = round(
            estimate["labor_total"]
            + estimate["materials_total"]
            + estimate["markup_total"]
            + estimate["misc_total"]
            + estimate["trip_charge"],
            2,
        )
        estimate["grand_total"] = round(estimate["subtotal"] + estimate["tax_total"], 2)

        # Overall adjustment factor (weighted by cost category)
        total_before = original_labor + original_materials + original_markup + original_misc + original_trip + original_tax
        total_after = estimate["grand_total"]
        overall_factor = round(total_after / total_before, 4) if total_before > 0 else 1.0
        estimate["market_adjustment_applied"] = overall_factor

        # Confidence impact: each active adjustment slightly reduces confidence
        confidence_components = estimate.get("confidence_components", {})
        confidence_components["market_volatility"] = round(-0.03 * len(adjustments), 2)
        estimate["confidence_components"] = confidence_components

        logger.info(
            "market_pricing.applied",
            county=estimate.get("county"),
            adjustment_count=len(adjustments),
            overall_factor=overall_factor,
            grand_total_before=total_before,
            grand_total_after=total_after,
        )

        return estimate, applied

    async def preview_adjustments(
        self,
        db: AsyncSession,
        county: str,
        base_estimate: dict,
    ) -> dict:
        """Preview what adjustments would apply to an estimate without modifying it."""
        adjustments = await self.get_active_adjustments(db, county)
        preview_estimate = dict(base_estimate)
        _, applied = self.apply_adjustments(preview_estimate, adjustments)
        return {
            "base_total": base_estimate.get("grand_total", 0.0),
            "adjusted_total": preview_estimate["grand_total"],
            "overall_factor": preview_estimate["market_adjustment_applied"],
            "adjustments": [
                {
                    "name": a.name,
                    "category": a.category,
                    "factor": a.factor,
                    "applies_to": a.applies_to,
                    "source": a.source,
                }
                for a in applied
            ],
        }


    async def invalidate_cache(self, county: str | None = None) -> None:
        """Invalidate adjustment cache. Called by CRUD operations."""
        if county:
            # Best-effort: delete exact key and wildcard is tricky in Redis without scan
            # We use a simpler approach: delete the broad key pattern via scan
            from app.core.cache import _get_redis
            redis = _get_redis()
            try:
                async for key in redis.scan_iter(match="market_adj:*"):
                    await redis.delete(key)
            except Exception as exc:
                logger.warning("market_pricing.cache_invalidate_failed", error=str(exc))
        else:
            await cache_invalidate("market_adj:*")


# ── Singleton ─────────────────────────────────────────────────────────────────

market_pricing_engine = MarketPricingEngine()
