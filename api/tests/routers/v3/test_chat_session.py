"""Tests for V3 chat session_id persistence for conversation continuity."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from app.models.sessions import ChatSession, ChatMessage as ChatMessageModel
from app.services.agent_v3 import AgentV3Result
from app.services.llm_structured import ClassifyResult
from app.services.pricing_engine import EstimateResult

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_estimate_result():
    """Return a fully populated EstimateResult for chat tests."""
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
        assumptions=["Standard toilet replacement"],
        sources=["Ferguson catalog 2026"],
        pricing_trace={},
    )


@pytest.fixture
def mock_agent_result(mock_estimate_result: EstimateResult):
    """Return a basic AgentV3Result suitable for chat tests."""
    return AgentV3Result(
        classification=ClassifyResult(
            task_code="TOILET_REPLACE_STANDARD",
            county="Dallas",
            reasoning="Clear toilet replacement request.",
        ),
        estimate=mock_estimate_result,
        narrative="The estimated cost is $502.38.",
        classified_by="llm",
        tool_calls=[],
    )


# ---------------------------------------------------------------------------
# Tests — non-stream endpoint
# ---------------------------------------------------------------------------

@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_creates_session_on_first_request(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    mock_agent_result: AgentV3Result,
):
    """A first request (no session_id) creates a new ChatSession and returns session_id."""
    mock_process.return_value = mock_agent_result

    response = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "how much to replace a toilet", "county": "Dallas"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None
    assert isinstance(data["session_id"], int)
    assert data["session_id"] > 0
    assert data["estimate_id"] is not None
    assert data["answer"] == "The estimated cost is $502.38."


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_reuses_existing_session(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    mock_agent_result: AgentV3Result,
):
    """Sending a valid session_id reuses the same ChatSession across requests."""
    mock_process.return_value = mock_agent_result

    # First request — creates session
    resp1 = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "how much to replace a toilet", "county": "Dallas"},
    )
    session_id = resp1.json()["session_id"]
    assert session_id is not None

    # Second request — reuse session
    resp2 = await test_client.post(
        "/api/v3/chat/price",
        json={
            "message": "add a premium toilet",
            "county": "Dallas",
            "session_id": session_id,
        },
    )
    data2 = resp2.json()
    assert data2["session_id"] == session_id


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_stores_messages_in_session(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    db_session: AsyncSession,
    mock_agent_result: AgentV3Result,
):
    """Messages from the exchange are persisted as ChatMessage rows."""
    mock_process.return_value = mock_agent_result

    response = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "how much to replace a toilet", "county": "Dallas"},
    )
    session_id = response.json()["session_id"]

    # Query messages
    result = await db_session.execute(
        select(ChatMessageModel).where(ChatMessageModel.session_id == session_id)
    )
    messages = result.scalars().all()

    assert len(messages) == 2
    roles = {m.role for m in messages}
    assert roles == {"user", "assistant"}
    contents = {m.content for m in messages}
    assert "how much to replace a toilet" in contents


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_session_ownership(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    db_session: AsyncSession,
    mock_agent_result: AgentV3Result,
):
    """Session is linked to the authenticated user (id=1 in test)."""
    mock_process.return_value = mock_agent_result

    response = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "replace a water heater", "county": "Tarrant"},
    )
    data = response.json()

    # Fetch session from DB
    result = await db_session.execute(
        select(ChatSession).where(ChatSession.id == data["session_id"])
    )
    session = result.scalar_one_or_none()
    assert session is not None
    assert session.user_id == 1
    assert session.county == "Tarrant"
    assert session.title == "replace a water heater"  # truncated from message


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_invalid_session_id_creates_new(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    mock_agent_result: AgentV3Result,
):
    """An invalid (non-existent) session_id should create a new session."""
    mock_process.return_value = mock_agent_result

    response = await test_client.post(
        "/api/v3/chat/price",
        json={
            "message": "fix a leaky faucet",
            "county": "Dallas",
            "session_id": 99999,
        },
    )
    data = response.json()
    assert data["session_id"] is not None
    assert data["session_id"] != 99999


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_multiple_sessions_per_user(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    db_session: AsyncSession,
    mock_agent_result: AgentV3Result,
):
    """Sending two messages without session_id creates two distinct sessions."""
    mock_process.return_value = mock_agent_result

    resp1 = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "toilet replacement", "county": "Dallas"},
    )
    sid1 = resp1.json()["session_id"]

    resp2 = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "water heater install", "county": "Tarrant"},
    )
    sid2 = resp2.json()["session_id"]

    assert sid1 != sid2

    # Both belong to user 1
    result = await db_session.execute(
        select(ChatSession).where(ChatSession.id.in_([sid1, sid2]))
    )
    sessions = result.scalars().all()
    assert all(s.user_id == 1 for s in sessions)


# ---------------------------------------------------------------------------
# Tests — streaming endpoint
# ---------------------------------------------------------------------------

@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_stream_returns_session_id(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    mock_agent_result: AgentV3Result,
):
    """The streaming endpoint's pricing event includes session_id."""
    mock_process.return_value = mock_agent_result

    async with test_client.stream(
        "POST",
        "/api/v3/chat/price/stream",
        json={"message": "how much to replace a toilet", "county": "Dallas"},
    ) as response:
        assert response.status_code == 200
        lines = []
        async for chunk in response.aiter_lines():
            lines.append(chunk)

    # Find the pricing event data line
    pricing_data = None
    for i, line in enumerate(lines):
        if line.startswith("data: ") and i > 0 and lines[i - 1] == "event: pricing":
            import json
            pricing_data = json.loads(line[6:])
            break

    assert pricing_data is not None, "No pricing event found in stream"
    assert pricing_data.get("session_id") is not None
    assert isinstance(pricing_data["session_id"], int)


@patch("app.routers.v3.chat.agent_v3.process_message", new_callable=AsyncMock)
async def test_chat_v3_stream_reuses_session(
    mock_process: AsyncMock,
    test_client: AsyncClient,
    mock_agent_result: AgentV3Result,
):
    """Sending session_id to the stream endpoint reuses the session."""
    mock_process.return_value = mock_agent_result

    # First request to create session
    resp1 = await test_client.post(
        "/api/v3/chat/price",
        json={"message": "toilet replacement", "county": "Dallas"},
    )
    session_id = resp1.json()["session_id"]

    # Stream with session_id
    async with test_client.stream(
        "POST",
        "/api/v3/chat/price/stream",
        json={
            "message": "add labor for removal",
            "county": "Dallas",
            "session_id": session_id,
        },
    ) as response:
        lines = []
        async for chunk in response.aiter_lines():
            lines.append(chunk)

    pricing_data = None
    for i, line in enumerate(lines):
        if line.startswith("data: ") and i > 0 and lines[i - 1] == "event: pricing":
            import json
            pricing_data = json.loads(line[6:])
            break

    assert pricing_data is not None
    assert pricing_data["session_id"] == session_id
