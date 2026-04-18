"""Tests for the per-user notification inbox."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.notifications import Notification
from app.models.users import User
from app.models.estimates import Estimate, Proposal
from app.services.notifications_service import notify
from app.core.auth import get_current_user
from app.main import app

pytestmark = pytest.mark.asyncio


async def test_notify_helper_creates_row(db_session):
    n = await notify(
        db=db_session,
        user_id=1,
        kind="system",
        title="Hello",
        body="World",
        link="/x",
    )
    assert n is not None
    nid = n.id
    await db_session.commit()
    row = (await db_session.execute(select(Notification).where(Notification.id == nid))).scalar_one()
    assert row.user_id == 1
    assert row.kind == "system"
    assert row.read_at is None


async def test_list_and_unread_count(test_client: AsyncClient, db_session):
    db_session.add(Notification(user_id=1, kind="system", title="A", body="a"))
    db_session.add(Notification(user_id=1, kind="system", title="B", body="b"))
    await db_session.commit()

    res = await test_client.get("/api/v1/notifications?limit=10")
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) >= 2
    assert all(it["read_at"] is None for it in items[:2])

    res = await test_client.get("/api/v1/notifications/unread-count")
    assert res.status_code == 200
    assert res.json()["count"] >= 2


async def test_mark_read_by_ids_and_unread_filter(test_client: AsyncClient, db_session):
    a = Notification(user_id=1, kind="system", title="A")
    b = Notification(user_id=1, kind="system", title="B")
    db_session.add_all([a, b])
    await db_session.commit()
    await db_session.refresh(a)
    await db_session.refresh(b)

    res = await test_client.post(
        "/api/v1/notifications/mark-read", json={"ids": [a.id]}
    )
    assert res.status_code == 200
    assert res.json()["updated"] == 1

    res = await test_client.get("/api/v1/notifications?unread_only=true&limit=50")
    ids = [it["id"] for it in res.json()]
    assert a.id not in ids
    assert b.id in ids

    res = await test_client.post("/api/v1/notifications/mark-read", json={"all": True})
    assert res.status_code == 200
    res = await test_client.get("/api/v1/notifications/unread-count")
    assert res.json()["count"] == 0


async def test_user_isolation(test_client: AsyncClient, db_session):
    other = Notification(user_id=999, kind="system", title="Not for you")
    db_session.add(other)
    await db_session.commit()

    res = await test_client.get("/api/v1/notifications?limit=100")
    assert res.status_code == 200
    titles = [it["title"] for it in res.json()]
    assert "Not for you" not in titles


async def test_accept_flow_notifies_sender(test_client: AsyncClient, db_session):
    est = Estimate(
        title="Notify Me Estimate",
        job_type="service",
        status="draft",
        subtotal=100.0,
        grand_total=100.0,
        created_by=1,
    )
    db_session.add(est)
    await db_session.commit()
    await db_session.refresh(est)

    # Default test user (id=1, admin) sends the proposal.
    res = await test_client.post(
        f"/api/v1/proposals/{est.id}/send",
        json={"recipient_email": "client@example.com", "recipient_name": "Client"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["public_token"]

    # Verify the proposal's created_by was set to the sender.
    prop = (
        await db_session.execute(select(Proposal).where(Proposal.public_token == token))
    ).scalar_one()
    assert prop.created_by == 1

    # Public accept as unauthenticated.
    res = await test_client.post(
        f"/api/v1/public/proposals/{token}/accept",
        json={"signature": "John Doe"},
    )
    assert res.status_code == 200, res.text

    # Notification row should exist for the sender.
    rows = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == 1,
                Notification.kind == "proposal_accepted",
            )
        )
    ).scalars().all()
    assert len(rows) >= 1
    assert str(est.id) in (rows[0].link or "")
