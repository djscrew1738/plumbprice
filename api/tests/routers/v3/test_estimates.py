"""Tests for the v3 estimates router — org scoping and access control."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.auth import get_current_user
from app.main import app
from app.models.estimates import Estimate
from app.models.users import User

pytestmark = pytest.mark.asyncio

ORG_ID = 990001
OTHER_ORG_ID = 990002
USER_ID = 9001
TEAMMATE_ID = 9002
OTHER_USER_ID = 9003


def _org_user() -> User:
    return User(
        id=USER_ID, email="v3user@x.com", full_name="V3 User",
        is_active=True, is_admin=False, organization_id=ORG_ID, role="estimator",
    )


def _teammate() -> User:
    return User(
        id=TEAMMATE_ID, email="teammate@x.com", full_name="Teammate",
        is_active=True, is_admin=False, organization_id=ORG_ID, role="estimator",
    )


def _other_org_user() -> User:
    return User(
        id=OTHER_USER_ID, email="other@x.com", full_name="Other Org",
        is_active=True, is_admin=False, organization_id=OTHER_ORG_ID, role="estimator",
    )


@pytest_asyncio.fixture(autouse=True)
async def _scope_to_v3_org(db_session):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _org_user

    async def _scrub():
        await db_session.execute(
            delete(Estimate).where(Estimate.id.in_([901, 902, 903]))
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


async def _seed_estimate(db, *, estimate_id: int, organization_id: int | None, created_by: int):
    est = Estimate(
        id=estimate_id,
        title=f"V3 Est {estimate_id}",
        job_type="service",
        status="draft",
        grand_total=1000.0,
        organization_id=organization_id,
        created_by=created_by,
    )
    db.add(est)
    await db.commit()
    return est


# ── GET /v3/estimates/{id} ─────────────────────────────────────────────────


async def test_get_estimate_v3_creator_can_access(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=901, organization_id=ORG_ID, created_by=USER_ID)

    resp = await test_client.get("/api/v3/estimates/901")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 901


async def test_get_estimate_v3_teammate_can_access(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=902, organization_id=ORG_ID, created_by=TEAMMATE_ID)

    resp = await test_client.get("/api/v3/estimates/902")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 902


async def test_get_estimate_v3_other_org_denied(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=903, organization_id=OTHER_ORG_ID, created_by=OTHER_USER_ID)

    resp = await test_client.get("/api/v3/estimates/903")
    assert resp.status_code == 403


# ── GET /v3/estimates ──────────────────────────────────────────────────────


async def test_list_estimates_v3_includes_teammate_work(test_client: AsyncClient, db_session):
    await _seed_estimate(db_session, estimate_id=901, organization_id=ORG_ID, created_by=USER_ID)
    await _seed_estimate(db_session, estimate_id=902, organization_id=ORG_ID, created_by=TEAMMATE_ID)
    # Other org estimate should not appear
    await _seed_estimate(db_session, estimate_id=903, organization_id=OTHER_ORG_ID, created_by=OTHER_USER_ID)

    resp = await test_client.get("/api/v3/estimates")
    assert resp.status_code == 200
    body = resp.json()
    ids = {e["id"] for e in body}
    assert 901 in ids
    assert 902 in ids
    assert 903 not in ids


async def test_list_estimates_v3_null_org_scopes_to_created_by(test_client: AsyncClient, db_session):
    def null_org_user():
        return User(
            id=USER_ID, email="null-v3@x.com", full_name="Null V3",
            is_active=True, is_admin=False, organization_id=None, role="estimator",
        )

    await _seed_estimate(db_session, estimate_id=901, organization_id=None, created_by=USER_ID)
    await _seed_estimate(db_session, estimate_id=902, organization_id=None, created_by=TEAMMATE_ID)

    app.dependency_overrides[get_current_user] = null_org_user
    try:
        resp = await test_client.get("/api/v3/estimates")
        assert resp.status_code == 200
        body = resp.json()
        ids = {e["id"] for e in body}
        assert 901 in ids
        assert 902 not in ids
    finally:
        app.dependency_overrides[get_current_user] = _org_user
