"""Tests for pricing_adjustment_service."""
import pytest
from sqlalchemy import select, delete

from app.services.pricing_adjustment_service import PricingAdjustmentService
from app.models.pricing_intelligence import PricingAdjustment


@pytest.mark.asyncio
async def test_get_labor_multiplier_empty():
    svc = PricingAdjustmentService()
    assert svc.get_labor_multiplier("WH_40G_GAS_STANDARD") == 1.0


@pytest.mark.asyncio
async def test_refresh_and_lookup(db_session):
    svc = PricingAdjustmentService()

    # Seed adjustments
    db_session.add(PricingAdjustment(
        adjustment_type="labor_hours_multiplier",
        target_type="task_code",
        target_key="WH_40G_GAS_STANDARD",
        adjustment_value=1.15,
        is_active=True,
    ))
    db_session.add(PricingAdjustment(
        adjustment_type="material_markup_override",
        target_type="job_type",
        target_key="service",
        adjustment_value=0.35,
        is_active=True,
    ))
    db_session.add(PricingAdjustment(
        adjustment_type="overhead_adder",
        target_type="task_code",
        target_key="WH_40G_GAS_STANDARD",
        adjustment_value=25.0,
        is_active=True,
    ))
    await db_session.commit()

    await svc.refresh_cache(db_session)

    assert svc.get_labor_multiplier("WH_40G_GAS_STANDARD") == 1.15
    assert svc.get_labor_multiplier("UNKNOWN_TASK") == 1.0

    markup = svc.get_material_markup_override("service")
    assert markup == 0.35
    assert svc.get_material_markup_override("construction") is None

    overhead = svc.get_overhead_adder("WH_40G_GAS_STANDARD")
    assert overhead == 25.0
    assert svc.get_overhead_adder("UNKNOWN_TASK") == 0.0

    # Cleanup
    await db_session.execute(delete(PricingAdjustment))
    await db_session.commit()


@pytest.mark.asyncio
async def test_apply_labor_adjustment():
    svc = PricingAdjustmentService()
    svc._labor_adjustments = {
        "WH_40G_GAS_STANDARD": [{"adjustment_value": 1.10}],
    }
    assert svc.apply_labor_adjustment(400.0, "WH_40G_GAS_STANDARD") == 440.0
    assert svc.apply_labor_adjustment(400.0, "UNKNOWN") == 400.0


@pytest.mark.asyncio
async def test_apply_material_markup_override():
    svc = PricingAdjustmentService()
    svc._job_type_adjustments = {
        "service": [{"adjustment_type": "material_markup_override", "adjustment_value": 0.30}],
    }
    assert svc.apply_material_markup_override(0.25, "service") == 0.30
    assert svc.apply_material_markup_override(0.25, "construction") == 0.25
