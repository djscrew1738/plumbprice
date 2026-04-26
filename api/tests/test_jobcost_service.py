"""Tests for job-cost reconciliation service (Track C5)."""
import datetime as dt

import pytest

from app.models.estimates import Estimate, EstimateLineItem
from app.models.job_costs import EstimateActuals
from app.services.jobcost_service import (
    estimate_variance,
    variance_by_task_code,
)


def _est(**kw):
    """Make an Estimate with sensible totals."""
    base = dict(
        title="t",
        job_type="service",
        labor_total=1000.0,
        materials_total=500.0,
        markup_total=300.0,
        grand_total=1800.0,
        organization_id=1,
    )
    base.update(kw)
    return Estimate(**base)


def test_estimate_variance_no_actuals_marks_unclosed():
    est = _est()
    out = estimate_variance(est, None)
    assert out["has_actuals"] is False
    assert out["labor"]["estimated"] == 1000.0
    assert out["labor"]["actual"] is None
    assert out["labor"]["delta"] is None
    assert out["total_cost"]["estimated"] == 1500.0


def test_estimate_variance_with_overrun():
    est = _est()
    actuals = EstimateActuals(
        estimate_id=1,
        actual_labor_cost=1300.0,    # +300 over
        actual_materials_cost=480.0,  # -20 under
        actual_revenue=1800.0,
    )
    out = estimate_variance(est, actuals)
    assert out["has_actuals"] is True
    assert out["labor"]["delta"] == 300.0
    assert out["labor"]["pct"] == pytest.approx(0.3, abs=1e-6)
    assert out["materials"]["delta"] == -20.0
    assert out["total_cost"]["actual"] == 1780.0
    assert out["total_cost"]["delta"] == 280.0
    # Estimated gross margin = 1800 - 1500 = 300; actual = 1800 - 1780 = 20.
    assert out["gross_margin"]["estimated"] == 300.0
    assert out["gross_margin"]["actual"] == 20.0


def test_safe_div_zero_estimated_returns_none_pct():
    est = _est(labor_total=0.0, materials_total=0.0, grand_total=0.0)
    actuals = EstimateActuals(
        estimate_id=1, actual_labor_cost=100.0, actual_materials_cost=50.0,
    )
    out = estimate_variance(est, actuals)
    # estimated total cost is 0 — pct must be None, not divide-by-zero.
    assert out["total_cost"]["pct"] is None


@pytest.mark.asyncio
async def test_variance_by_task_code_apportions_correctly(db_session):
    """Two estimates each with 2 task-code lines; verify rollup math."""
    closed = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    for est_total_actual_labor in (1100.0, 1100.0, 1100.0):
        # Build estimate: 800 labor + 200 materials = 1000 total cost.
        est = Estimate(
            title="t",
            job_type="service",
            labor_total=800.0,
            materials_total=200.0,
            grand_total=1300.0,
            organization_id=1,
        )
        db_session.add(est)
        await db_session.flush()
        # Two line items: A=600 (60%), B=400 (40%).
        db_session.add(EstimateLineItem(
            estimate_id=est.id, line_type="labor",
            description="A", quantity=1, unit_cost=600, total_cost=600,
            trace_json={"task_code": "A_CODE"},
        ))
        db_session.add(EstimateLineItem(
            estimate_id=est.id, line_type="labor",
            description="B", quantity=1, unit_cost=400, total_cost=400,
            trace_json={"task_code": "B_CODE"},
        ))
        # Actuals: total cost = 1100 (10% over).
        db_session.add(EstimateActuals(
            estimate_id=est.id,
            organization_id=1,
            actual_labor_cost=900.0,
            actual_materials_cost=200.0,
            closed_at=closed,
        ))
    await db_session.commit()

    res = await variance_by_task_code(db_session, organization_id=1, min_n=3)
    by_code = {r["task_code"]: r for r in res}
    assert "A_CODE" in by_code and "B_CODE" in by_code
    a = by_code["A_CODE"]
    assert a["n"] == 3
    # 60% share of 1000 estimated → 600 each, x3 = 1800.
    assert a["estimated_cost"] == pytest.approx(1800.0, abs=1e-2)
    # 60% share of 1100 actual → 660 each, x3 = 1980.
    assert a["actual_cost"] == pytest.approx(1980.0, abs=1e-2)
    assert a["pct"] == pytest.approx(0.10, abs=1e-3)


@pytest.mark.asyncio
async def test_variance_by_task_code_skips_unclosed(db_session):
    est = Estimate(
        title="open",
        job_type="service",
        labor_total=800.0,
        materials_total=200.0,
        grand_total=1300.0,
        organization_id=1,
    )
    db_session.add(est)
    await db_session.flush()
    db_session.add(EstimateLineItem(
        estimate_id=est.id, line_type="labor",
        description="X", quantity=1, unit_cost=600, total_cost=600,
        trace_json={"task_code": "OPEN_ONLY"},
    ))
    db_session.add(EstimateActuals(
        estimate_id=est.id,
        organization_id=1,
        actual_labor_cost=900.0,
        # NB: no closed_at — should be filtered out.
    ))
    await db_session.commit()

    res = await variance_by_task_code(db_session, organization_id=1, min_n=1)
    codes = {r["task_code"] for r in res}
    assert "OPEN_ONLY" not in codes
