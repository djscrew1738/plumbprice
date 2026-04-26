"""Job-cost reconciliation service (Track C5).

Compute estimate-vs-actual variance from `EstimateActuals`. Output is shaped
for two surfaces:

* Per-estimate: how badly did this one job miss?
* Roll-up: which task codes consistently bleed margin?
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateLineItem
from app.models.job_costs import EstimateActuals


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _variance_block(estimated: Optional[float], actual: Optional[float]) -> dict:
    """Return {estimated, actual, delta, pct} block. Missing inputs → Nones."""
    if estimated is None and actual is None:
        return {"estimated": None, "actual": None, "delta": None, "pct": None}
    delta = None
    if estimated is not None and actual is not None:
        delta = actual - estimated
    return {
        "estimated": estimated,
        "actual": actual,
        "delta": delta,
        "pct": _safe_div(delta, estimated),
    }


def estimate_variance(est: Estimate, actuals: Optional[EstimateActuals]) -> dict:
    """Compute the variance dict for a single estimate."""
    est_labor = est.labor_total or 0.0
    est_mat = est.materials_total or 0.0
    est_total = est.grand_total or (est_labor + est_mat)

    a_labor = actuals.actual_labor_cost if actuals else None
    a_mat = actuals.actual_materials_cost if actuals else None
    a_sub = actuals.actual_subcontractor_cost if actuals else None
    a_other = actuals.actual_other_cost if actuals else None
    a_revenue = actuals.actual_revenue if actuals else None

    actual_total_cost: Optional[float]
    parts = [p for p in (a_labor, a_mat, a_sub, a_other) if p is not None]
    actual_total_cost = sum(parts) if parts else None

    gross_margin_estimated = est_total - (est_labor + est_mat) if est_total else None
    gross_margin_actual = (
        a_revenue - actual_total_cost
        if a_revenue is not None and actual_total_cost is not None
        else None
    )

    return {
        "estimate_id": est.id,
        "estimate_title": est.title,
        "labor": _variance_block(est_labor, a_labor),
        "materials": _variance_block(est_mat, a_mat),
        "subcontractor": _variance_block(None, a_sub),
        "other": _variance_block(None, a_other),
        "total_cost": _variance_block(est_labor + est_mat, actual_total_cost),
        "revenue": _variance_block(est_total, a_revenue),
        "gross_margin": _variance_block(gross_margin_estimated, gross_margin_actual),
        "actual_labor_hours": actuals.actual_labor_hours if actuals else None,
        "closed_at": actuals.closed_at.isoformat() if actuals and actuals.closed_at else None,
        "has_actuals": actuals is not None,
    }


async def variance_by_task_code(
    db: AsyncSession,
    *,
    organization_id: Optional[int],
    min_n: int = 3,
) -> list[dict]:
    """Aggregate variance by task code across all closed estimates.

    Strategy: for each line item with a task_code (in trace_json), apportion
    the estimate-level cost variance to that task code by the line item's
    share of estimated cost. This is approximate but gives the right signal
    for "which task codes consistently come in over budget".
    """
    stmt = (
        select(Estimate, EstimateActuals, EstimateLineItem)
        .join(EstimateActuals, EstimateActuals.estimate_id == Estimate.id)
        .join(EstimateLineItem, EstimateLineItem.estimate_id == Estimate.id)
        .where(EstimateActuals.closed_at.isnot(None))
    )
    if organization_id is not None:
        stmt = stmt.where(EstimateActuals.organization_id == organization_id)

    rows = (await db.execute(stmt)).all()

    tally: dict[str, dict[str, float]] = {}
    for est, actuals, item in rows:
        trace = item.trace_json if isinstance(item.trace_json, dict) else None
        code = (trace or {}).get("task_code")
        if not code:
            continue
        code = str(code).upper()

        est_total_cost = (est.labor_total or 0.0) + (est.materials_total or 0.0)
        if est_total_cost <= 0:
            continue
        share = (item.total_cost or 0.0) / est_total_cost

        actual_parts = [
            p for p in (
                actuals.actual_labor_cost,
                actuals.actual_materials_cost,
                actuals.actual_subcontractor_cost,
                actuals.actual_other_cost,
            ) if p is not None
        ]
        if not actual_parts:
            continue
        actual_total_cost = sum(actual_parts)

        bucket = tally.setdefault(
            code,
            {"n": 0, "estimated": 0.0, "actual": 0.0, "estimates": set()},
        )
        bucket["estimated"] += share * est_total_cost
        bucket["actual"] += share * actual_total_cost
        bucket["estimates"].add(est.id)

    out: list[dict] = []
    for code, b in tally.items():
        n = len(b["estimates"])  # type: ignore[arg-type]
        if n < min_n:
            continue
        delta = b["actual"] - b["estimated"]
        out.append({
            "task_code": code,
            "n": n,
            "estimated_cost": round(b["estimated"], 2),
            "actual_cost": round(b["actual"], 2),
            "delta": round(delta, 2),
            "pct": round(delta / b["estimated"], 4) if b["estimated"] else None,
        })
    out.sort(key=lambda r: (-(r["pct"] or 0), -r["n"]))
    return out
