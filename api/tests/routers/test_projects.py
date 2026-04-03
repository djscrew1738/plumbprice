import pytest
from httpx import AsyncClient
from starlette import status

pytestmark = pytest.mark.asyncio


async def test_create_project_defaults_to_lead_pipeline_status(test_client: AsyncClient):
    response = await test_client.post(
        "/api/v1/projects",
        json={
            "name": "Lakewood Water Heater",
            "job_type": "service",
            "customer_name": "Jane Doe",
            "county": "Dallas",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["name"] == "Lakewood Water Heater"
    assert payload["status"] == "lead"
    assert payload["customer_name"] == "Jane Doe"


async def test_list_projects_filters_by_status(test_client: AsyncClient):
    await test_client.post(
        "/api/v1/projects",
        json={
            "name": "Lead Project",
            "job_type": "service",
            "customer_name": "Lead Customer",
            "county": "Dallas",
        },
    )
    await test_client.post(
        "/api/v1/projects",
        json={
            "name": "Sent Project",
            "job_type": "service",
            "customer_name": "Sent Customer",
            "county": "Dallas",
            "status": "estimate_sent",
        },
    )

    response = await test_client.get("/api/v1/projects", params={"status": "estimate_sent"})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["summary"]["estimate_sent"] == 1
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["name"] == "Sent Project"
    assert payload["projects"][0]["status"] == "estimate_sent"


async def test_get_project_returns_detail(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/v1/projects",
        json={
            "name": "Detail Test Project",
            "job_type": "commercial",
            "customer_name": "Acme Corp",
            "customer_phone": "214-555-1234",
            "customer_email": "acme@example.com",
            "county": "Collin",
            "city": "Plano",
            "notes": "Access through side gate",
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    project_id = create_resp.json()["id"]

    response = await test_client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Detail Test Project"
    assert data["customer_name"] == "Acme Corp"
    assert data["customer_phone"] == "214-555-1234"
    assert data["customer_email"] == "acme@example.com"
    assert data["county"] == "Collin"
    assert data["city"] == "Plano"
    assert data["notes"] == "Access through side gate"
    assert data["estimate_count"] == 0
    assert isinstance(data["estimates"], list)


async def test_get_project_not_found(test_client: AsyncClient):
    response = await test_client.get("/api/v1/projects/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


async def test_update_project_status(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/v1/projects",
        json={"name": "Status Update Test", "job_type": "service", "county": "Dallas"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    project_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "lead"

    patch_resp = await test_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "estimate_sent"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["status"] == "estimate_sent"


async def test_update_project_customer_info(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/v1/projects",
        json={"name": "Customer Info Test", "job_type": "service", "county": "Tarrant"},
    )
    project_id = create_resp.json()["id"]

    patch_resp = await test_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "customer_name": "Bob Smith",
            "customer_phone": "817-555-9876",
            "customer_email": "bob@example.com",
            "notes": "Prefers morning appointments",
        },
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    updated = patch_resp.json()
    assert updated["customer_name"] == "Bob Smith"


async def test_update_project_invalid_status(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/v1/projects",
        json={"name": "Invalid Status Test", "job_type": "service", "county": "Dallas"},
    )
    project_id = create_resp.json()["id"]

    patch_resp = await test_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "not_a_real_status"},
    )
    assert patch_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid status" in patch_resp.json()["detail"].lower()


async def test_update_project_not_found(test_client: AsyncClient):
    response = await test_client.patch(
        "/api/v1/projects/99999",
        json={"status": "won"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_project(test_client: AsyncClient):
    create_resp = await test_client.post(
        "/api/v1/projects",
        json={"name": "Delete Me", "job_type": "service", "county": "Dallas"},
    )
    project_id = create_resp.json()["id"]

    delete_resp = await test_client.delete(f"/api/v1/projects/{project_id}")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    # Confirm it's gone
    get_resp = await test_client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_project_not_found(test_client: AsyncClient):
    response = await test_client.delete("/api/v1/projects/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
