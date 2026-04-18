"""Tests for blueprint → estimate conversion endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user
from app.main import app
from app.models.blueprints import BlueprintDetection, BlueprintJob, BlueprintPage
from app.models.users import User

pytestmark = pytest.mark.asyncio


BASE = "/api/v1/blueprints"


async def _mk_job(
    db_session, *, with_detections: bool = True, created_by: int = 1
) -> BlueprintJob:
    job = BlueprintJob(
        filename="blueprints/bp.pdf",
        original_filename="bp.pdf",
        storage_path="blueprints/bp.pdf",
        status="complete",
        created_by=created_by,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    page = BlueprintPage(job_id=job.id, page_number=1, sheet_type="plumbing")
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)
    await db_session.refresh(job)

    if with_detections:
        db_session.add_all([
            BlueprintDetection(
                page_id=page.id, fixture_type="toilet", count=3, confidence=0.92
            ),
            BlueprintDetection(
                page_id=page.id, fixture_type="lavatory", count=2, confidence=0.88
            ),
            BlueprintDetection(
                page_id=page.id, fixture_type="water_heater", count=1, confidence=0.95
            ),
        ])
        await db_session.commit()
        await db_session.refresh(job)

    return job


async def test_to_estimate_empty_takeoff_returns_422(test_client: AsyncClient, db_session):
    job = await _mk_job(db_session, with_detections=False)

    resp = await test_client.post(f"{BASE}/{job.id}/to-estimate", json={})
    assert resp.status_code == 422
    assert "fixtures" in resp.json()["detail"].lower()


async def test_to_estimate_creates_draft_with_line_items(
    test_client: AsyncClient, db_session
):
    job = await _mk_job(db_session)

    resp = await test_client.post(f"{BASE}/{job.id}/to-estimate", json={})
    assert resp.status_code == 200, resp.text
    estimate_id = resp.json()["estimate_id"]
    assert isinstance(estimate_id, int)

    # Pull the estimate back through the public endpoint to verify shape
    detail = await test_client.get(f"/api/v1/estimates/{estimate_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "draft"
    assert payload["blueprint_job_id"] == job.id
    assert payload["job_type"] == "construction"
    # 3 toilets + 2 lavs + 1 WH → multiple material rows + labor rows + markup/misc/tax
    assert len(payload["line_items"]) >= 6
    line_types = {li["line_type"] for li in payload["line_items"]}
    assert {"material", "labor"}.issubset(line_types)
    assert payload["grand_total"] > 0


async def test_to_estimate_404_for_non_owner(test_client: AsyncClient, db_session):
    # Job owned by a different user
    job = await _mk_job(db_session, created_by=42)

    async def _other_user():
        return User(
            id=999,
            email="other@example.com",
            full_name="Other User",
            is_active=True,
            is_admin=False,
        )

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _other_user
    try:
        resp = await test_client.post(f"{BASE}/{job.id}/to-estimate", json={})
        assert resp.status_code == 404
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


async def test_to_estimate_is_not_deduped(test_client: AsyncClient, db_session):
    job = await _mk_job(db_session)

    r1 = await test_client.post(f"{BASE}/{job.id}/to-estimate", json={})
    r2 = await test_client.post(f"{BASE}/{job.id}/to-estimate", json={})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["estimate_id"] != r2.json()["estimate_id"]
