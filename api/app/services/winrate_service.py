"""Win-rate analytics service (Track C4).

Surfaces *historical* win-rate context to estimators while they price work.
Never auto-adjusts — purely informational.

Two slices:

* By markup band — for the current estimate's markup-%, what was our
  historical win-rate in nearby bands (±5 pp)?
* By task code — for each task code on the estimate, what's our historical
  win-rate? (Pulled from `trace_json["task_code"]` on line items.)
"""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateLineItem
from app.models.outcomes import EstimateOutcome


# Markup-% band width (in percentage points) used for the "near my markup"
# rollup. A 5pp band means: if you're quoting 28%, we look at 23%–33% history.
DEFAULT_BAND_PP = 5.0


def _markup_pct(est: Estimate) -> Optional[float]:
    """Return markup as a fraction of cost, or None if it can't be computed."""
    cost = (est.labor_total or 0.0) + (est.materials_total or 0.0)
    if cost <= 0 or est.markup_total is None:
        return None
    return est.markup_total / cost


async def winrate_by_markup_band(
    db: AsyncSession,
    *,
    organization_id: Optional[int],
    target_markup_pct: float,
    band_pp: float = DEFAULT_BAND_PP,
) -> dict:
    """Win rate among decided (won/lost) estimates within ±band_pp of the target."""
    stmt = (
        select(Estimate, EstimateOutcome.outcome)
        .join(EstimateOutcome, EstimateOutcome.estimate_id == Estimate.id)
        .where(EstimateOutcome.outcome.in_(["won", "lost"]))
    )
    if organization_id is not None:
        stmt = stmt.where(EstimateOutcome.organization_id == organization_id)

    rows = (await db.execute(stmt)).all()

    band_lo = target_markup_pct - band_pp / 100.0
    band_hi = target_markup_pct + band_pp / 100.0

    in_band_won = in_band_lost = 0
    overall_won = overall_lost = 0
    for est, outcome in rows:
        pct = _markup_pct(est)
        if pct is None:
            continue
        if outcome == "won":
            overall_won += 1
            if band_lo <= pct <= band_hi:
                in_band_won += 1
        elif outcome == "lost":
            overall_lost += 1
            if band_lo <= pct <= band_hi:
                in_band_lost += 1

    in_band_n = in_band_won + in_band_lost
    overall_n = overall_won + overall_lost
    return {
        "target_markup_pct": round(target_markup_pct, 4),
        "band_pp": band_pp,
        "band_lo_pct": round(band_lo, 4),
        "band_hi_pct": round(band_hi, 4),
        "in_band": {
            "n": in_band_n,
            "won": in_band_won,
            "lost": in_band_lost,
            "win_rate": round(in_band_won / in_band_n, 4) if in_band_n else None,
        },
        "overall": {
            "n": overall_n,
            "won": overall_won,
            "lost": overall_lost,
            "win_rate": round(overall_won / overall_n, 4) if overall_n else None,
        },
    }


async def winrate_by_task_code(
    db: AsyncSession,
    *,
    organization_id: Optional[int],
    task_codes: Optional[Iterable[str]] = None,
    min_n: int = 3,
) -> list[dict]:
    """Per-task-code win-rate rollup.

    `task_code` is read from each line item's `trace_json["task_code"]`.
    Codes with fewer than `min_n` decided estimates are filtered out (too
    noisy to surface as guidance).
    """
    stmt = (
        select(EstimateLineItem.trace_json, EstimateOutcome.outcome)
        .join(Estimate, Estimate.id == EstimateLineItem.estimate_id)
        .join(EstimateOutcome, EstimateOutcome.estimate_id == Estimate.id)
        .where(EstimateOutcome.outcome.in_(["won", "lost"]))
    )
    if organization_id is not None:
        stmt = stmt.where(EstimateOutcome.organization_id == organization_id)

    rows = (await db.execute(stmt)).all()

    requested = {c.upper() for c in (task_codes or [])}
    tally: dict[str, dict[str, int]] = {}
    for trace, outcome in rows:
        if not isinstance(trace, dict):
            continue
        code = trace.get("task_code")
        if not code:
            continue
        code = str(code).upper()
        if requested and code not in requested:
            continue
        bucket = tally.setdefault(code, {"won": 0, "lost": 0})
        if outcome == "won":
            bucket["won"] += 1
        elif outcome == "lost":
            bucket["lost"] += 1

    out: list[dict] = []
    for code, b in tally.items():
        n = b["won"] + b["lost"]
        if n < min_n:
            continue
        out.append({
            "task_code": code,
            "n": n,
            "won": b["won"],
            "lost": b["lost"],
            "win_rate": round(b["won"] / n, 4) if n else None,
        })
    out.sort(key=lambda r: (-r["n"], r["task_code"]))
    return out
