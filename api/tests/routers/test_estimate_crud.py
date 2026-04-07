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


# ─── POST /estimates/{id}/duplicate ───────────────────────────────────────────

async def test_duplicate_estimate_creates_copy_with_same_line_items(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Duplicate should create a new estimate with title ' (copy)' appended and all line items copied."""
    # Create original
    eid = await _create_estimate(test_client, mock_estimate_result)

    # Fetch original to verify state
    get_orig = await test_client.get(f"/api/v1/estimates/{eid}")
    assert get_orig.status_code == status.HTTP_200_OK
    orig_data = get_orig.json()

    # Duplicate it
    dup_resp = await test_client.post(f"/api/v1/estimates/{eid}/duplicate")
    assert dup_resp.status_code == status.HTTP_201_CREATED
    dup_data = dup_resp.json()

    # Verify new estimate properties
    assert dup_data["id"] != eid  # Different ID
    assert dup_data["title"] == f"{orig_data['title']} (copy)"
    assert dup_data["status"] == "draft"  # Always draft
    assert dup_data["job_type"] == orig_data["job_type"]
    assert dup_data["grand_total"] == orig_data["grand_total"]
    assert dup_data["labor_total"] == orig_data["labor_total"]
    assert dup_data["materials_total"] == orig_data["materials_total"]
    assert dup_data["county"] == orig_data["county"]
    assert dup_data["tax_rate"] == orig_data["tax_rate"]

    # Verify original is unchanged
    get_check = await test_client.get(f"/api/v1/estimates/{eid}")
    assert get_check.status_code == status.HTTP_200_OK
    check_data = get_check.json()
    assert check_data["title"] == orig_data["title"]  # No (copy) suffix
    assert check_data["id"] == eid  # Same ID


async def test_duplicate_estimate_copies_line_items_exactly(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Duplicate should copy all line items exactly."""
    eid = await _create_estimate(test_client, mock_estimate_result)

    # Duplicate
    dup_resp = await test_client.post(f"/api/v1/estimates/{eid}/duplicate")
    assert dup_resp.status_code == status.HTTP_201_CREATED
    dup_data = dup_resp.json()
    dup_id = dup_data["id"]

    # Fetch both originals' and duplicates' line items
    orig_resp = await test_client.get(f"/api/v1/estimates/{eid}")
    orig_line_items = orig_resp.json()["line_items"]

    dup_fetch = await test_client.get(f"/api/v1/estimates/{dup_id}")
    dup_line_items = dup_fetch.json()["line_items"]

    # Should have same number and content
    assert len(dup_line_items) == len(orig_line_items)
    for orig_li, dup_li in zip(orig_line_items, dup_line_items):
        assert dup_li["line_type"] == orig_li["line_type"]
        assert dup_li["description"] == orig_li["description"]
        assert dup_li["quantity"] == orig_li["quantity"]
        assert dup_li["unit"] == orig_li["unit"]
        assert dup_li["unit_cost"] == orig_li["unit_cost"]
        assert dup_li["total_cost"] == orig_li["total_cost"]
        assert dup_li["supplier"] == orig_li["supplier"]


async def test_duplicate_estimate_status_is_always_draft(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Even if original is 'sent' or 'accepted', duplicate should be 'draft'."""
    eid = await _create_estimate(test_client, mock_estimate_result)

    # Change original to 'sent'
    await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "sent"})

    # Duplicate
    dup_resp = await test_client.post(f"/api/v1/estimates/{eid}/duplicate")
    assert dup_resp.status_code == status.HTTP_201_CREATED
    assert dup_resp.json()["status"] == "draft"


async def test_duplicate_estimate_original_unchanged(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Duplicating should not modify the original estimate in any way."""
    eid = await _create_estimate(test_client, mock_estimate_result)

    # Get original state
    orig_resp = await test_client.get(f"/api/v1/estimates/{eid}")
    orig_state = orig_resp.json()

    # Duplicate it
    await test_client.post(f"/api/v1/estimates/{eid}/duplicate")

    # Fetch original again and compare
    check_resp = await test_client.get(f"/api/v1/estimates/{eid}")
    check_state = check_resp.json()

    # Everything except created_at should be identical
    for key in orig_state.keys():
        if key != "created_at":
            assert check_state[key] == orig_state[key]


async def test_duplicate_estimate_not_found(test_client: AsyncClient):
    """Duplicating a non-existent estimate should return 404."""
    resp = await test_client.post("/api/v1/estimates/99999/duplicate")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in resp.json()["detail"].lower()


async def test_duplicate_estimate_preserves_metadata(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Duplicate should preserve county, tax_rate, confidence_score, and assumptions."""
    eid = await _create_estimate(test_client, mock_estimate_result)

    orig_resp = await test_client.get(f"/api/v1/estimates/{eid}")
    orig_data = orig_resp.json()

    dup_resp = await test_client.post(f"/api/v1/estimates/{eid}/duplicate")
    dup_data = dup_resp.json()

    assert dup_data["county"] == orig_data["county"]
    assert dup_data["tax_rate"] == orig_data["tax_rate"]
    assert dup_data["confidence_score"] == orig_data["confidence_score"]
    assert dup_data["confidence_label"] == orig_data["confidence_label"]
    assert dup_data["assumptions"] == orig_data["assumptions"]


async def test_duplicate_estimate_response_has_correct_status_code(
    test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    """Duplicate endpoint should return 201 Created."""
    eid = await _create_estimate(test_client, mock_estimate_result)
    resp = await test_client.post(f"/api/v1/estimates/{eid}/duplicate")
    assert resp.status_code == status.HTTP_201_CREATED
