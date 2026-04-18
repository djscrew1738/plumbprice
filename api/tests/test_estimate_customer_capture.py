"""Tests for customer contact capture at estimate-creation time.

NOTE: These tests intentionally avoid using the ``db_session`` fixture.
The in-memory SQLite setup uses a fresh connection per session, so mixing
direct ORM reads with HTTP calls can drop rows across connections. Instead
we round-trip through the HTTP API exclusively to keep the same connection
pool semantics as the rest of the test suite.
"""
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.services.pricing_engine import EstimateResult, LineItem

pytestmark = pytest.mark.asyncio


def _make_result() -> EstimateResult:
    return EstimateResult(
        template_code="TOILET_REPLACE_STANDARD",
        assembly_code=None,
        job_type="service",
        access_type="first_floor",
        urgency_type="standard",
        county="Dallas",
        tax_rate=0.0825,
        labor_total=100.0,
        materials_total=50.0,
        tax_total=4.13,
        markup_total=15.0,
        misc_total=0.0,
        subtotal=165.0,
        grand_total=169.13,
        confidence_score=0.9,
        confidence_label="HIGH",
        line_items=[
            LineItem(line_type="labor", description="Labor", quantity=1, unit="hr",
                     unit_cost=100.0, total_cost=100.0),
        ],
        assumptions=[],
        sources=[],
        pricing_trace={},
    )


def _mock_agent(result: EstimateResult):
    return {
        "answer": "ok",
        "estimate": {"grand_total": result.grand_total},
        "confidence": result.confidence_score,
        "confidence_label": result.confidence_label,
        "assumptions": [],
        "sources": [],
        "job_type_detected": result.job_type,
        "template_used": result.template_code,
        "classification": {"classified_by": "keyword"},
        "_estimate_result": result,
    }


async def _post_chat(client: AsyncClient, result: EstimateResult, extra: dict) -> dict:
    with patch("app.routers.chat.process_chat_message") as m:
        m.return_value = _mock_agent(result)
        resp = await client.post(
            "/api/v1/chat/price",
            json={"message": "replace toilet", **extra},
        )
        assert resp.status_code == 200, resp.text
        return resp.json()


async def _projects_with_email(client: AsyncClient, email: str) -> list[dict]:
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    projects = payload.get("projects") if isinstance(payload, dict) else payload
    # Detail endpoint carries customer_email; list endpoint may not. Fetch each.
    matches: list[dict] = []
    for p in projects or []:
        detail = await client.get(f"/api/v1/projects/{p['id']}")
        if detail.status_code == 200:
            d = detail.json()
            if (d.get("customer_email") or "").lower() == email.lower():
                matches.append(d)
    return matches


async def test_customer_email_creates_new_lead_project(test_client: AsyncClient):
    data = await _post_chat(
        test_client,
        _make_result(),
        {"customer": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-1212",
            "address": "1 Main St, Dallas TX",
        }},
    )
    eid = data["estimate_id"]
    assert eid is not None

    projects = await _projects_with_email(test_client, "jane@example.com")
    assert len(projects) == 1
    proj = projects[0]
    assert proj["customer_email"] == "jane@example.com"
    assert proj["customer_name"] == "Jane Doe"
    assert proj["customer_phone"] == "555-1212"
    assert proj["status"] == "lead"


async def test_duplicate_customer_email_links_to_existing_project(test_client: AsyncClient):
    await _post_chat(
        test_client, _make_result(),
        {"customer": {"name": "Bob", "email": "bob@example.com"}},
    )
    await _post_chat(
        test_client, _make_result(),
        {"customer": {"name": "Bob", "email": "BOB@example.com"}},
    )
    projects = await _projects_with_email(test_client, "bob@example.com")
    assert len(projects) == 1


async def test_no_customer_info_no_project_created(test_client: AsyncClient):
    data = await _post_chat(test_client, _make_result(), {})
    eid = data["estimate_id"]
    assert eid is not None
    # Fetch estimate via HTTP; project_id should be absent/null
    detail = await test_client.get(f"/api/v1/estimates/{eid}")
    assert detail.status_code == 200
    body = detail.json()
    # Not all detail payloads include project_id; accept missing or None
    assert body.get("project_id") in (None, 0) or "project_id" not in body
