"""Tests for password reset flow (forgot-password / reset-password).

State-mutation convention: all DB state is created via HTTP endpoints to avoid
the SQLite test pool greenlet issue. The raw reset token is made deterministic
by monkey-patching `secrets.token_urlsafe`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core import rate_limit
from app.routers import auth as auth_router

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str, password: str = "Password123!") -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Reset Tester"},
    )
    assert resp.status_code == 200, resp.text


async def _mint_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    email: str,
    raw: str,
) -> None:
    """Trigger forgot-password with a deterministic raw token value."""
    monkeypatch.setattr(auth_router.secrets, "token_urlsafe", lambda n=32: raw)
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200, resp.text
    monkeypatch.undo()


@pytest.fixture(autouse=True)
def _clear_rate_limit_state(monkeypatch: pytest.MonkeyPatch):
    # Force the local fallback path so tests don't depend on a live Redis and
    # don't leak counts across runs via Redis TTLs.
    monkeypatch.setattr(rate_limit, "_redis_client", lambda: None)
    rate_limit._local_counts.clear()
    yield
    rate_limit._local_counts.clear()


async def test_forgot_password_known_email_returns_200(test_client: AsyncClient):
    await _register(test_client, "reset.known@example.com")
    resp = await test_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset.known@example.com"},
    )
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower()


async def test_forgot_password_unknown_email_no_leak(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "does-not-exist@example.com"},
    )
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower()


async def test_forgot_password_rate_limited_after_three(test_client: AsyncClient):
    email = "reset.ratelimit@example.com"
    await _register(test_client, email)
    for _ in range(3):
        r = await test_client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
    r4 = await test_client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r4.status_code == 429


async def test_reset_password_with_valid_token(
    test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    email = "reset.valid@example.com"
    await _register(test_client, email, password="OldPassword1!")
    raw = "unit-test-raw-token-value-abcdef1234567890"
    await _mint_token(test_client, monkeypatch, email, raw)

    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": "NewPassword2@"},
    )
    assert resp.status_code == 200, resp.text

    old_login = await test_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "OldPassword1!"},
    )
    assert old_login.status_code == 401

    new_login = await test_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "NewPassword2@"},
    )
    assert new_login.status_code == 200
    assert new_login.json().get("access_token")


async def test_reset_password_bogus_token(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally-not-a-real-token-xxxxxxxxxxxx", "new_password": "NewPassword2@"},
    )
    assert resp.status_code == 400


async def test_reset_password_expired_token(
    test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    email = "reset.expired@example.com"
    await _register(test_client, email)

    # Force the token TTL to be negative so the minted token is already expired.
    monkeypatch.setattr(
        auth_router, "PASSWORD_RESET_TOKEN_TTL", timedelta(minutes=-5)
    )
    raw = "expired-raw-token-abcdefghijklmnop"
    await _mint_token(test_client, monkeypatch, email, raw)
    monkeypatch.setattr(
        auth_router, "PASSWORD_RESET_TOKEN_TTL", timedelta(hours=1)
    )

    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": "NewPassword2@"},
    )
    assert resp.status_code == 400


async def test_reset_password_reused_token(
    test_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    email = "reset.reused@example.com"
    await _register(test_client, email, password="OldPassword1!")
    raw = "reuse-raw-token-abcdefghijklmnop"
    await _mint_token(test_client, monkeypatch, email, raw)

    first = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": "NewPassword2@"},
    )
    assert first.status_code == 200

    second = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": "AnotherOne3#"},
    )
    assert second.status_code == 400


async def test_reset_password_enforces_min_length(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "anything-longer-than-ten-characters", "new_password": "short"},
    )
    assert resp.status_code == 422
