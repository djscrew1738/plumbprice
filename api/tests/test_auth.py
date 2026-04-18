"""Tests for auth endpoints — accept-invite notification."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.notifications import Notification
from app.models.users import User, UserInvite

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def _seed_admin_user(db_session):
    """Ensure the default test admin (id=1) exists in the DB."""
    existing = (
        await db_session.execute(select(User).where(User.id == 1))
    ).scalar_one_or_none()
    if existing is None:
        db_session.add(
            User(
                id=1,
                email="test@example.com",
                full_name="Test Admin",
                hashed_password="x",
                role="admin",
                is_active=True,
                is_admin=True,
            )
        )
        await db_session.commit()


async def _create_invite(
    db_session,
    *,
    email: str,
    role: str = "estimator",
    invited_by: int | None = 1,
) -> str:
    """Insert a UserInvite directly and return the raw token."""
    raw = secrets.token_urlsafe(32)
    invite = UserInvite(
        id=uuid.uuid4(),
        email=email,
        role=role,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        invited_by=invited_by,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(invite)
    await db_session.commit()
    return raw


async def test_accept_invite_notifies_sender(test_client: AsyncClient, db_session):
    """Accepting an invite should create an invite_accepted notification for the sender."""
    raw = await _create_invite(db_session, email="newuser@example.com", role="estimator")

    res = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "Password123!", "full_name": "New User"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["user"]["email"] == "newuser@example.com"

    # Notification should exist for the inviter (user_id=1)
    rows = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == 1,
                Notification.kind == "invite_accepted",
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    assert any(
        "newuser@example.com" in (r.title + (r.body or "")) for r in rows
    )
    assert any(r.link == "/admin?tab=users" for r in rows)


async def test_accept_invite_no_notify_without_invited_by(
    test_client: AsyncClient, db_session
):
    """When invited_by is None, accept-invite still succeeds without notification."""
    raw = await _create_invite(
        db_session, email="orphan@example.com", role="viewer", invited_by=None
    )

    res = await test_client.post(
        "/api/v1/auth/accept-invite",
        json={"token": raw, "password": "Password123!"},
    )
    assert res.status_code == 200, res.text
