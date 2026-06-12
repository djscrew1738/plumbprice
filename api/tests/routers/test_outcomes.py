"""Tests for the outcomes router — win/loss tracking and null-org safety."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.auth import get_current_user
from app.main import app
from app.models.estimates import Estimate
from app.models.outcomes import EstimateOutcome
from app.models.users import User

pytestmark = pytest.mark.asyncio

USER_ID = 8001
ORG_ID = 880001


def _org_user() -> User:
    return User(
        id=USER_ID, email="outcomes@x.com", full_name="Outcomes User",
        is_active=True, is_admin=False, organization_id=ORG_ID, role="estimator",
    )


def _null_org_user() -> User:
    return User(
        id=USER_ID + 1, email="null-outcomes@x.com", full_name="Null Org User",
        is_active=True, is_admin=False, organization_id=None, role="estimator",
    )


@pytest_asyncio.fixture(autouse=True)
async def _scope_to_outcomes_org(db_session):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _org_user

    async def _scrub():
        await db_session.execute(
            delete(EstimateOutcome).where(
                EstimateOutcome.estimate_id.in_([801, 802, 803, 804])
            )
        )
        await db_session.execute(
            delete(Estimate).where(Estimate.id.in_([801, 802, 803, 804]))
        )
        await db_session.commit()

    await _scrub()
    try:
        yield
    finally:
        await _scrub()
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


async def _seed_estimate(db, *, estimate_id: int, organization_id: int | None, created_by: int = USER_ID):
    est = Estimate(
        id=estimate_id,
        title=f"Est {estimate_id}",
        job_type="service",
        status="draft",
        grand_total=1000.0,
        organization_id=organization_id,
        created_by=created_by,
    )
    db.add(est)
    await db.commit()
    return est


# ── /outcomes/stats ─────────────────────────────────────────────────────────


async def test_stats_empty_for_org(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/estimates/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["win_rate"] is None
    assert body["confidence_breakdown"] == {}


async def test_stats_null_org_returns_empty(test_client: AsyncClient):
    app.dependency_overrides[get_current_user] = _null_org_user
    try:
        resp = await test_client.get("/api/v1/estimates/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["won"] == 0
        assert body["lost"] == 0
        assert body["win_rate"] is None
        assert body["confidence_breakdown"] == {}
    finally:
        app.dependency_overrides[get_current_user] = _org_user


# ── /outcomes/list ──────────────────────────────────────────────────────────


async def test_list_null_org_scopes_to_created_by(test_client: AsyncClient, db_session):
    # Seed an estimate for the null-org user
    await _seed_estimate(db_session, estimate_id=801, organization_id=None, created_by=USER_ID + 1)
    outcome = EstimateOutcome(
        estimate_id=801,
        outcome="won",
        organization_id=None,
        recorded_by=USER_ID + 1,
    )
    db_session.add(outcome)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = _null_org_user
    try:
        resp = await test_client.get("/api/v1/estimates/list")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["estimate_id"] == 801
    finally:
        app.dependency_overrides[get_current_user] = _org_user


# ── POST /{id}/outcome ─────────────────────────────────────────────────────


async def test_record_outcome_null_org_finds_own_estimate(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=802, organization_id=None, created_by=USER_ID + 1)

    app.dependency_overrides[get_current_user] = _null_org_user
    try:
        resp = await test_client.post(
            "/api/v1/estimates/802/outcome",
            json={"outcome": "won", "final_price": 950.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["outcome"] == "won"
        assert body["final_price"] == 950.0
    finally:
        app.dependency_overrides[get_current_user] = _org_user


async def test_record_outcome_null_org_404_for_other_users_estimate(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=803, organization_id=None, created_by=USER_ID)

    app.dependency_overrides[get_current_user] = _null_org_user
    try:
        resp = await test_client.post(
            "/api/v1/estimates/803/outcome",
            json={"outcome": "won"},
        )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = _org_user
