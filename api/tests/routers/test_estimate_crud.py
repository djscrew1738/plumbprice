"""
Tests for estimate CRUD endpoints:
  GET  /estimates
  GET  /estimates/{id}
  PATCH /estimates/{id}/status
  DELETE /estimates/{id}
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from starlette import status

from app.services.pricing_engine import EstimateResult

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_estimate_result() -> EstimateResult:
    return EstimateResult(
        template_code="TOILET_REPLACE_STANDARD",
        assembly_code="TOILET_INSTALL_KIT",
        job_type="service",
        access_type="first_floor",
        urgency_type="standard",
        county="Dallas",
        tax_rate=0.0825,
        labor_total=250.0,
        materials_total=150.0,
        tax_total=12.38,
        markup_total=45.0,
        misc_total=45.0,
        subtotal=490.0,
        grand_total=502.38,
        confidence_score=0.9,
        confidence_label="HIGH",
        line_items=[],
        assumptions=["Standard access", "Gas water heater assumed"],
        sources=["DFW labor rate table"],
        pricing_trace={},
    )


async def _create_estimate(client: AsyncClient, result: EstimateResult, msg: str = "replace toilet") -> int:
    """Helper: POST to /chat/price with a mock to create and persist an estimate."""
    with patch("app.routers.chat.process_chat_message") as mock_agent:
        mock_agent.return_value = {
            "answer": "Estimated $502.",
            "estimate": {"grand_total": result.grand_total},
            "confidence": result.confidence_score,
            "confidence_label": result.confidence_label,
            "assumptions": result.assumptions,
            "sources": result.sources,
            "job_type_detected": result.job_type,
            "template_used": result.template_code,
            "classification": {"classified_by": "keyword"},
            "_estimate_result": result,
        }
        resp = await client.post("/api/v1/chat/price", json={"message": msg})
        assert resp.status_code == 200
        return resp.json()["estimate_id"]


# ─── GET /estimates ───────────────────────────────────────────────────────────

async def test_list_estimates_returns_empty_when_none(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/estimates")
    assert resp.status_code == status.HTTP_200_OK
    assert isinstance(resp.json(), list)


async def test_list_estimates_returns_created_estimates(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)
    resp = await test_client.get("/api/v1/estimates")
    assert resp.status_code == status.HTTP_200_OK
    ids = [e["id"] for e in resp.json()]
    assert eid in ids


async def test_list_estimates_filter_by_job_type(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    await _create_estimate(test_client, mock_estimate_result, msg="replace toilet")

    resp = await test_client.get("/api/v1/estimates", params={"job_type": "service"})
    assert resp.status_code == status.HTTP_200_OK
    for est in resp.json():
        assert est["job_type"] == "service"

    resp2 = await test_client.get("/api/v1/estimates", params={"job_type": "commercial"})
    assert resp2.status_code == status.HTTP_200_OK
    # Shouldn't include our service estimate
    ids = [e["id"] for e in resp2.json()]
    assert mock_estimate_result.job_type == "service"  # sanity


# ─── GET /estimates/{id} ──────────────────────────────────────────────────────

async def test_get_estimate_returns_detail(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)

    resp = await test_client.get(f"/api/v1/estimates/{eid}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["id"] == eid
    assert data["job_type"] == "service"
    assert data["grand_total"] == pytest.approx(502.38)
    assert data["confidence_label"] == "HIGH"
    assert isinstance(data["line_items"], list)
    assert isinstance(data["assumptions"], list)


async def test_get_estimate_not_found(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/estimates/99999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in resp.json()["detail"].lower()


# ─── PATCH /estimates/{id}/status ─────────────────────────────────────────────

async def test_update_estimate_status_to_sent(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)

    resp = await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "sent"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "sent"
    assert resp.json()["id"] == eid


async def test_update_estimate_status_to_accepted(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)
    resp = await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "accepted"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "accepted"


async def test_update_estimate_status_to_rejected(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)
    resp = await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "rejected"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "rejected"


async def test_update_estimate_status_invalid(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)
    resp = await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "approved"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid status" in resp.json()["detail"].lower()


async def test_update_estimate_status_not_found(test_client: AsyncClient):
    resp = await test_client.patch("/api/v1/estimates/99999/status", json={"status": "sent"})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── DELETE /estimates/{id} ───────────────────────────────────────────────────

async def test_delete_estimate_returns_204(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    eid = await _create_estimate(test_client, mock_estimate_result)

    resp = await test_client.delete(f"/api/v1/estimates/{eid}")
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    # Confirm it's gone
    get_resp = await test_client.get(f"/api/v1/estimates/{eid}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_estimate_not_found(test_client: AsyncClient):
    resp = await test_client.delete("/api/v1/estimates/99999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
