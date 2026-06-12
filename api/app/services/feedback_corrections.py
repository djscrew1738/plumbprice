"""Feedback-driven pricing corrections engine.

Analyzes estimate_feedback votes (thumbs up/down) by task_code to identify
systematic pricing issues. Generates PricingRecommendation records for admin
review when negative feedback crosses a threshold.

This complements the outcome-driven pricing_corrections.py (which uses actual
job costs) with a faster, user-driven signal loop.
"""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateFeedback, EstimateLineItem
from app.models.pricing_intelligence import PricingRecommendation

logger = structlog.get_logger()

# Minimum number of total votes on a task_code before we consider it
_MIN_TOTAL_VOTES = 3
# Minimum ratio of down-votes to total votes to trigger a recommendation
_MIN_DOWNVOTE_RATIO = 0.6
# Maximum age in days of feedback to consider
_MAX_FEEDBACK_AGE_DAYS = 90


async def analyze_task_code_feedback(
    db: AsyncSession,
    task_code: str,
    organization_id: Optional[int] = None,
) -> dict:
    """Return feedback statistics for a given task_code.

    Result includes up_count, down_count, total, down_ratio, and
    a flag indicating whether the threshold for a recommendation is met.
    """
    # Find all estimates that have this task_code as their primary task
    subq = (
        select(EstimateLineItem.estimate_id)
        .where(
            EstimateLineItem.trace_json.isnot(None),
        )
        .distinct()
    )
    estimate_ids = [row[0] for row in (await db.execute(subq)).fetchall()]

    # Filter to estimates whose primary task_code matches
    matching_estimate_ids: list[int] = []
    for eid in estimate_ids:
        primary = await _get_primary_task_code(db, eid)
        if primary == task_code:
            matching_estimate_ids.append(eid)

    if not matching_estimate_ids:
        return {
            "task_code": task_code,
            "up_count": 0,
            "down_count": 0,
            "total": 0,
            "down_ratio": 0.0,
            "threshold_met": False,
        }

    # Count votes
    counts = await db.execute(
        select(
            EstimateFeedback.vote,
            func.count(EstimateFeedback.id),
        )
        .where(EstimateFeedback.estimate_id.in_(matching_estimate_ids))
        .group_by(EstimateFeedback.vote)
    )
    vote_counts = {row[0]: row[1] for row in counts.fetchall()}
    up_count = vote_counts.get("up", 0)
    down_count = vote_counts.get("down", 0)
    total = up_count + down_count

    down_ratio = down_count / total if total > 0 else 0.0
    threshold_met = (
        total >= _MIN_TOTAL_VOTES and down_ratio >= _MIN_DOWNVOTE_RATIO
    )

    return {
        "task_code": task_code,
        "up_count": up_count,
        "down_count": down_count,
        "total": total,
        "down_ratio": round(down_ratio, 2),
        "threshold_met": threshold_met,
    }


async def generate_recommendation_from_feedback(
    db: AsyncSession,
    task_code: str,
    organization_id: Optional[int] = None,
) -> Optional[PricingRecommendation]:
    """Generate a PricingRecommendation from negative feedback if thresholds are met.

    Returns the created recommendation, or None if thresholds not met or one
    already exists.
    """
    stats = await analyze_task_code_feedback(db, task_code, organization_id)
    if not stats["threshold_met"]:
        return None

    # Check for existing pending feedback-driven recommendation
    existing = (
        await db.execute(
            select(PricingRecommendation)
            .where(
                PricingRecommendation.task_code == task_code,
                PricingRecommendation.organization_id == organization_id,
                PricingRecommendation.status == "pending",
                PricingRecommendation.source == "feedback",
            )
        )
    ).scalar_one_or_none()

    if existing:
        # Update sample count (feedback total) on existing pending rec
        existing.sample_count = stats["total"]
        existing.avg_variance_pct = round(-stats["down_ratio"] * 20, 2)
        existing.suggested_adjustment = _compute_adjustment(
            existing.avg_variance_pct
        )
        existing.rationale = (
            f"{stats['down_count']} of {stats['total']} recent user feedback votes "
            f"({stats['down_ratio']*100:.0f}%) were negative for this task code. "
            "Review pricing accuracy."
        )
        await db.commit()
        await db.refresh(existing)
        return existing

    rec = PricingRecommendation(
        organization_id=organization_id,
        task_code=task_code,
        recommendation_type="feedback_review",
        avg_variance_pct=round(-stats["down_ratio"] * 20, 2),
        sample_count=stats["total"],
        suggested_adjustment=_compute_adjustment(-stats["down_ratio"] * 20),
        rationale=(
            f"{stats['down_count']} of {stats['total']} recent user feedback votes "
            f"({stats['down_ratio']*100:.0f}%) were negative for this task code. "
            "Review pricing accuracy."
        ),
        status="pending",
        source="feedback",
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    logger.info(
        "feedback_corrections.recommendation_created",
        task_code=task_code,
        down_count=stats["down_count"],
        total=stats["total"],
        rec_id=rec.id,
    )
    return rec


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


def _compute_adjustment(avg_variance_pct: float) -> float:
    """Compute a suggested multiplier adjustment from variance percentage."""
    adjustment = 1.0 + (avg_variance_pct / 100.0)
    return round(max(0.70, min(1.30, adjustment)), 4)
