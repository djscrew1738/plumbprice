"""Tests for the proposal acceptance loop."""
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, Proposal

pytestmark = pytest.mark.asyncio


async def _make_estimate(db_session: AsyncSession, **overrides) -> Estimate:
    est = Estimate(
        title=overrides.get("title", "Acceptance Loop Estimate"),
        job_type="service",
        status="draft",
        labor_total=200.0,
        materials_total=100.0,
        tax_total=24.75,
        markup_total=30.0,
        misc_total=0.0,
        subtotal=330.0,
        grand_total=354.75,
        confidence_score=0.9,
        confidence_label="HIGH",
        assumptions=[],
        sources=[],
        county="Dallas",
        tax_rate=0.0825,
        created_by=1,
        organization_id=overrides.get("organization_id"),
    )
    db_session.add(est)
    await db_session.commit()
    await db_session.refresh(est)
    return est


async def _send(test_client: AsyncClient, estimate_id: int, email: str = "client@example.com") -> dict:
    res = await test_client.post(
        f"/api/v1/proposals/{estimate_id}/send",
        json={"recipient_email": email, "recipient_name": "Jane"},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_send_creates_public_token(test_client, db_session):
    est = await _make_estimate(db_session)
    result = await _send(test_client, est.id)
    assert result["success"] is True
    assert result["public_token"]
    assert result["accept_url"].endswith(f"/p/{result['public_token']}")

    # GET public view returns pending + sets opened_at
    token = result["public_token"]
    r1 = await test_client.get(f"/api/v1/public/proposals/{token}")
    assert r1.status_code == 200
    data = r1.json()
    assert data["status"] in ("sent", "opened")
    assert data["estimate"]["id"] == est.id
    assert data["opened_at"] is not None

    # opened_at persisted
    row = (await db_session.execute(select(Proposal).where(Proposal.public_token == token))).scalar_one()
    assert row.opened_at is not None


async def test_accept_sets_signature_and_is_idempotent(test_client, db_session):
    est = await _make_estimate(db_session)
    sent = await _send(test_client, est.id)
    token = sent["public_token"]

    r = await test_client.post(
        f"/api/v1/public/proposals/{token}/accept",
        json={"signature": "Jane Doe"},
        headers={"User-Agent": "pytest-client/1.0", "X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "accepted"
    assert data["client_signature"] == "Jane Doe"
    assert data["accepted_at"] is not None

    row = (await db_session.execute(select(Proposal).where(Proposal.public_token == token))).scalar_one()
    assert row.client_ip == "10.0.0.1"
    assert row.client_user_agent == "pytest-client/1.0"

    # Double accept → same state (idempotent)
    r2 = await test_client.post(
        f"/api/v1/public/proposals/{token}/accept",
        json={"signature": "Different Name"},
    )
    assert r2.status_code == 200
    assert r2.json()["client_signature"] == "Jane Doe"  # unchanged


async def test_accept_after_decline_conflicts(test_client, db_session):
    est = await _make_estimate(db_session)
    sent = await _send(test_client, est.id)
    token = sent["public_token"]

    d = await test_client.post(f"/api/v1/public/proposals/{token}/decline", json={"reason": "Too expensive"})
    assert d.status_code == 200
    assert d.json()["status"] == "declined"

    # Decline is idempotent
    d2 = await test_client.post(f"/api/v1/public/proposals/{token}/decline", json={})
    assert d2.status_code == 200
    assert d2.json()["status"] == "declined"

    # Accept after decline conflicts
    a = await test_client.post(f"/api/v1/public/proposals/{token}/accept", json={"signature": "Nope"})
    assert a.status_code == 409


async def test_expired_token_returns_404(test_client, db_session):
    est = await _make_estimate(db_session)
    sent = await _send(test_client, est.id)
    token = sent["public_token"]

    # Force expiry in DB
    row = (await db_session.execute(select(Proposal).where(Proposal.public_token == token))).scalar_one()
    row.token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    r = await test_client.get(f"/api/v1/public/proposals/{token}")
    assert r.status_code == 404

    a = await test_client.post(f"/api/v1/public/proposals/{token}/accept", json={"signature": "X"})
    assert a.status_code == 409


async def test_bogus_token_returns_404(test_client):
    r = await test_client.get("/api/v1/public/proposals/not-a-real-token")
    assert r.status_code == 404
