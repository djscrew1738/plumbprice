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


def _make_service_with_client(client_mock) -> LLMService:
    """Create a fresh LLMService and inject a mock client."""
    svc = LLMService()
    svc._client = client_mock
    svc._available = None  # untested
    return svc


# ─── classify() ───────────────────────────────────────────────────────────────

async def test_classify_returns_none_when_blocked():
    svc = LLMService()
    svc._available = False  # circuit-breaker tripped
    result = await svc.classify("replace the toilet")
    assert result is None


async def test_classify_successful_json_response():
    payload = {
        "task_code": "TOILET_REPLACE_STANDARD",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.92,
    }
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion(json.dumps(payload))
    )

    svc = _make_service_with_client(client_mock)
    result = await svc.classify("how much to replace a toilet")

    assert result is not None
    assert result["task_code"] == "TOILET_REPLACE_STANDARD"
    assert result["confidence"] == pytest.approx(0.92)
    assert result["county"] == "Dallas"
    assert result["quantity"] == 1
    assert svc._available is True


async def test_classify_clamps_confidence_to_range():
    payload = {
        "task_code": "KITCHEN_FAUCET_REPLACE",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 2.5,  # out of range — should be clamped to 1.0
    }
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion(json.dumps(payload))
    )

    svc = _make_service_with_client(client_mock)
    result = await svc.classify("fix kitchen faucet")

    assert result is not None
    assert result["confidence"] == pytest.approx(1.0)


async def test_classify_normalises_invalid_county_to_dallas():
    payload = {
        "task_code": "TOILET_REPLACE_STANDARD",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Bexar",  # not a DFW county
        "quantity": 1,
        "preferred_supplier": None,
        "confidence": 0.8,
    }
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion(json.dumps(payload))
    )

    svc = _make_service_with_client(client_mock)
    result = await svc.classify("replace toilet")

    assert result["county"] == "Dallas"


async def test_classify_returns_none_on_invalid_json():
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion("this is not json {{}}")
    )

    svc = _make_service_with_client(client_mock)
    result = await svc.classify("some message")

    # Parse error should return None but NOT mark service unavailable
    assert result is None
    assert svc._available is None  # still untested, not blocked


async def test_classify_marks_unavailable_on_connection_error():
    class FakeConnectionError(Exception):
        pass
    FakeConnectionError.__name__ = "APIConnectionError"  # triggers "Connection" check

    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(side_effect=FakeConnectionError("refused"))

    svc = _make_service_with_client(client_mock)
    result = await svc.classify("replace toilet")

    assert result is None
    assert svc._available is False  # circuit-breaker tripped


async def test_classify_quantity_clamped_to_range():
    payload = {
        "task_code": "ANGLE_STOP_REPLACE",
        "access_type": "first_floor",
        "urgency": "standard",
        "county": "Dallas",
        "quantity": 99,  # beyond max of 20
        "preferred_supplier": None,
        "confidence": 0.85,
    }
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion(json.dumps(payload))
    )

    svc = _make_service_with_client(client_mock)
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


async def test_generate_response_returns_text():
    opener = "Replacing your toilet in Dallas will run about $502 all-in."
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion(opener)
    )

    svc = _make_service_with_client(client_mock)
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


async def test_generate_response_returns_none_on_error():
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))

    svc = _make_service_with_client(client_mock)
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


async def test_generate_response_returns_none_for_empty_text():
    client_mock = AsyncMock()
    client_mock.chat.completions.create = AsyncMock(
        return_value=_make_completion("   ")  # whitespace only
    )

    svc = _make_service_with_client(client_mock)
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

async def test_check_available_returns_true_when_models_list_succeeds():
    client_mock = AsyncMock()
    client_mock.models.list = AsyncMock(return_value=[])

    svc = _make_service_with_client(client_mock)
    ok = await svc.check_available()

    assert ok is True
    assert svc._available is True


async def test_check_available_returns_false_on_error():
    client_mock = AsyncMock()
    client_mock.models.list = AsyncMock(side_effect=Exception("connection refused"))

    svc = _make_service_with_client(client_mock)
    ok = await svc.check_available()

    assert ok is False
    assert svc._available is False


async def test_check_available_returns_false_when_no_client():
    svc = LLMService()
    svc._client = None
    # Patch settings so hermes_endpoint_url is empty (no client created)
    with patch("app.services.llm_service.settings") as mock_settings:
        mock_settings.hermes_endpoint_url = ""
        ok = await svc.check_available()
    assert ok is False
