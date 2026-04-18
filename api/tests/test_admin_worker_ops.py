"""Tests for admin worker-task observability + manual retry endpoints."""

from __future__ import annotations

import pytest

from app.core.auth import get_current_user
from app.main import app
from app.models.blueprints import BlueprintJob
from app.models.documents import UploadedDocument
from app.models.users import User


BASE = "/api/v1/admin"


@pytest.fixture
def non_admin_user():
    async def override():
        return User(
            id=999,
            email="nonadmin@example.com",
            full_name="Non Admin",
            is_active=True,
            is_admin=False,
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


class _FakeAsyncResult:
    id = "fake-task-id-123"


def _fake_delay(*args, **kwargs):
    return _FakeAsyncResult()


# ─── Non-admin access checks ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_task_state_forbidden_for_non_admin(test_client, non_admin_user):
    resp = await test_client.get(f"{BASE}/tasks/abc")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_tasks_forbidden_for_non_admin(test_client, non_admin_user):
    resp = await test_client.get(f"{BASE}/tasks?status=failed")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_blueprint_retry_forbidden_for_non_admin(test_client, non_admin_user):
    resp = await test_client.post(f"{BASE}/blueprints/1/retry")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_document_retry_forbidden_for_non_admin(test_client, non_admin_user):
    resp = await test_client.post(f"{BASE}/documents/1/retry")
    assert resp.status_code == 403


# ─── Happy paths as admin (conftest override makes current_user admin) ───

@pytest.mark.asyncio
async def test_list_failed_tasks_ok(test_client, db_session):
    bp = BlueprintJob(
        filename="blueprints/a.pdf",
        original_filename="a.pdf",
        storage_path="blueprints/a.pdf",
        status="error",
        processing_error="boom",
    )
    doc = UploadedDocument(
        filename="docs/b.pdf",
        original_filename="b.pdf",
        doc_type="spec",
        storage_path="docs/b.pdf",
        status="error",
        processing_error="bad parse",
    )
    db_session.add_all([bp, doc])
    await db_session.commit()

    resp = await test_client.get(f"{BASE}/tasks?status=failed&limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "count" in data
    types = {item["type"] for item in data["items"]}
    assert {"blueprint", "document"}.issubset(types)
    for item in data["items"]:
        assert set(item.keys()) >= {
            "type",
            "id",
            "original_filename",
            "error",
            "updated_at",
            "task_id",
        }


@pytest.mark.asyncio
async def test_retry_blueprint_non_error_returns_409(test_client, db_session):
    bp = BlueprintJob(
        filename="blueprints/c.pdf",
        original_filename="c.pdf",
        storage_path="blueprints/c.pdf",
        status="complete",
    )
    db_session.add(bp)
    await db_session.commit()
    await db_session.refresh(bp)

    resp = await test_client.post(f"{BASE}/blueprints/{bp.id}/retry")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_document_non_error_returns_409(test_client, db_session):
    doc = UploadedDocument(
        filename="docs/c.pdf",
        original_filename="c.pdf",
        doc_type="spec",
        storage_path="docs/c.pdf",
        status="complete",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    resp = await test_client.post(f"{BASE}/documents/{doc.id}/retry")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_blueprint_not_found(test_client):
    resp = await test_client.post(f"{BASE}/blueprints/987654321/retry")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_blueprint_resets_and_returns_task_id(
    test_client, db_session, monkeypatch
):
    bp = BlueprintJob(
        filename="blueprints/d.pdf",
        original_filename="d.pdf",
        storage_path="blueprints/d.pdf",
        status="error",
        processing_error="oops",
    )
    db_session.add(bp)
    await db_session.commit()
    await db_session.refresh(bp)
    await db_session.close()

    import worker.tasks.blueprint_analysis as ba

    monkeypatch.setattr(ba.analyze_blueprint, "delay", _fake_delay)

    from app.routers import admin as admin_router

    async def fake_lock(lock_key: str) -> bool:
        return True

    monkeypatch.setattr(admin_router, "_acquire_retry_lock", fake_lock)

    resp = await test_client.post(f"{BASE}/blueprints/{bp.id}/retry")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["task_id"] == "fake-task-id-123"
    assert data["status"] == "pending"
    assert data["job_id"] == bp.id


@pytest.mark.asyncio
async def test_retry_document_resets_and_returns_task_id(
    test_client, db_session, monkeypatch
):
    doc = UploadedDocument(
        filename="docs/d.pdf",
        original_filename="d.pdf",
        doc_type="spec",
        storage_path="docs/d.pdf",
        status="error",
        processing_error="bad",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    await db_session.close()

    import worker.tasks.document_processing as dp

    monkeypatch.setattr(dp.process_document, "delay", _fake_delay)

    from app.routers import admin as admin_router

    async def fake_lock(lock_key: str) -> bool:
        return True

    monkeypatch.setattr(admin_router, "_acquire_retry_lock", fake_lock)

    resp = await test_client.post(f"{BASE}/documents/{doc.id}/retry")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["task_id"] == "fake-task-id-123"
    assert data["status"] == "pending"
    assert data["document_id"] == doc.id


@pytest.mark.asyncio
async def test_retry_blueprint_lock_held_returns_409(
    test_client, db_session, monkeypatch
):
    bp = BlueprintJob(
        filename="blueprints/e.pdf",
        original_filename="e.pdf",
        storage_path="blueprints/e.pdf",
        status="error",
        processing_error="oops",
    )
    db_session.add(bp)
    await db_session.commit()
    await db_session.refresh(bp)

    from app.routers import admin as admin_router

    async def fake_lock(lock_key: str) -> bool:
        return False

    monkeypatch.setattr(admin_router, "_acquire_retry_lock", fake_lock)

    resp = await test_client.post(f"{BASE}/blueprints/{bp.id}/retry")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_task_state_returns_shape(test_client):
    resp = await test_client.get(f"{BASE}/tasks/some-unknown-id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "some-unknown-id"
    assert "state" in data
    assert "retries" in data
    assert "result_summary" in data
    assert "traceback_excerpt" in data
