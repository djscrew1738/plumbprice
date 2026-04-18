"""Tests for the analytics router and service layer."""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.auth import get_current_user
from app.main import app
from app.models.estimates import Estimate
from app.models.outcomes import EstimateOutcome
from app.models.projects import Project, ProjectActivity
from app.models.users import User

pytestmark = pytest.mark.asyncio

# Use a dedicated organization so our fixtures never collide with other test
# modules that share the in-memory SQLite database.
ORG_ID = 770001
OTHER_ORG_ID = 770002


def _analytics_admin() -> User:
    return User(
        id=7001, email="analytics-admin@x.com", full_name="Analytics Admin",
        is_active=True, is_admin=True, organization_id=ORG_ID, role="admin",
    )


@pytest_asyncio.fixture(autouse=True)
async def _scope_to_analytics_org(db_session):
    """Swap the auth override to a user scoped to the analytics test org,
    and clean that org's rows between tests so each test sees a fresh state."""
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _analytics_admin

    async def _scrub() -> None:
        await db_session.execute(
            delete(EstimateOutcome).where(
                EstimateOutcome.organization_id.in_([ORG_ID, OTHER_ORG_ID])
            )
        )
        await db_session.execute(
            delete(ProjectActivity).where(
                ProjectActivity.project_id.in_(
                    [301, 302, 303, 304, 305]
                )
            )
        )
        await db_session.execute(
            delete(Estimate).where(
                Estimate.organization_id.in_([ORG_ID, OTHER_ORG_ID])
            )
        )
        await db_session.execute(
            delete(Project).where(
                Project.organization_id.in_([ORG_ID, OTHER_ORG_ID])
            )
        )
        await db_session.execute(
            delete(User).where(User.organization_id.in_([ORG_ID, OTHER_ORG_ID]))
        )
        await db_session.commit()

    await _scrub()
    try:
        yield
    finally:
        await _scrub()
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


async def _seed_estimate(
    db,
    *,
    estimate_id: int,
    organization_id: int,
    job_type: str,
    grand_total: float = 1000.0,
    created_by: int | None = 7001,
    project_id: int | None = None,
) -> Estimate:
    est = Estimate(
        id=estimate_id,
        project_id=project_id,
        title=f"Est {estimate_id}",
        job_type=job_type,
        status="draft",
        grand_total=grand_total,
        organization_id=organization_id,
        created_by=created_by,
    )
    db.add(est)
    await db.commit()
    return est


async def _seed_outcome(
    db,
    *,
    estimate_id: int,
    organization_id: int,
    outcome: str,
    final_price: float,
) -> EstimateOutcome:
    row = EstimateOutcome(
        estimate_id=estimate_id,
        outcome=outcome,
        final_price=final_price,
        organization_id=organization_id,
        recorded_by=7001,
    )
    db.add(row)
    await db.commit()
    return row


# ── /analytics/revenue ──────────────────────────────────────────────────────


