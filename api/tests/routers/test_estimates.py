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
        assumptions=["Test assumption"],
        sources=["Test source"],
        pricing_trace={},
    )


@patch("app.routers.chat.process_chat_message")
async def test_list_estimate_versions_returns_snapshot_history(
    mock_process_chat, test_client: AsyncClient, mock_estimate_result: EstimateResult
):
    mock_process_chat.return_value = {
        "answer": "The estimated price is $502.",
        "estimate": {"grand_total": 502.38},
        "confidence": 0.9,
        "confidence_label": "HIGH",
        "assumptions": ["Test assumption"],
        "sources": ["Test source"],
        "job_type_detected": "service",
        "template_used": "TOILET_REPLACE_STANDARD",
        "classification": {"classified_by": "keyword"},
        "_estimate_result": mock_estimate_result,
    }

    create_response = await test_client.post(
        "/api/v1/chat/price",
        json={"message": "how much to replace a toilet"},
    )

    assert create_response.status_code == status.HTTP_200_OK
    estimate_id = create_response.json()["estimate_id"]

    versions_response = await test_client.get(f"/api/v1/estimates/{estimate_id}/versions")

    assert versions_response.status_code == status.HTTP_200_OK
    payload = versions_response.json()
    assert len(payload["versions"]) == 1
    assert payload["versions"][0]["version_number"] == 1
    assert payload["versions"][0]["snapshot"]["grand_total"] == 502.38
    assert payload["versions"][0]["snapshot"]["county"] == "Dallas"
