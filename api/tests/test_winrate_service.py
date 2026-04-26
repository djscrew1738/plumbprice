"""Tests for win-rate analytics service (Track C4)."""
import pytest

from app.models.estimates import Estimate, EstimateLineItem
from app.models.outcomes import EstimateOutcome
from app.services.winrate_service import (
    winrate_by_markup_band,
    winrate_by_task_code,
)


async def _seed(db, estimates):
    """Helper: seed (markup_pct, outcome, [task_codes]) tuples.

    markup_pct is given as fraction; we synthesize labor=100, materials=0 so
    markup_total = pct * 100 reproduces it.
    """
    for pct, outcome, codes in estimates:
        est = Estimate(
            title="e",
            job_type="service",
            labor_total=100.0,
            materials_total=0.0,
            markup_total=pct * 100.0,
            organization_id=1,
        )
        db.add(est)
        await db.flush()
        for j, code in enumerate(codes):
            db.add(EstimateLineItem(
                estimate_id=est.id,
                line_type="labor",
                description=f"line {j}",
                quantity=1, unit_cost=1, total_cost=1,
                trace_json={"task_code": code},
            ))
        db.add(EstimateOutcome(
            estimate_id=est.id,
            outcome=outcome,
            organization_id=1,
        ))
    await db.commit()


@pytest.mark.asyncio
async def test_winrate_by_markup_band_in_band_vs_overall(db_session):
    await _seed(db_session, [
        # in-band (target=0.28, ±0.05)
        (0.27, "won", []),
        (0.30, "won", []),
        (0.25, "lost", []),
        # out of band
        (0.10, "won", []),
        (0.50, "lost", []),
    ])
    res = await winrate_by_markup_band(
        db_session, organization_id=1, target_markup_pct=0.28, band_pp=5.0,
    )
    assert res["in_band"]["n"] == 3
    assert res["in_band"]["won"] == 2
    assert res["in_band"]["win_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert res["overall"]["n"] == 5
    assert res["overall"]["win_rate"] == pytest.approx(3 / 5, abs=1e-4)


@pytest.mark.asyncio
async def test_winrate_by_markup_band_empty(db_session):
    res = await winrate_by_markup_band(
        db_session, organization_id=999, target_markup_pct=0.30,
    )
    assert res["in_band"]["n"] == 0
    assert res["in_band"]["win_rate"] is None
    assert res["overall"]["win_rate"] is None


@pytest.mark.asyncio
async def test_winrate_by_task_code_filters_below_min_n(db_session):
    await _seed(db_session, [
        (0.30, "won",  ["TOILET_REPLACE_STANDARD"]),
        (0.30, "won",  ["TOILET_REPLACE_STANDARD"]),
        (0.30, "lost", ["TOILET_REPLACE_STANDARD"]),
        (0.30, "won",  ["KITCHEN_FAUCET_REPLACE"]),  # n=1, below default min_n=3
    ])
    res = await winrate_by_task_code(db_session, organization_id=1, min_n=3)
    codes = {r["task_code"] for r in res}
    assert "TOILET_REPLACE_STANDARD" in codes
    assert "KITCHEN_FAUCET_REPLACE" not in codes
    toilet = next(r for r in res if r["task_code"] == "TOILET_REPLACE_STANDARD")
    assert toilet["n"] == 3
    assert toilet["win_rate"] == pytest.approx(2 / 3, abs=1e-4)


@pytest.mark.asyncio
async def test_winrate_by_task_code_scoped_to_requested(db_session):
    await _seed(db_session, [
        (0.30, "won",  ["A_CODE"]),
        (0.30, "won",  ["A_CODE"]),
        (0.30, "lost", ["A_CODE"]),
        (0.30, "won",  ["B_CODE"]),
        (0.30, "won",  ["B_CODE"]),
        (0.30, "lost", ["B_CODE"]),
    ])
    res = await winrate_by_task_code(
        db_session, organization_id=1, task_codes=["A_CODE"], min_n=3,
    )
    assert {r["task_code"] for r in res} == {"A_CODE"}
