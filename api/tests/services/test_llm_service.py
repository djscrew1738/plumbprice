"""
Unit tests for LLMService (llm_service.py).
Mocks the AsyncOpenAI client — Ollama does not need to be running.
"""

import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_service import LLMService

pytestmark = pytest.mark.asyncio


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_completion(content: str):
    """Build a minimal mock ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.fixture
def mock_openai():
    """Fixture to mock AsyncOpenAI and return the mock client."""
    with patch("openai.AsyncOpenAI") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value = mock_client
        yield mock_client


# ─── classify() ───────────────────────────────────────────────────────────────

async def test_classify_returns_none_when_blocked():
    svc = LLMService()
    svc._available = False  # circuit-breaker tripped
    result = await svc.classify("replace the toilet")
    assert result is None


async def test_classify_successful_json_response(mock_openai):
    payload = {
        "task_code": "TOILET_REPLACE_STANDARD",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.92,
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("how much to replace a toilet")

    assert result is not None
    assert result["task_code"] == "TOILET_REPLACE_STANDARD"
    assert result["confidence"] == pytest.approx(0.92)
    assert result["county"] == "Dallas"
    assert result["quantity"] == 1
    assert svc._available is True


async def test_classify_prompt_contains_full_task_catalog(mock_openai):
    payload = {
        "task_code": "ROUGH_IN_MASTER_BATH",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Collin",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.9,
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("rough in a master bath")

    assert result is not None
    assert result["task_code"] == "ROUGH_IN_MASTER_BATH"
    prompt = mock_openai.chat.completions.create.await_args.kwargs["messages"][0]["content"]
    assert "ROUGH_IN_MASTER_BATH" in prompt
    assert "COMMERCIAL_URINAL_INSTALL" in prompt


async def test_classify_clamps_confidence_to_range(mock_openai):
    payload = {
        "task_code": "KITCHEN_FAUCET_REPLACE",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 2.5,  # out of range — should be clamped to 1.0
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("fix kitchen faucet")

    assert result is not None
    assert result["confidence"] == pytest.approx(1.0)


async def test_classify_normalises_invalid_county_to_dallas(mock_openai):
    payload = {
        "task_code": "TOILET_REPLACE_STANDARD",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Bexar",  # not a DFW county
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.8,
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("replace toilet")

    assert result["county"] == "Dallas"


async def test_classify_returns_none_on_invalid_json(mock_openai):
    mock_openai.chat.completions.create.return_value = _make_completion("this is not json {{}}")

    svc = LLMService()
    result = await svc.classify("some message")

    # Parse error should return None but NOT mark service unavailable
    assert result is None


async def test_classify_rejects_unknown_task_code(mock_openai):
    payload = {
        "task_code": "NOT_A_REAL_TASK",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.8,
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("some made up task")

    assert result is not None
    assert result["task_code"] is None


async def test_classify_marks_unavailable_on_connection_error(mock_openai):
    class FakeConnectionError(Exception):
        pass
    FakeConnectionError.__name__ = "APIConnectionError"  # triggers "Connection" check

    mock_openai.chat.completions.create.side_effect = FakeConnectionError("refused")

    svc = LLMService()
    result = await svc.classify("replace toilet")

    assert result is None
    assert svc._available is False  # circuit-breaker tripped


async def test_classify_quantity_clamped_to_range(mock_openai):
    payload = {
        "task_code": "ANGLE_STOP_REPLACE",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 99,  # beyond max of 20
        "preferred_supplier": None,
        "confidence": 0.85,
    }
    mock_openai.chat.completions.create.return_value = _make_completion(json.dumps(payload))

    svc = LLMService()
    result = await svc.classify("replace angle stops")

    assert result is not None
    assert result["quantity"] == 20  # clamped


# ─── generate_response() ──────────────────────────────────────────────────────

async def test_generate_response_returns_none_when_blocked():
    svc = LLMService()
    svc._available = False
    result = await svc.generate_response(
        message="replace toilet",
        grand_total=502.0,
        labor_total=250.0,
        materials_total=150.0,
        tax_total=12.38,
        template_name="Toilet Replacement",
        county="Dallas",
    )
    assert result is None


async def test_generate_response_returns_text(mock_openai):
    opener = "Replacing your toilet in Dallas will run about $502 all-in."
    mock_openai.chat.completions.create.return_value = _make_completion(opener)

    svc = LLMService()
    result = await svc.generate_response(
        message="how much to replace a toilet",
        grand_total=502.0,
        labor_total=250.0,
        materials_total=150.0,
        tax_total=12.38,
        template_name="Toilet Replacement",
        county="Dallas",
    )

    assert result == opener


async def test_generate_response_returns_none_on_error(mock_openai):
    mock_openai.chat.completions.create.side_effect = Exception("timeout")

    svc = LLMService()
    result = await svc.generate_response(
        message="replace toilet",
        grand_total=502.0,
        labor_total=250.0,
        materials_total=150.0,
        tax_total=12.38,
        template_name="Toilet Replacement",
        county="Dallas",
    )
    assert result is None


async def test_generate_response_returns_none_for_empty_text(mock_openai):
    mock_openai.chat.completions.create.return_value = _make_completion("   ")  # whitespace only

    svc = LLMService()
    result = await svc.generate_response(
        message="replace toilet",
        grand_total=502.0,
        labor_total=250.0,
        materials_total=150.0,
        tax_total=12.38,
        template_name="Toilet Replacement",
        county="Dallas",
    )
    assert result is None


# ─── check_available() ────────────────────────────────────────────────────────

async def test_check_available_returns_true_when_models_list_succeeds(mock_openai):
    mock_openai.models.list.return_value = []

    svc = LLMService()
    ok = await svc.check_available()

    assert ok is True
    assert svc._available is True


async def test_check_available_returns_false_on_error(mock_openai):
    mock_openai.models.list.side_effect = Exception("connection refused")

    svc = LLMService()
    ok = await svc.check_available()

    assert ok is False
    # On first failure, it promotes to secondary and available remains None
    assert svc._available is None
    assert svc._active_tier == "secondary"


async def test_check_available_returns_false_when_no_client():
    svc = LLMService()
    # Patch settings so hermes_endpoint_url is empty (no client created)
    with patch("app.services.llm_service.settings") as mock_settings:
        # We need to mock _make_client to return None or let it fail
        with patch("openai.AsyncOpenAI", side_effect=ImportError):
            ok = await svc.check_available()
    assert ok is False
