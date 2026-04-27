"""Tests for ChatAttachment endpoints (d1 multi-modal sessions)."""

import pytest
from httpx import AsyncClient

from app.models.sessions import ChatSession, ChatAttachment


@pytest.fixture(autouse=True)
async def _clean(db_session):
    from sqlalchemy import delete
    await db_session.execute(delete(ChatAttachment))
    await db_session.execute(delete(ChatSession))
    await db_session.commit()


async def _make_session(db_session) -> int:
    s = ChatSession(user_id=1, title="leak fix")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s.id


@pytest.mark.asyncio
async def test_list_empty(test_client: AsyncClient, db_session):
    sid = await _make_session(db_session)
    r = await test_client.get(f"/api/v1/sessions/{sid}/attachments")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_attached_photo(test_client: AsyncClient, db_session):
    sid = await _make_session(db_session)
    r = await test_client.post(
        f"/api/v1/sessions/{sid}/attachments",
        json={"kind": "photo", "ref_id": 42, "status": "attached"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "photo"
    assert body["ref_id"] == 42
    assert body["status"] == "attached"
    assert body["session_id"] == sid


@pytest.mark.asyncio
async def test_agent_request_then_fulfill(test_client: AsyncClient, db_session):
    """Agent asks for a photo (status=requested, no ref_id), client uploads and PATCHes."""
    sid = await _make_session(db_session)

    r = await test_client.post(
        f"/api/v1/sessions/{sid}/attachments",
        json={"kind": "photo", "status": "requested", "note": "show me the supply line"},
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    assert r.json()["ref_id"] is None

    r2 = await test_client.patch(
        f"/api/v1/sessions/{sid}/attachments/{aid}",
        json={"ref_id": 7, "status": "attached"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "attached"
    assert r2.json()["ref_id"] == 7


@pytest.mark.asyncio
async def test_invalid_kind_rejected(test_client: AsyncClient, db_session):
    sid = await _make_session(db_session)
    r = await test_client.post(
        f"/api/v1/sessions/{sid}/attachments", json={"kind": "telepathy"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_session_not_found(test_client: AsyncClient):
    r = await test_client.get("/api/v1/sessions/99999/attachments")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_attachment(test_client: AsyncClient, db_session):
    sid = await _make_session(db_session)
    r = await test_client.post(
        f"/api/v1/sessions/{sid}/attachments",
        json={"kind": "voice", "ref_id": 1},
    )
    aid = r.json()["id"]
    r2 = await test_client.delete(f"/api/v1/sessions/{sid}/attachments/{aid}")
    assert r2.status_code == 204
    r3 = await test_client.get(f"/api/v1/sessions/{sid}/attachments")
    assert r3.json() == []
