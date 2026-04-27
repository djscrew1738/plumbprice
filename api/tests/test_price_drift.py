"""Tests for supplier price drift detection (c2-dfw-intelligence)."""
from datetime import datetime, timedelta, timezone

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.services.price_drift import detect_price_drifts, price_history_for_product

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def _clean_supplier_tables(db_session: AsyncSession):
    await db_session.execute(delete(SupplierPriceHistory))
    await db_session.execute(delete(SupplierProduct))
    await db_session.execute(delete(Supplier))
    await db_session.commit()
    yield


async def _supplier(db: AsyncSession, name: str | None = None) -> Supplier:
    name = name or f"Ferguson-{uuid.uuid4().hex[:8]}"
    s = Supplier(name=name, slug=name.lower().replace(" ", "-"), type="wholesale")
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _product(
    db: AsyncSession, supplier: Supplier, *, current_cost: float, canonical: str = "pex_3_4"
) -> SupplierProduct:
    await db.refresh(supplier)
    p = SupplierProduct(
        supplier_id=supplier.id,
        canonical_item=canonical,
        sku=f"sku-{canonical}",
        name=f"{canonical.upper()} pipe",
        cost=current_cost,
        is_active=True,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _history(
    db: AsyncSession, product: SupplierProduct, *, cost: float, days_ago: int
) -> None:
    # product attributes may be expired after a prior commit() — refresh
    # to ensure .id is available without an async lazy-load mid-execute.
    await db.refresh(product)
    from sqlalchemy import insert
    recorded_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    await db.execute(
        insert(SupplierPriceHistory).values(
            product_id=product.id, cost=cost, recorded_at=recorded_at, source="test"
        )
    )
    await db.commit()


async def test_no_drifts_when_no_products(db_session):
    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert drifts == []


async def test_drift_detected_above_threshold_up(db_session):
    s = await _supplier(db_session, name="Ferguson DFW")
    p = await _product(db_session, s, current_cost=120.0)  # +20% from 100
    await _history(db_session, p, cost=100.0, days_ago=45)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert len(drifts) == 1
    d = drifts[0]
    assert d.product_id == p.id
    assert d.direction == "up"
    assert abs(d.delta_pct - 0.2) < 1e-6
    assert d.current_cost == 120.0
    assert d.baseline_cost == 100.0
    assert d.supplier_name == "Ferguson DFW"


async def test_drift_detected_below_threshold_skipped(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=110.0)  # +10%
    await _history(db_session, p, cost=100.0, days_ago=45)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert drifts == []


async def test_downward_drift_also_flagged(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=80.0)  # -20%
    await _history(db_session, p, cost=100.0, days_ago=45)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert len(drifts) == 1
    assert drifts[0].direction == "down"
    assert drifts[0].delta_pct < 0


async def test_skips_products_without_baseline(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=200.0)
    # Baseline only 5 days ago — too recent to count for a 30-day lookback.
    await _history(db_session, p, cost=100.0, days_ago=5)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert drifts == []


async def test_inactive_products_excluded(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=200.0)
    p.is_active = False
    await db_session.commit()
    await _history(db_session, p, cost=100.0, days_ago=45)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert drifts == []


async def test_results_sorted_by_abs_delta_desc(db_session):
    s = await _supplier(db_session)
    p1 = await _product(db_session, s, current_cost=120.0, canonical="a")  # +20%
    p2 = await _product(db_session, s, current_cost=200.0, canonical="b")  # +100%
    p3 = await _product(db_session, s, current_cost=50.0, canonical="c")  # -50%
    await _history(db_session, p1, cost=100.0, days_ago=45)
    await _history(db_session, p2, cost=100.0, days_ago=45)
    await _history(db_session, p3, cost=100.0, days_ago=45)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert [d.product_id for d in drifts] == [p2.id, p3.id, p1.id]


async def test_uses_most_recent_baseline_at_or_before_cutoff(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=130.0)
    # Two old prices — the more recent (still past cutoff) should win.
    await _history(db_session, p, cost=100.0, days_ago=120)
    await _history(db_session, p, cost=110.0, days_ago=45)
    # And one newer than cutoff (must be ignored)
    await _history(db_session, p, cost=125.0, days_ago=10)

    drifts = await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0.15)
    assert len(drifts) == 1
    assert drifts[0].baseline_cost == 110.0
    assert abs(drifts[0].delta_pct - (130 - 110) / 110) < 1e-3


async def test_history_for_product_returns_chronological_series(db_session):
    s = await _supplier(db_session)
    p = await _product(db_session, s, current_cost=100.0)
    await _history(db_session, p, cost=80.0, days_ago=60)
    await _history(db_session, p, cost=90.0, days_ago=30)
    await _history(db_session, p, cost=100.0, days_ago=5)
    # Out-of-window
    await _history(db_session, p, cost=70.0, days_ago=200)

    await db_session.refresh(p)
    series = await price_history_for_product(db_session, p.id, lookback_days=90)
    assert [pt["cost"] for pt in series] == [80.0, 90.0, 100.0]
    assert all(pt["recorded_at"] for pt in series)


async def test_threshold_validation(db_session):
    with pytest.raises(ValueError):
        await detect_price_drifts(db_session, lookback_days=30, threshold_pct=0)
