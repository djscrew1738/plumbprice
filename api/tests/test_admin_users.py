"""Tests for admin user invite + role CRUD."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.auth import get_current_user
from app.main import app
from app.models.users import User, UserInvite, Organization


BASE = "/api/v1/admin"


@pytest.fixture
def non_admin_user():
    async def override():
        return User(
            id=777,
            email="viewer@example.com",
            full_name="Viewer",
            is_active=True,
            is_admin=False,
            role="viewer",
        )

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def _seed_admin(db_session):
    """Ensure a persisted admin row exists matching the conftest override (id=1)."""
    existing = await db_session.execute(select(User).where(User.id == 1))
    if existing.scalar_one_or_none() is None:
        db_session.add(
            User(
                id=1,
                email="test@example.com",
                full_name="Test User",
                hashed_password="x",
                role="admin",
                is_active=True,
                is_admin=True,
            )
        )
        await db_session.commit()
    yield


# ─── Non-admin access ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_forbidden_for_non_admin(test_client, non_admin_user):
    r = await test_client.post(f"{BASE}/users/invite", json={"email": "a@b.com", "role": "estimator"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_users_forbidden_for_non_admin(test_client, non_admin_user):
    r = await test_client.get(f"{BASE}/users")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_patch_user_forbidden_for_non_admin(test_client, non_admin_user):
    r = await test_client.patch(f"{BASE}/users/1", json={"role": "estimator"})
    assert r.status_code == 403


# ─── Happy paths ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_and_list_invites(test_client, _seed_admin):
    r = await test_client.post(
        f"{BASE}/users/invite",
        json={"email": "newbie@example.com", "role": "estimator", "full_name": "Newbie"},
    )
    assert r.status_code == 200, r.text

    r2 = await test_client.get(f"{BASE}/invites")
    assert r2.status_code == 200
    emails = [inv["email"] for inv in r2.json()]
    assert "newbie@example.com" in emails


@pytest.mark.asyncio
async def test_invite_bad_role_returns_400(test_client, _seed_admin):
    r = await test_client.post(
        f"{BASE}/users/invite",
        json={"email": "x@example.com", "role": "superadmin"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_creates_user(test_client, db_session, _seed_admin):
    r = await test_client.post(
        f"{BASE}/users/invite",
        json={"email": "accept@example.com", "role": "estimator"},
    )
    assert r.status_code == 200

    # Regenerate a known token by creating an invite directly through a second path:
    # We need the raw token — reinject via model.
    import secrets, hashlib
    from datetime import datetime, timedelta, timezone as tz
    import uuid

    raw = secrets.token_urlsafe(32)
    invite = UserInvite(
        id=uuid.uuid4(),
        email="direct@example.com",
        role="admin",
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        invited_by=1,
        expires_at=datetime.now(tz.utc) + timedelta(days=1),
    )
    db_session.add(invite)
    await db_session.commit()

    r2 = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "supersecret123", "full_name": "Direct User"},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["user"]["email"] == "direct@example.com"
    assert data["user"]["role"] == "admin"
    assert data["user"]["is_admin"] is True
    assert data["access_token"]

    # Second accept returns 400 (token consumed)
    r3 = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "another12345"},
    )
    assert r3.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_expired_returns_400(test_client, db_session):
    import secrets, hashlib, uuid
    from datetime import datetime, timedelta, timezone as tz

    raw = secrets.token_urlsafe(32)
    invite = UserInvite(
        id=uuid.uuid4(),
        email="stale@example.com",
        role="estimator",
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(tz.utc) - timedelta(days=1),
    )
    db_session.add(invite)
    await db_session.commit()

    r = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "supersecret123"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_patch_own_role_returns_409(test_client, _seed_admin):
    r = await test_client.patch(f"{BASE}/users/1", json={"role": "estimator"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_demote_last_admin_returns_409(test_client, db_session, _seed_admin):
    # Create another admin via seed — but ensure user id=1 is the only admin in its org (None org)
    # Attempt to deactivate id=1 via DELETE → self-deactivate guard returns 409
    r = await test_client.delete(f"{BASE}/users/1")
    assert r.status_code == 409

    # Also verify patch to is_active=False on the only admin (another user) is blocked.
    other_admin = User(
        email="solo-admin@example.com",
        hashed_password="x",
        full_name="Solo",
        role="admin",
        is_admin=True,
        is_active=True,
        organization_id=5555,  # unique org with one admin
    )
    db_session.add(other_admin)
    await db_session.commit()
    await db_session.refresh(other_admin)

    r2 = await test_client.patch(
        f"{BASE}/users/{other_admin.id}",
        json={"role": "estimator"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_revoke_invite(test_client, db_session, _seed_admin):
    import secrets, hashlib, uuid
    from datetime import datetime, timedelta, timezone as tz

    raw = secrets.token_urlsafe(32)
    invite_id = uuid.uuid4()
    invite = UserInvite(
        id=invite_id,
        email="revokeme@example.com",
        role="estimator",
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(tz.utc) + timedelta(days=1),
    )
    db_session.add(invite)
    await db_session.commit()

    r = await test_client.delete(f"{BASE}/invites/{invite_id}")
    assert r.status_code == 200

    # Token should no longer be acceptable
    r2 = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "supersecret123"},
    )
    assert r2.status_code == 400
