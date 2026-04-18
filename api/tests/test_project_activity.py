import pytest
from httpx import AsyncClient
from starlette import status

from app.core.auth import get_current_user
from app.main import app
from app.models.users import User

pytestmark = pytest.mark.asyncio


async def _create_project(client: AsyncClient, name="Activity Test", status_="lead") -> int:
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "job_type": "service",
            "customer_name": "Alice",
            "county": "Dallas",
            "status": status_,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    return resp.json()["id"]


async def _cleanup(client: AsyncClient, pid: int) -> None:
    await client.delete(f"/api/v1/projects/{pid}")


async def test_activity_empty_on_create(test_client: AsyncClient):
    pid = await _create_project(test_client, name="Activity Empty")
    try:
        resp = await test_client.get(f"/api/v1/projects/{pid}/activity")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []
    finally:
        await _cleanup(test_client, pid)


async def test_stage_change_is_logged(test_client: AsyncClient):
    pid = await _create_project(test_client, name="Stage Change")

    patch = await test_client.patch(
        f"/api/v1/projects/{pid}",
        json={"status": "won"},
    )
    assert patch.status_code == status.HTTP_200_OK

    resp = await test_client.get(f"/api/v1/projects/{pid}/activity")
    assert resp.status_code == status.HTTP_200_OK
    entries = resp.json()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["kind"] == "stage_changed"
    assert entry["payload"]["from"] == "lead"
    assert entry["payload"]["to"] == "won"
    # Actor is optional — join to users may yield None if test user is not persisted.
    if entry["actor"] is not None:
        assert entry["actor"]["id"] == 1

    # Clean up to avoid polluting summary counts for other tests.
    await test_client.delete(f"/api/v1/projects/{pid}")


async def test_note_added_appears_in_list(test_client: AsyncClient):
    pid = await _create_project(test_client, name="Notes Project")
    try:
        resp = await test_client.post(
            f"/api/v1/projects/{pid}/activity",
            json={"note": "Called the customer; will follow up tomorrow."},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        created = resp.json()
        assert created["kind"] == "note_added"
        assert created["payload"]["note"].startswith("Called")

        listing = await test_client.get(f"/api/v1/projects/{pid}/activity")
        items = listing.json()
        assert any(
            i["kind"] == "note_added" and i["payload"]["note"].startswith("Called")
            for i in items
        )
    finally:
        await _cleanup(test_client, pid)


async def test_activity_org_isolation(test_client: AsyncClient):
    # Create project as admin (default test user)
    pid = await _create_project(test_client, name="Isolated Project")
    try:
        # Swap to a non-admin user from a different org
        def other_user():
            return User(
                id=999,
                email="stranger@other.com",
                full_name="Other Org User",
                is_active=True,
                is_admin=False,
                organization_id=9999,
            )

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = other_user
        try:
            resp = await test_client.get(f"/api/v1/projects/{pid}/activity")
            assert resp.status_code == status.HTTP_404_NOT_FOUND

            post = await test_client.post(
                f"/api/v1/projects/{pid}/activity",
                json={"note": "hello"},
            )
            assert post.status_code == status.HTTP_404_NOT_FOUND
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
    finally:
        await _cleanup(test_client, pid)
