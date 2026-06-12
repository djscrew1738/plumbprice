"""Pricing Adjustment Service.

Loads admin-approved pricing corrections from the database and applies them
to labor and material calculations. Adjustments are cached in-memory for
fast lookup during estimate generation.

Adjustment types:
  - labor_hours_multiplier: multiplies labor hours (and thus labor cost)
  - material_markup_override: overrides the materials markup percentage
  - overhead_adder: adds a flat overhead amount to the subtotal

Target types:
  - task_code: applies to a specific labor template
  - canonical_item: applies to a specific material
  - job_type: applies to all jobs of a category (service, construction, commercial)
"""
from __future__ import annotations

from typing import Optional
import structlog

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.pricing_intelligence import PricingAdjustment

logger = structlog.get_logger()


class PricingAdjustmentService:
    """In-memory cached lookup for active pricing adjustments."""

    def __init__(self) -> None:
        self._labor_adjustments: dict[str, list[dict]] = {}   # task_code -> adjustments
        self._material_adjustments: dict[str, list[dict]] = {}  # canonical_item -> adjustments
        self._job_type_adjustments: dict[str, list[dict]] = {}  # job_type -> adjustments
        self._overhead_adjustments: dict[str, list[dict]] = {}  # task_code -> overhead adders
        self._loaded = False

    async def refresh_cache(self, db: AsyncSession | None = None) -> None:
        """Reload all active adjustments from DB into memory."""
        close_db = db is None
        if db is None:
            db = AsyncSessionLocal()
        try:
            result = await db.execute(
                select(PricingAdjustment).where(PricingAdjustment.is_active == True)
            )
            rows = result.scalars().all()

            self._labor_adjustments = {}
            self._material_adjustments = {}
            self._job_type_adjustments = {}
            self._overhead_adjustments = {}

            for row in rows:
                adj = {
                    "id": row.id,
                    "adjustment_type": row.adjustment_type,
                    "target_type": row.target_type,
                    "target_key": row.target_key,
                    "adjustment_value": row.adjustment_value,
                    "rationale": row.rationale,
                }
                if row.adjustment_type == "labor_hours_multiplier":
                    self._labor_adjustments.setdefault(row.target_key, []).append(adj)
                elif row.adjustment_type == "material_markup_override":
                    self._material_adjustments.setdefault(row.target_key, []).append(adj)
                elif row.adjustment_type == "overhead_adder":
                    self._overhead_adjustments.setdefault(row.target_key, []).append(adj)
                # job_type adjustments can be any of the above types
                if row.target_type == "job_type":
                    self._job_type_adjustments.setdefault(row.target_key, []).append(adj)

            self._loaded = True
            logger.info(
                "pricing_adjustments.cache_refreshed",
                labor=len(self._labor_adjustments),
                material=len(self._material_adjustments),
                job_type=len(self._job_type_adjustments),
                overhead=len(self._overhead_adjustments),
            )
        except Exception as exc:
            logger.error("pricing_adjustments.cache_refresh_failed", error=str(exc))
        finally:
            if close_db:
                await db.close()

    # ── Public lookup API ──────────────────────────────────────────────────────

    def get_labor_multiplier(self, task_code: str, job_type: str | None = None) -> float:
        """Return the combined labor hours multiplier for a task_code."""
        multipliers: list[float] = []
        for adj in self._labor_adjustments.get(task_code, []):
            multipliers.append(adj["adjustment_value"])
        if job_type:
            for adj in self._job_type_adjustments.get(job_type, []):
                if adj["adjustment_type"] == "labor_hours_multiplier":
                    multipliers.append(adj["adjustment_value"])
        if not multipliers:
            return 1.0
        # Combine multipliers multiplicatively
        result = 1.0
        for m in multipliers:
            result *= m
        return round(result, 4)

    def get_material_markup_override(self, job_type: str | None = None) -> float | None:
        """Return the material markup override for a job_type, or None if not set."""
        # Only job_type-level material markup overrides are supported for now
        if not job_type:
            return None
        values: list[float] = []
        for adj in self._job_type_adjustments.get(job_type, []):
            if adj["adjustment_type"] == "material_markup_override":
                values.append(adj["adjustment_value"])
        if not values:
            return None
        # Use the most recent (highest id) override
        return values[-1]

    def get_overhead_adder(self, task_code: str, job_type: str | None = None) -> float:
        """Return the total overhead adder for a task_code."""
        total = 0.0
        for adj in self._overhead_adjustments.get(task_code, []):
            total += adj["adjustment_value"]
        if job_type:
            for adj in self._job_type_adjustments.get(job_type, []):
                if adj["adjustment_type"] == "overhead_adder":
                    total += adj["adjustment_value"]
        return round(total, 2)

    # ── Application helpers ────────────────────────────────────────────────────

    def apply_labor_adjustment(self, labor_cost: float, task_code: str, job_type: str | None = None) -> float:
        """Apply labor adjustment multiplier to a labor cost."""
        mult = self.get_labor_multiplier(task_code, job_type)
        if mult == 1.0:
            return labor_cost
        adjusted = labor_cost * mult
        logger.debug("pricing_adjustments.labor_applied", task_code=task_code, mult=mult, before=labor_cost, after=round(adjusted, 2))
        return round(adjusted, 2)

    def apply_material_markup_override(self, markup_pct: float, job_type: str | None = None) -> float:
        """Return the effective markup percentage, considering overrides."""
        override = self.get_material_markup_override(job_type)
        if override is None:
            return markup_pct
        logger.debug("pricing_adjustments.material_markup_applied", job_type=job_type, original=markup_pct, override=override)
        return override


# Singleton
pricing_adjustment_service = PricingAdjustmentService()
