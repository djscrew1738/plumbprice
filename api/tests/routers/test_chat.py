import pytest
from httpx import AsyncClient
from starlette import status
from unittest.mock import patch

from app.services.pricing_engine import EstimateResult

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_estimate_result():
    """Fixture to create a mock EstimateResult."""
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
async def test_chat_price_success(
    mock_process_chat, test_client: AsyncClient, mock_estimate_result
):
    """Test the /api/v1/chat/price endpoint on success."""
    # Mock the agent's processing result
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
        "_estimate_result": mock_estimate_result,  # Include the raw result for persistence
    }

    request_data = {"message": "how much to replace a toilet"}
    response = await test_client.post("/api/v1/chat/price", json=request_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["answer"] == "The estimated price is $502."
    assert data["confidence_label"] == "HIGH"
    assert data["estimate_id"] is not None  # Check that an ID was assigned after persistence


@patch("app.routers.chat.process_chat_message")
async def test_chat_price_classification_failure(mock_process_chat, test_client: AsyncClient):
    """Test the chat price endpoint when the agent cannot classify the message."""
    mock_process_chat.return_value = {
        "answer": "I can't classify this.",
        "estimate": None,
        "confidence": 0.0,
        "confidence_label": "LOW",
        "assumptions": ["Could not classify job type from message"],
        "sources": [],
        "_estimate_result": None,
    }

    request_data = {"message": "how much is a thingy?"}
    response = await test_client.post("/api/v1/chat/price", json=request_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["answer"] == "I can't classify this."
    assert data["confidence_label"] == "LOW"
    assert data["estimate_id"] is None


@patch("app.routers.chat.process_chat_message", side_effect=Exception("Pricing engine exploded"))
async def test_chat_price_server_error(mock_process_chat, test_client: AsyncClient):
    """Test the chat price endpoint when a server error occurs."""
    request_data = {"message": "This will cause an error"}
    response = await test_client.post("/api/v1/chat/price", json=request_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "An error occurred while processing your request" in data["detail"]
