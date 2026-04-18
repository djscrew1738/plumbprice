"""Tests for PATCH /api/v1/estimates/{id} — draft editing + auto-versioning."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from starlette import status

from app.core.auth import get_current_user
from app.main import app
from app.models.users import User
from app.services.pricing_engine import EstimateResult, LineItem

pytestmark = pytest.mark.asyncio


def _make_result() -> EstimateResult:
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
        line_items=[
            LineItem(line_type="labor", description="Labor", quantity=2, unit="hr",
                     unit_cost=125.0, total_cost=250.0),
            LineItem(line_type="material", description="Toilet", quantity=1, unit="ea",
                     unit_cost=150.0, total_cost=150.0),
        ],
        assumptions=["Standard access"],
        sources=["DFW labor rate table"],
        pricing_trace={},
    )


async def _create(client: AsyncClient, result: EstimateResult, msg: str = "replace toilet") -> int:
    with patch("app.routers.chat.process_chat_message") as m:
        m.return_value = {
            "answer": "ok",
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


async def test_patch_draft_updates_line_items_and_bumps_version(test_client: AsyncClient):
    eid = await _create(test_client, _make_result())

    resp = await test_client.patch(
        f"/api/v1/estimates/{eid}",
        json={
            "line_items": [
                {"line_type": "labor", "description": "Labor (2hr)",
                 "quantity": 2, "unit": "hr", "unit_cost": 150.0, "total_cost": 300.0},
                {"line_type": "material", "description": "Premium Toilet",
                 "quantity": 1, "unit": "ea", "unit_cost": 200.0, "total_cost": 200.0},
            ],
        },
    )
    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["labor_total"] == pytest.approx(300.0)
    assert body["materials_total"] == pytest.approx(200.0)
    assert body["subtotal"] == pytest.approx(500.0)
    assert body["grand_total"] == pytest.approx(500.0)  # no tax line in edit
    assert len(body["line_items"]) == 2

    # A new version snapshot should exist (initial v1 + pre-edit snapshot v2)
    versions = (await test_client.get(f"/api/v1/estimates/{eid}/versions")).json()
    numbers = sorted(v["version_number"] for v in versions["versions"])
    assert 2 in numbers
    assert max(numbers) >= 2


async def test_patch_non_draft_returns_409(test_client: AsyncClient):
    eid = await _create(test_client, _make_result())
    await test_client.patch(f"/api/v1/estimates/{eid}/status", json={"status": "sent"})

    resp = await test_client.patch(
        f"/api/v1/estimates/{eid}",
        json={"line_items": [
            {"line_type": "labor", "description": "x", "quantity": 1,
             "unit": "hr", "unit_cost": 100.0},
        ]},
    )
    assert resp.status_code == 409


async def test_patch_empty_line_items_returns_422(test_client: AsyncClient):
    eid = await _create(test_client, _make_result())
    resp = await test_client.patch(
        f"/api/v1/estimates/{eid}",
        json={"line_items": []},
    )
    assert resp.status_code == 422


async def test_patch_totals_recomputed(test_client: AsyncClient):
    eid = await _create(test_client, _make_result())
    resp = await test_client.patch(
        f"/api/v1/estimates/{eid}",
        json={"line_items": [
            {"line_type": "labor", "description": "L", "quantity": 1,
             "unit": "hr", "unit_cost": 100.0, "total_cost": 100.0},
            {"line_type": "material", "description": "M", "quantity": 2,
             "unit": "ea", "unit_cost": 25.0, "total_cost": 50.0},
            {"line_type": "markup", "description": "Markup", "quantity": 1,
             "unit": "lot", "unit_cost": 15.0, "total_cost": 15.0},
            {"line_type": "tax", "description": "Tax", "quantity": 1,
             "unit": "lot", "unit_cost": 4.13, "total_cost": 4.13},
        ]},
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["labor_total"] == pytest.approx(100.0)
    assert d["materials_total"] == pytest.approx(50.0)
    assert d["markup_total"] == pytest.approx(15.0)
    assert d["tax_total"] == pytest.approx(4.13)
    assert d["subtotal"] == pytest.approx(165.0)
    assert d["grand_total"] == pytest.approx(169.13)


async def test_patch_other_user_returns_404(test_client: AsyncClient):
    eid = await _create(test_client, _make_result())

    # Swap the auth override to return a non-admin different user with a
    # distinct organization — should not see the estimate.
    async def _other() -> User:
        return User(
            id=999,
            email="other@example.com",
            full_name="Other",
            is_active=True,
            is_admin=False,
            organization_id=424242,
        )

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _other
    try:
        resp = await test_client.patch(
            f"/api/v1/estimates/{eid}",
            json={"line_items": [
                {"line_type": "labor", "description": "x", "quantity": 1,
                 "unit": "hr", "unit_cost": 10.0},
            ]},
        )
        assert resp.status_code == 404
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
