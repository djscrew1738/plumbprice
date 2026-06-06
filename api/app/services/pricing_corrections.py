"""Pricing Corrections Recommendations Engine (E2.3).

Analyzes variance between estimated and actual job costs to identify systematic
pricing biases. Generates PricingRecommendation records for admin review.

IMPORTANT: Recommendations are purely advisory. They are NEVER auto-applied.
An admin must explicitly approve each recommendation before it affects the
pricing engine (see pricing_adjustments table and E2.4).
"""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outcomes import EstimateOutcome
from app.models.estimates import Estimate, EstimateLineItem
from app.models.pricing_intelligence import PricingRecommendation

logger = structlog.get_logger()

# Minimum number of data points required before generating a recommendation
_MIN_SAMPLE_COUNT = 5
# Variance threshold: only recommend if |avg_variance_pct| > this value
_VARIANCE_THRESHOLD_PCT = 5.0
# How many recent closed jobs to analyse per task_code
_LOOKBACK_LIMIT = 30


async def generate_pricing_recommendations(
    db: AsyncSession,
    *,
    organization_id: Optional[int] = None,
) -> list[PricingRecommendation]:
    """Generate pricing correction recommendations from closed job actuals.

    Returns a list of newly-created PricingRecommendation records.
    """
    # Find closed outcomes with actual cost data
    query = (
        select(EstimateOutcome)
        .join(Estimate, Estimate.id == EstimateOutcome.estimate_id)
        .where(
            EstimateOutcome.actual_total.isnot(None),
            EstimateOutcome.outcome == "won",
        )
    )
    if organization_id:
        query = query.where(EstimateOutcome.organization_id == organization_id)

    outcomes = (await db.execute(query)).scalars().all()

    # Group outcomes by task_code via line items
    task_variances: dict[str, list[float]] = {}
    for outcome in outcomes:
        estimate = (
            await db.execute(
                select(Estimate).where(Estimate.id == outcome.estimate_id)
            )
        ).scalar_one_or_none()
        if not estimate or not estimate.grand_total or estimate.grand_total <= 0:
            continue

        variance_pct = (
            ((outcome.actual_total - estimate.grand_total) / estimate.grand_total) * 100
        )

        # Group by dominant task_code from line items
        task_code = await _get_primary_task_code(db, outcome.estimate_id)
        if task_code:
            task_variances.setdefault(task_code, []).append(variance_pct)

    new_recommendations: list[PricingRecommendation] = []

    for task_code, variances in task_variances.items():
        recent = variances[-_LOOKBACK_LIMIT:]  # most recent N
        if len(recent) < _MIN_SAMPLE_COUNT:
            continue

        avg_variance = sum(recent) / len(recent)
        if abs(avg_variance) <= _VARIANCE_THRESHOLD_PCT:
            continue

        # Check if a recent recommendation for this task_code + org already exists
        existing = (
            await db.execute(
                select(PricingRecommendation)
                .where(
                    PricingRecommendation.task_code == task_code,
                    PricingRecommendation.organization_id == organization_id,
                    PricingRecommendation.status == "pending",
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update sample count and variance on existing pending recommendation
            existing.avg_variance_pct = avg_variance
            existing.sample_count = len(recent)
            existing.suggested_adjustment = _compute_adjustment(avg_variance)
            continue

        rec_type, rationale = _classify_variance(avg_variance)
        rec = PricingRecommendation(
            organization_id=organization_id,
            task_code=task_code,
            recommendation_type=rec_type,
            avg_variance_pct=round(avg_variance, 2),
            sample_count=len(recent),
            suggested_adjustment=_compute_adjustment(avg_variance),
            rationale=rationale,
            status="pending",
        )
        db.add(rec)
        new_recommendations.append(rec)

    await db.commit()

    logger.info(
        "pricing_corrections.generated",
        new=len(new_recommendations),
        task_codes=len(task_variances),
        organization_id=organization_id,
    )
    return new_recommendations


async def _get_primary_task_code(
    db: AsyncSession, estimate_id: int
) -> Optional[str]:
    """Return the most common task_code on the estimate's line items."""
    items = (
        await db.execute(
            select(EstimateLineItem)
            .where(EstimateLineItem.estimate_id == estimate_id)
        )
    ).scalars().all()

    if not items:
        return None

    codes: dict[str, int] = {}
    for item in items:
        code = (item.trace_json or {}).get("task_code") or item.description
        if code:
            codes[code] = codes.get(code, 0) + 1

    return max(codes, key=lambda k: codes[k]) if codes else None


def _classify_variance(avg_variance_pct: float) -> tuple[str, str]:
    """Determine recommendation type and rationale from variance direction."""
    if avg_variance_pct > 0:
        # Actual > Estimated → we are underpricing
        return (
            "adjust_labor_hours",
            f"Actuals are averaging {avg_variance_pct:.1f}% higher than estimates. "
            "Consider increasing labor hour estimates for this task type.",
        )
    else:
        # Actual < Estimated → we are overpricing (winning less)
        return (
            "adjust_material_markup",
            f"Actuals are averaging {abs(avg_variance_pct):.1f}% lower than estimates. "
            "Review material markup — may be reducing win rate.",
        )


def _compute_adjustment(avg_variance_pct: float) -> float:
    """Compute a suggested multiplier adjustment from variance percentage.

    Example: if we're 10% under, suggest a 1.10 multiplier on labor.
    Capped at ±30% to prevent wild swings from small sample sizes.
    """
    adjustment = 1.0 + (avg_variance_pct / 100.0)
    return round(max(0.70, min(1.30, adjustment)), 4)
