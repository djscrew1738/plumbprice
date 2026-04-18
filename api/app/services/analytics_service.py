"""Analytics aggregation service.

Computes revenue, pipeline, and rep-performance rollups from Outcome,
Project, ProjectActivity, and Estimate tables. Kept as plain functions
to stay unit-testable outside the router layer.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate
from app.models.outcomes import EstimateOutcome
from app.models.projects import Project, ProjectActivity
from app.models.users import User


Period = Literal["30d", "90d", "365d", "all"]

PIPELINE_STAGES = ["lead", "estimate_sent", "won", "lost", "in_progress", "complete"]


def period_to_cutoff(period: Period) -> Optional[datetime]:
    """Convert a period string to a UTC cutoff datetime. ``all`` returns None."""
    if period == "all":
        return None
    days = {"30d": 30, "90d": 90, "365d": 365}.get(period)
    if days is None:
        return None
    return datetime.now(timezone.utc) - timedelta(days=days)


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


async def compute_revenue(
    db: AsyncSession,
    organization_id: Optional[int],
    period: Period = "all",
) -> dict:
    """Aggregate won outcomes for an organization.

    Returns totals, deal counts, by-month breakdown, and by-job-type breakdown.
    """
    cutoff = period_to_cutoff(period)

    stmt = (
        select(
            EstimateOutcome.id,
            EstimateOutcome.final_price,
            EstimateOutcome.created_at,
            Estimate.job_type,
        )
        .join(Estimate, EstimateOutcome.estimate_id == Estimate.id)
        .where(
            EstimateOutcome.outcome == "won",
            EstimateOutcome.organization_id.is_(organization_id)
            if organization_id is None
            else EstimateOutcome.organization_id == organization_id,
        )
    )
    if cutoff is not None:
        stmt = stmt.where(EstimateOutcome.created_at >= cutoff)

    result = await db.execute(stmt)
    rows = result.all()

    total_won = 0.0
    deal_count = 0
    by_month: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    by_job: dict[str, dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "count": 0})

    for row in rows:
        price = float(row.final_price or 0.0)
        deal_count += 1
        total_won += price

        created = row.created_at
        if isinstance(created, datetime):
            mkey = _month_key(created)
            by_month[mkey]["amount"] += price
            by_month[mkey]["count"] += 1

        jt = row.job_type or "unknown"
        by_job[jt]["amount"] += price
        by_job[jt]["count"] += 1

    avg_deal_size = round(total_won / deal_count, 2) if deal_count else 0.0

    return {
        "period": period,
        "total_won": round(total_won, 2),
        "deal_count": deal_count,
        "avg_deal_size": avg_deal_size,
        "by_month": [
            {"month": m, "amount": round(v["amount"], 2), "count": int(v["count"])}
            for m, v in sorted(by_month.items())
        ],
        "by_job_type": [
            {"type": t, "amount": round(v["amount"], 2), "count": int(v["count"])}
            for t, v in sorted(by_job.items(), key=lambda kv: -kv[1]["amount"])
        ],
    }


async def compute_pipeline(
    db: AsyncSession,
    organization_id: Optional[int],
) -> dict:
    """Stage counts, average residency hours per stage, and conversion rates."""
    project_filter = (
        Project.organization_id.is_(None)
        if organization_id is None
        else Project.organization_id == organization_id
    )

    # Stage counts — initialize all known stages with 0 so the shape is stable.
    stage_counts: dict[str, int] = {s: 0 for s in PIPELINE_STAGES}
    count_stmt = (
        select(Project.status, func.count(Project.id))
        .where(project_filter)
        .group_by(Project.status)
    )
    for status_val, count in (await db.execute(count_stmt)).all():
        if status_val:
            stage_counts[status_val] = int(count)

    # Pull projects and activities for residency + reach calculations.
    projects_rows = (
        await db.execute(
            select(Project.id, Project.status, Project.created_at).where(project_filter)
        )
    ).all()
    project_ids = [r.id for r in projects_rows]

    reached: dict[str, set[int]] = defaultdict(set)
    # All existing projects have reached their current stage.
    for r in projects_rows:
        if r.status:
            reached[r.status].add(r.id)
        # Default-created projects start in "lead" — ensure that stage is reached
        # even if someone immediately transitioned away.
        reached["lead"].add(r.id)

    stage_durations: dict[str, list[float]] = defaultdict(list)

    if project_ids:
        act_stmt = (
            select(
                ProjectActivity.project_id,
                ProjectActivity.created_at,
                ProjectActivity.payload,
            )
            .where(
                ProjectActivity.project_id.in_(project_ids),
                ProjectActivity.kind == "stage_changed",
            )
            .order_by(ProjectActivity.project_id, ProjectActivity.created_at)
        )
        activity_rows = (await db.execute(act_stmt)).all()

        created_by_project = {r.id: r.created_at for r in projects_rows}
        prev_ts: dict[int, datetime] = {}

        for act in activity_rows:
            pid = act.project_id
            payload = act.payload or {}
            frm = payload.get("from")
            to = payload.get("to")
            if frm:
                reached[frm].add(pid)
            if to:
                reached[to].add(pid)

            start_ts = prev_ts.get(pid) or created_by_project.get(pid)
            if isinstance(start_ts, datetime) and isinstance(act.created_at, datetime):
                delta = (act.created_at - start_ts).total_seconds() / 3600.0
                if frm and delta >= 0:
                    stage_durations[frm].append(delta)
            prev_ts[pid] = act.created_at

    avg_time_in_stage_hours: dict[str, float] = {}
    for stage in PIPELINE_STAGES:
        values = stage_durations.get(stage, [])
        if values:
            avg_time_in_stage_hours[stage] = round(sum(values) / len(values), 2)
        else:
            avg_time_in_stage_hours[stage] = 0.0

    def _safe_ratio(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    lead_n = len(reached.get("lead", set()))
    quoted_n = len(reached.get("estimate_sent", set()))
    won_n = len(reached.get("won", set()))

    conversion = {
        "lead_to_quoted": _safe_ratio(quoted_n, lead_n),
        "quoted_to_won": _safe_ratio(won_n, quoted_n),
        "overall": _safe_ratio(won_n, lead_n),
    }

    return {
        "stage_counts": stage_counts,
        "avg_time_in_stage_hours": avg_time_in_stage_hours,
        "conversion": conversion,
    }


async def compute_rep_performance(
    db: AsyncSession,
    organization_id: Optional[int],
    period: Period = "all",
) -> list[dict]:
    """Per-user activity inside an organization."""
    cutoff = period_to_cutoff(period)

    user_filter = (
        User.organization_id.is_(None)
        if organization_id is None
        else User.organization_id == organization_id
    )
    users = (await db.execute(select(User).where(user_filter))).scalars().all()

    # Quotes created per user
    est_stmt = select(Estimate.created_by, func.count(Estimate.id)).where(
        Estimate.organization_id.is_(None)
        if organization_id is None
        else Estimate.organization_id == organization_id
    )
    if cutoff is not None:
        est_stmt = est_stmt.where(Estimate.created_at >= cutoff)
    est_stmt = est_stmt.group_by(Estimate.created_by)
    quotes_by_user: dict[int, int] = {}
    for uid, cnt in (await db.execute(est_stmt)).all():
        if uid is not None:
            quotes_by_user[int(uid)] = int(cnt)

    # Won outcomes per user (attributed to the estimate's creator)
    won_stmt = (
        select(
            Estimate.created_by,
            func.count(EstimateOutcome.id),
            func.coalesce(func.sum(EstimateOutcome.final_price), 0.0),
        )
        .join(Estimate, EstimateOutcome.estimate_id == Estimate.id)
        .where(
            EstimateOutcome.outcome == "won",
            EstimateOutcome.organization_id.is_(None)
            if organization_id is None
            else EstimateOutcome.organization_id == organization_id,
        )
    )
    if cutoff is not None:
        won_stmt = won_stmt.where(EstimateOutcome.created_at >= cutoff)
    won_stmt = won_stmt.group_by(Estimate.created_by)
    won_by_user: dict[int, tuple[int, float]] = {}
    for uid, cnt, amt in (await db.execute(won_stmt)).all():
        if uid is not None:
            won_by_user[int(uid)] = (int(cnt), float(amt or 0.0))

    rows: list[dict] = []
    for u in users:
        qc = quotes_by_user.get(u.id, 0)
        wc, wa = won_by_user.get(u.id, (0, 0.0))
        avg = round(wa / wc, 2) if wc else 0.0
        rows.append(
            {
                "user_id": u.id,
                "full_name": u.full_name or u.email,
                "email": u.email,
                "role": u.role,
                "quotes_created": qc,
                "won_count": wc,
                "won_amount": round(wa, 2),
                "avg_deal_size": avg,
            }
        )

    rows.sort(key=lambda r: (-r["won_amount"], -r["quotes_created"], r["user_id"]))
    return rows


async def compute_active_pipeline_value(
    db: AsyncSession,
    organization_id: Optional[int],
) -> float:
    """Sum of grand totals for estimates whose projects are in an in-flight stage.

    Helpful as a StatCard value alongside total-won revenue.
    """
    active_stages = ["lead", "estimate_sent", "in_progress"]
    stmt = (
        select(func.coalesce(func.sum(Estimate.grand_total), 0.0))
        .join(Project, Estimate.project_id == Project.id)
        .where(
            Project.status.in_(active_stages),
            Estimate.organization_id.is_(None)
            if organization_id is None
            else Estimate.organization_id == organization_id,
        )
    )
    result = await db.execute(stmt)
    value = result.scalar() or 0.0
    return float(value)