async def test_revenue_empty_returns_zero_shape(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/analytics/revenue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_won"] == 0
    assert body["deal_count"] == 0
    assert body["avg_deal_size"] == 0
    assert body["by_month"] == []
    assert body["by_job_type"] == []


async def test_revenue_aggregates_by_month_and_job_type(
    test_client: AsyncClient, db_session
):
    await _seed_estimate(
        db_session, estimate_id=77_101, organization_id=ORG_ID, job_type="service",
        grand_total=500.0,
    )
    await _seed_estimate(
        db_session, estimate_id=77_102, organization_id=ORG_ID, job_type="service",
        grand_total=500.0,
    )
    await _seed_estimate(
        db_session, estimate_id=77_103, organization_id=ORG_ID, job_type="commercial",
        grand_total=3000.0,
    )

    await _seed_outcome(
        db_session, estimate_id=77_101, organization_id=ORG_ID,
        outcome="won", final_price=400.0,
    )
    await _seed_outcome(
        db_session, estimate_id=77_102, organization_id=ORG_ID,
        outcome="won", final_price=600.0,
    )
    await _seed_outcome(
        db_session, estimate_id=77_103, organization_id=ORG_ID,
        outcome="won", final_price=2500.0,
    )
    # A lost outcome must not be counted toward revenue.
    await _seed_estimate(
        db_session, estimate_id=77_104, organization_id=ORG_ID, job_type="service",
    )
    await _seed_outcome(
        db_session, estimate_id=77_104, organization_id=ORG_ID,
        outcome="lost", final_price=999.0,
    )

    resp = await test_client.get("/api/v1/analytics/revenue?period=all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_won"] == 3500.0
    assert body["deal_count"] == 3
    assert body["avg_deal_size"] == pytest.approx(1166.67, rel=1e-3)

    types = {entry["type"]: entry for entry in body["by_job_type"]}
    assert types["service"]["amount"] == 1000.0
    assert types["service"]["count"] == 2
    assert types["commercial"]["amount"] == 2500.0

    assert len(body["by_month"]) >= 1
    assert sum(m["count"] for m in body["by_month"]) == 3


async def test_revenue_org_isolation(test_client: AsyncClient, db_session):
    # Other-org data must be invisible to ORG_ID.
    await _seed_estimate(
        db_session, estimate_id=77_201, organization_id=OTHER_ORG_ID, job_type="service",
    )
    await _seed_outcome(
        db_session, estimate_id=77_201, organization_id=OTHER_ORG_ID,
        outcome="won", final_price=10_000.0,
    )
    # Our org data
    await _seed_estimate(
        db_session, estimate_id=77_202, organization_id=ORG_ID, job_type="service",
    )
    await _seed_outcome(
        db_session, estimate_id=77_202, organization_id=ORG_ID,
        outcome="won", final_price=250.0,
    )

    resp = await test_client.get("/api/v1/analytics/revenue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_won"] == 250.0
    assert body["deal_count"] == 1


# ── /analytics/pipeline ─────────────────────────────────────────────────────


async def test_pipeline_empty_shape(test_client: AsyncClient):
    resp = await test_client.get("/api/v1/analytics/pipeline")
    assert resp.status_code == 200
    body = resp.json()
    assert "stage_counts" in body and "lead" in body["stage_counts"]
    assert body["stage_counts"]["lead"] == 0
    assert body["avg_time_in_stage_hours"]["lead"] == 0.0
    assert body["conversion"] == {
        "lead_to_quoted": 0.0, "quoted_to_won": 0.0, "overall": 0.0
    }


async def test_pipeline_residency_and_conversion(test_client: AsyncClient, db_session):
    base = datetime.now(timezone.utc) - timedelta(days=10)
    # Project A: lead -> estimate_sent -> won
    a = Project(
        id=301, name="A", job_type="service", status="won",
        organization_id=ORG_ID, created_by=7001,
    )
    a.created_at = base
    db_session.add(a)
    await db_session.commit()

    # Project B: lead -> estimate_sent
    b = Project(
        id=302, name="B", job_type="service", status="estimate_sent",
        organization_id=ORG_ID, created_by=7001,
    )
    b.created_at = base
    db_session.add(b)
    await db_session.commit()

    # Project C: lead only — no transitions
    c = Project(
        id=303, name="C", job_type="service", status="lead",
        organization_id=ORG_ID, created_by=7001,
    )
    c.created_at = base
    db_session.add(c)
    await db_session.commit()

    acts = [
        ProjectActivity(
            project_id=301, kind="stage_changed",
            payload={"from": "lead", "to": "estimate_sent"},
        ),
        ProjectActivity(
            project_id=301, kind="stage_changed",
            payload={"from": "estimate_sent", "to": "won"},
        ),
        ProjectActivity(
            project_id=302, kind="stage_changed",
            payload={"from": "lead", "to": "estimate_sent"},
        ),
    ]
    for ac in acts:
        db_session.add(ac)
    await db_session.commit()

    acts[0].created_at = base + timedelta(hours=10)
    acts[1].created_at = base + timedelta(hours=30)
    acts[2].created_at = base + timedelta(hours=40)
    await db_session.commit()

    resp = await test_client.get("/api/v1/analytics/pipeline")
    assert resp.status_code == 200
    body = resp.json()

    assert body["stage_counts"]["won"] == 1
    assert body["stage_counts"]["estimate_sent"] == 1
    assert body["stage_counts"]["lead"] == 1

    # Avg lead residency: (10 + 40) / 2 = 25h
    assert body["avg_time_in_stage_hours"]["lead"] == pytest.approx(25.0, rel=1e-3)
    # Only A transitioned out of estimate_sent: 20h
    assert body["avg_time_in_stage_hours"]["estimate_sent"] == pytest.approx(20.0, rel=1e-3)

    assert body["conversion"]["lead_to_quoted"] == pytest.approx(2 / 3, rel=1e-3)
    assert body["conversion"]["quoted_to_won"] == pytest.approx(0.5, rel=1e-3)
    assert body["conversion"]["overall"] == pytest.approx(1 / 3, rel=1e-3)


# ── /analytics/rep-performance ──────────────────────────────────────────────


async def test_rep_performance_forbidden_for_non_admin(test_client: AsyncClient):
    def not_admin():
        return User(
            id=42, email="rep@x.com", full_name="Rep",
            is_active=True, is_admin=False, organization_id=ORG_ID, role="estimator",
        )

    app.dependency_overrides[get_current_user] = not_admin
    try:
        resp = await test_client.get("/api/v1/analytics/rep-performance")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = _analytics_admin


async def test_rep_performance_admin_gets_rows(test_client: AsyncClient, db_session):
    u = User(
        id=7777, email="alice-analytics@x.com", full_name="Alice",
        hashed_password="x", is_active=True, is_admin=False,
        organization_id=ORG_ID, role="estimator",
    )
    db_session.add(u)
    await db_session.commit()

    await _seed_estimate(
        db_session, estimate_id=77_701, organization_id=ORG_ID, job_type="service",
        created_by=7777,
    )
    await _seed_outcome(
        db_session, estimate_id=77_701, organization_id=ORG_ID,
        outcome="won", final_price=1234.0,
    )

    resp = await test_client.get("/api/v1/analytics/rep-performance")
    assert resp.status_code == 200
    body = resp.json()
    alice = next((r for r in body["reps"] if r["user_id"] == 7777), None)
    assert alice is not None
    assert alice["quotes_created"] == 1
    assert alice["won_count"] == 1
    assert alice["won_amount"] == 1234.0
    assert alice["avg_deal_size"] == 1234.0

