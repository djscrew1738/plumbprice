"""Tests for the public agent router (v3 upgrade)."""

import pytest
from httpx import AsyncClient
from starlette import status
from unittest.mock import patch

from app.services.llm_structured import ClassifyResult
from app.services.pricing_engine import EstimateResult, LineItem
from app.services.agent_v3 import AgentV3Result

pytestmark = pytest.mark.asyncio


def _make_estimate_result(
    *,
    task_code: str = "TOILET_REPLACE",
    grand_total: float = 750.0,
    confidence_score: float = 0.9,
    confidence_label: str = "HIGH",
    line_items: list[LineItem] | None = None,
) -> EstimateResult:
    return EstimateResult(
        template_code=task_code,
        assembly_code=None,
        job_type="service",
        access_type="first_floor",
        urgency_type="standard",
        county="Dallas",
        tax_rate=0.0825,
        labor_total=300.0,
        materials_total=400.0,
        tax_total=50.0,
        markup_total=0.0,
        misc_total=0.0,
        subtotal=700.0,
        grand_total=grand_total,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        line_items=line_items or [],
        assumptions=["First-floor access assumed"],
        sources=["public_widget_v3"],
        pricing_trace={},
    )


def _make_classify_result(
    *,
    task_code: str = "TOILET_REPLACE",
    confidence: float = 0.9,
) -> ClassifyResult:
    return ClassifyResult(
        task_code=task_code,
        access_type="first_floor",
        urgency="standard",
        county="Dallas",
        city="Dallas",
        quantity=1,
        preferred_supplier=None,
        confidence=confidence,
        reasoning="Clear request",
    )


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_clarification(mock_process, test_client: AsyncClient):
    """When confidence is low, the agent returns clarification questions."""
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(task_code=None, confidence=0.5),
        estimate=_make_estimate_result(task_code=None, confidence_score=0.5, confidence_label="LOW"),
        clarification_questions=["Is this a one-piece or two-piece toilet?", "What floor is it on?"],
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "replace my toilet",
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "clarification"
    assert len(data["clarification_questions"]) == 2
    assert data["follow_up_required"] is True
    assert data["estimate"] is None


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_success(mock_process, test_client: AsyncClient):
    """A quotable, in-scope job returns a full estimate."""
    line_items = [
        LineItem(
            line_type="material",
            description="Toilet bowl",
            quantity=1,
            unit="ea",
            unit_cost=250.0,
            total_cost=250.0,
        ),
        LineItem(
            line_type="labor",
            description="Installation labor",
            quantity=1.5,
            unit="hr",
            unit_cost=100.0,
            total_cost=150.0,
        ),
    ]
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(),
        estimate=_make_estimate_result(line_items=line_items),
        tool_calls=[],
        market_adjustments_applied=[],
        narrative="Typical DFW toilet replacement.",
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "How much to replace a toilet?",
        "customer": {"name": "Jane", "email": "jane@example.com", "zip_code": "75201"},
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["task_code"] == "TOILET_REPLACE"
    assert data["follow_up_required"] is False
    assert data["lead_id"] is not None

    est = data["estimate"]
    assert est["grand_total"] == 750.0
    assert est["subtotal"] == 700.0
    assert est["confidence"] == 0.9
    assert est["confidence_label"] == "HIGH"
    assert len(est["line_items"]) == 2
    assert est["line_items"][0]["description"] == "Toilet bowl"
    assert est["assumptions"] == ["First-floor access assumed"]


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_out_of_scope(mock_process, test_client: AsyncClient):
    """Jobs outside the allowed task list trigger lead capture only."""
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(task_code="WHOLE_HOUSE_REPIPE", confidence=0.85),
        estimate=_make_estimate_result(
            task_code="WHOLE_HOUSE_REPIPE",
            grand_total=12000.0,
            confidence_score=0.85,
            confidence_label="HIGH",
        ),
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "Repipe my whole house",
        "customer": {"email": "bob@example.com"},
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "out_of_scope"
    assert data["estimate"] is None
    assert data["follow_up_required"] is True
    assert data["lead_id"] is not None


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_too_large(mock_process, test_client: AsyncClient):
    """Estimates exceeding the public max total trigger lead capture only."""
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(task_code="WATER_HEATER_REPLACE_50G_GAS", confidence=0.9),
        estimate=_make_estimate_result(
            task_code="WATER_HEATER_REPLACE_50G_GAS",
            grand_total=8000.0,
            confidence_score=0.9,
            confidence_label="HIGH",
        ),
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "Replace water heater",
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "too_large"
    assert data["estimate"] is None
    assert data["follow_up_required"] is True


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_uncertain(mock_process, test_client: AsyncClient):
    """Low-confidence estimates trigger lead capture only."""
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(task_code="TOILET_REPLACE", confidence=0.4),
        estimate=_make_estimate_result(
            confidence_score=0.4,
            confidence_label="LOW",
        ),
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "something weird with plumbing",
    })

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "uncertain"
    assert data["estimate"] is None
    assert data["follow_up_required"] is True


@patch("app.routers.public_agent.agent_v3.process_message")
async def test_public_quote_history_passed(mock_process, test_client: AsyncClient):
    """Conversation history is forwarded to the v3 agent."""
    mock_process.return_value = AgentV3Result(
        classification=_make_classify_result(),
        estimate=_make_estimate_result(),
    )

    response = await test_client.post("/api/v1/public-agent/quote", json={
        "message": "Yes, first floor",
        "history": [
            {"role": "user", "content": "Replace a toilet"},
            {"role": "assistant", "content": "What floor is it on?"},
        ],
    })

    assert response.status_code == status.HTTP_200_OK
    call_kwargs = mock_process.call_args.kwargs
    assert call_kwargs["history"] == [
        {"role": "user", "content": "Replace a toilet"},
        {"role": "assistant", "content": "What floor is it on?"},
    ]


async def test_public_quote_config(test_client: AsyncClient):
    """Config endpoint returns widget metadata."""
    response = await test_client.get("/api/v1/public-agent/quote/config")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["enabled"] is True
    assert data["max_total_usd"] == 7500.0
    assert data["rate_per_minute"] == 10
    assert data["allowed_task_count"] > 0
