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
