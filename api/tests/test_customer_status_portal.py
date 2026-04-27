"""Tests for the customer status portal (f2-customer-status-portal)."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate
from app.models.projects import Project, ProjectActivity

pytestmark = pytest.mark.asyncio


async def _make_estimate(db_session: AsyncSession, project_id: int | None = None) -> Estimate:
    est = Estimate(
        title="Status Portal Estimate",
        job_type="service",
        status="draft",
        labor_total=200.0,
        materials_total=100.0,
        tax_total=24.75,
        markup_total=30.0,
        misc_total=0.0,
        subtotal=330.0,
        grand_total=354.75,
        confidence_score=0.9,
        confidence_label="HIGH",
        assumptions=[],
        sources=[],
        county="Dallas",
        tax_rate=0.0825,
        created_by=1,
        project_id=project_id,
    )
    db_session.add(est)
    await db_session.commit()
    await db_session.refresh(est)
    return est


async def _make_project(db_session: AsyncSession, status: str = "in_progress") -> Project:
    proj = Project(
        name="Smith Residence Repipe",
        job_type="service",
        status=status,
        customer_name="Jane Smith",
        city="Dallas",
        state="TX",
        created_by=1,
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


async def _send_and_accept(test_client, estimate_id: int) -> str:
    sent = await test_client.post(
        f"/api/v1/proposals/{estimate_id}/send",
        json={"recipient_email": "jane@example.com", "recipient_name": "Jane"},
    )
    assert sent.status_code == 200, sent.text
    token = sent.json()["public_token"]
    accepted = await test_client.post(
        f"/api/v1/public/proposals/{token}/accept",
        json={"signature": "Jane Smith"},
    )
    assert accepted.status_code == 200, accepted.text
    return token


async def test_status_404_before_accept(test_client, db_session):
    est = await _make_estimate(db_session)
    sent = await test_client.post(
        f"/api/v1/proposals/{est.id}/send",
        json={"recipient_email": "x@y.com", "recipient_name": "X"},
    )
    token = sent.json()["public_token"]
    r = await test_client.get(f"/api/v1/public/proposals/{token}/status")
    assert r.status_code == 404


async def test_status_returns_minimal_payload_after_accept(test_client, db_session):
    proj = await _make_project(db_session, status="scheduled")
    est = await _make_estimate(db_session, project_id=proj.id)
    token = await _send_and_accept(test_client, est.id)

    r = await test_client.get(f"/api/v1/public/proposals/{token}/status")
    assert r.status_code == 200
    data = r.json()
    assert data["token"] == token
    assert data["project_status"] == "scheduled"
    assert data["project_name"] == "Smith Residence Repipe"
    assert data["customer_name"] == "Jane Smith"
    assert data["accepted_at"] is not None
    assert data["milestones"] == []
    # No internal pricing leaked
    assert "grand_total" not in data
    assert "labor_total" not in data
    assert "markup_total" not in data


async def test_status_includes_visible_milestones_and_schedule(test_client, db_session):
    proj = await _make_project(db_session, status="in_progress")
    est = await _make_estimate(db_session, project_id=proj.id)
    token = await _send_and_accept(test_client, est.id)

    db_session.add_all([
        ProjectActivity(
            project=proj,
            kind="schedule_set",
            payload={"scheduled_for": "2026-05-10T14:00:00Z", "customer_note": "We'll see you Monday"},
        ),
        ProjectActivity(
            project=proj,
            kind="work_started",
            payload={"customer_note": "Crew on site"},
        ),
        # Internal kind that must NOT appear
        ProjectActivity(
            project=proj,
            kind="internal_margin_review",
            payload={"note": "secret profit talk"},
        ),
    ])
    await db_session.commit()

    r = await test_client.get(f"/api/v1/public/proposals/{token}/status")
    assert r.status_code == 200
    data = r.json()
    kinds = [m["kind"] for m in data["milestones"]]
    assert "schedule_set" in kinds
    assert "work_started" in kinds
    assert "internal_margin_review" not in kinds
    assert data["scheduled_for"] == "2026-05-10T14:00:00Z"


async def test_status_404_for_bogus_token(test_client):
    r = await test_client.get("/api/v1/public/proposals/bogus-token/status")
    assert r.status_code == 404


async def test_status_works_without_linked_project(test_client, db_session):
    est = await _make_estimate(db_session, project_id=None)
    token = await _send_and_accept(test_client, est.id)
    r = await test_client.get(f"/api/v1/public/proposals/{token}/status")
    assert r.status_code == 200
    data = r.json()
    assert data["project_status"] == "accepted"
    assert data["project_name"] == "Status Portal Estimate"
    assert data["milestones"] == []
