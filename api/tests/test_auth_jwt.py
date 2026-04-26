"""b3c — Auth integration tests: token expiry, invalid signatures, RBAC.

These tests exercise the JWT layer directly (no DB needed) plus the
HTTP-level auth dependency by temporarily un-overriding `get_current_user`
so the real JWT decoder runs against the test database.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.core.auth import (
    create_access_token,
    decode_token,
    get_current_admin,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.config import settings
from app.main import app
from app.models.users import User

# asyncio_mode='auto' in pyproject.toml auto-marks async functions; no
# module-level pytestmark needed.


# ─── unit: token round-trip ────────────────────────────────────────────────

def test_create_and_decode_token_roundtrip():
    """A freshly issued token decodes back to its original claims."""
    token = create_access_token({"sub": "42"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_decode_expired_token_raises_401():
    """A token issued in the past must be rejected as 401."""
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as excinfo:
        decode_token(token)
    assert excinfo.value.status_code == 401


def test_decode_invalid_signature_raises_401():
    """A token signed with a different key must be rejected as 401."""
    import jose.jwt as jwt
    bogus = jwt.encode({"sub": "42"}, "different-secret", algorithm=settings.algorithm)
    with pytest.raises(HTTPException) as excinfo:
        decode_token(bogus)
    assert excinfo.value.status_code == 401


def test_decode_garbage_token_raises_401():
    """A non-JWT string must be rejected as 401, not crash."""
    with pytest.raises(HTTPException) as excinfo:
        decode_token("not.a.token")
    assert excinfo.value.status_code == 401


# ─── unit: password hashing ────────────────────────────────────────────────

def test_password_hash_verifies():
    """Hashed password verifies against the original; tampered does not."""
    h = get_password_hash("hunter2")
    assert verify_password("hunter2", h) is True
    assert verify_password("wrong", h) is False


# ─── integration: HTTP-level auth ─────────────────────────────────────────

@pytest.fixture
def real_auth():
    """Temporarily restore the real get_current_user dependency.

    The conftest pins it to admin id=1; some tests need the JWT path.
    """
    saved = app.dependency_overrides.pop(get_current_user, None)
    yield
    if saved is not None:
        app.dependency_overrides[get_current_user] = saved


async def test_protected_route_no_token_returns_401(test_client: AsyncClient, real_auth):
    """Hitting a protected endpoint without a token should 401."""
    res = await test_client.get("/api/v1/auth/me")
    assert res.status_code == 401


async def test_protected_route_invalid_token_returns_401(
    test_client: AsyncClient, real_auth
):
    """Bearer header with junk token → 401."""
    res = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert res.status_code == 401


async def test_protected_route_expired_token_returns_401(
    test_client: AsyncClient, real_auth
):
    """Bearer header with expired token → 401."""
    expired = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))
    res = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert res.status_code == 401


async def test_protected_route_valid_token_returns_user(
    test_client: AsyncClient, db_session, real_auth
):
    """Valid token for a real user → 200 with that user's profile."""
    user = User(
        email="alice@example.com",
        full_name="Alice",
        hashed_password=get_password_hash("pw"),
        role="estimator",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    res = await test_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "alice@example.com"


async def test_protected_route_inactive_user_returns_400(
    test_client: AsyncClient, db_session, real_auth
):
    """Token for a deactivated user → 400 inactive (not 200)."""
    user = User(
        email="ghost@example.com",
        full_name="Ghost",
        hashed_password=get_password_hash("pw"),
        role="estimator",
        is_active=False,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    res = await test_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 400


# ─── integration: RBAC admin gate ─────────────────────────────────────────

async def test_admin_gate_rejects_non_admin():
    """get_current_admin must raise 403 when current user is not admin."""
    non_admin = User(
        id=999,
        email="user@example.com",
        full_name="Regular User",
        hashed_password="x",
        role="estimator",
        is_active=True,
        is_admin=False,
    )
    with pytest.raises(HTTPException) as excinfo:
        await get_current_admin(current_user=non_admin)
    assert excinfo.value.status_code == 403


async def test_admin_gate_passes_admin():
    """get_current_admin returns the user unchanged when they are admin."""
    admin = User(
        id=1,
        email="boss@example.com",
        full_name="Boss",
        hashed_password="x",
        role="admin",
        is_active=True,
        is_admin=True,
    )
    result = await get_current_admin(current_user=admin)
    assert result is admin
