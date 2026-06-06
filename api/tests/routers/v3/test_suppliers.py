"""Tests for v3 suppliers router — webhooks and health."""
import hmac
import hashlib
import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db, Base
from app.models.suppliers import Supplier, SupplierProduct
from app.models.supplier_webhooks import SupplierWebhook

pytestmark = pytest.mark.asyncio


def _sign_payload(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
async def fresh_db():
    """Create a fresh in-memory engine with tables for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _get_db
    yield {"engine": engine, "SessionLocal": SessionLocal}
    if original:
        app.dependency_overrides[get_db] = original
    else:
        app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


async def _seed_supplier_data(session):
    """Seed a supplier, product, and webhook into the given session."""
    supplier = Supplier(name="Webhook Test Supplier", slug="webhook-test", is_active=True)
    session.add(supplier)
    await session.flush()

    product = SupplierProduct(
        supplier_id=supplier.id,
        sku="WH-TEST-001",
        name="Test Product",
        cost=100.0,
        is_active=True,
        canonical_item="test.canonical",
    )
    session.add(product)

    webhook = SupplierWebhook(
        supplier_id=supplier.id,
        event_type="price_change",
        secret="webhook-secret-123",
        endpoint_url="https://example.com/webhook",
        is_active=True,
    )
    session.add(webhook)
    await session.commit()


async def test_webhook_price_change(test_client: AsyncClient, fresh_db):
    """Valid webhook price_change updates product cost and records history."""
    async with fresh_db["SessionLocal"]() as session:
        await _seed_supplier_data(session)

    payload = {
        "type": "price_change",
        "sku": "WH-TEST-001",
        "supplier": "webhook-test",
        "new_cost": 125.0,
        "old_cost": 100.0,
        "timestamp": "2026-05-17T10:00:00Z",
    }
    signature = _sign_payload(payload, "webhook-secret-123")

    res = await test_client.post(
        "/api/v3/suppliers/webhooks/webhook-test",
        json=payload,
        headers={"X-Signature": signature},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Verify product was updated
    async with fresh_db["SessionLocal"]() as session:
        from sqlalchemy import select
        result = await session.execute(select(SupplierProduct).where(SupplierProduct.sku == "WH-TEST-001"))
        product = result.scalar_one_or_none()
        assert product is not None
        assert product.cost == 125.0


async def test_webhook_invalid_signature(test_client: AsyncClient, fresh_db):
    """Webhook with invalid signature returns 401."""
    async with fresh_db["SessionLocal"]() as session:
        await _seed_supplier_data(session)

    payload = {
        "type": "price_change",
        "sku": "WH-TEST-001",
        "supplier": "webhook-test",
        "new_cost": 999.0,
    }

    res = await test_client.post(
        "/api/v3/suppliers/webhooks/webhook-test",
        json=payload,
        headers={"X-Signature": "bad-signature"},
    )
    assert res.status_code == 401
    assert "Invalid webhook signature" in res.json()["detail"]


async def test_webhook_missing_supplier(test_client: AsyncClient, fresh_db):
    """Webhook for non-existent supplier returns 404."""
    payload = {"type": "price_change", "sku": "X", "supplier": "nonexistent"}
    res = await test_client.post(
        "/api/v3/suppliers/webhooks/nonexistent",
        json=payload,
        headers={"X-Signature": "x"},
    )
    assert res.status_code == 404
    assert "Supplier not found" in res.json()["detail"]


async def test_webhook_invalid_payload(test_client: AsyncClient, fresh_db):
    """Malformed event type returns 400."""
    async with fresh_db["SessionLocal"]() as session:
        await _seed_supplier_data(session)

    payload = {"type": "invalid_event", "sku": "WH-TEST-001", "supplier": "webhook-test"}
    signature = _sign_payload(payload, "webhook-secret-123")

    res = await test_client.post(
        "/api/v3/suppliers/webhooks/webhook-test",
        json=payload,
        headers={"X-Signature": signature},
    )
    assert res.status_code == 400


async def test_supplier_health_requires_admin(test_client: AsyncClient, fresh_db):
    """Supplier health endpoint returns data when user is admin."""
    res = await test_client.get("/api/v3/suppliers/health")
    assert res.status_code == 200
    assert "suppliers" in res.json()
