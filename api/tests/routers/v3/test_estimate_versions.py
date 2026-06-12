"""Tests for Phase 14 — Estimate Versioning & Branching endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, delete

from app.core.auth import get_current_user
from app.main import app
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.models.users import User

pytestmark = pytest.mark.asyncio

ORG_ID = 990001
USER_ID = 9001


def _org_user() -> User:
    return User(
        id=USER_ID, email="v3user@x.com", full_name="V3 User",
        is_active=True, is_admin=False, organization_id=ORG_ID, role="estimator",
    )


@pytest_asyncio.fixture(autouse=True)
async def _scope_to_v3_org(db_session):
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _org_user

    async def _scrub():
        # Clean up ALL estimates and related rows for this test user/org
        from sqlalchemy import delete as sa_delete
        result = await db_session.execute(
            select(Estimate.id).where(
                Estimate.created_by == USER_ID,
                Estimate.organization_id == ORG_ID,
            )
        )
        est_ids = [r[0] for r in result.all()]
        if est_ids:
            await db_session.execute(
                sa_delete(EstimateLineItem).where(EstimateLineItem.estimate_id.in_(est_ids))
            )
            await db_session.execute(
                sa_delete(EstimateVersion).where(EstimateVersion.estimate_id.in_(est_ids))
            )
            await db_session.execute(
                sa_delete(Estimate).where(Estimate.id.in_(est_ids))
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


async def _seed_estimate(db, *, estimate_id: int):
    est = Estimate(
        id=estimate_id,
        title="Test Estimate",
        job_type="service",
        status="draft",
        labor_total=100.0,
        materials_total=200.0,
        tax_total=26.75,
        markup_total=50.0,
        misc_total=0.0,
        subtotal=350.0,
        grand_total=376.75,
        confidence_score=0.85,
        confidence_label="HIGH",
        assumptions=["Test assumption"],
        sources=["agent_v3"],
        county="Dallas",
        tax_rate=0.0825,
        organization_id=ORG_ID,
        created_by=USER_ID,
    )
    db.add(est)
    await db.flush()

    db.add(EstimateLineItem(
        estimate_id=estimate_id,
        line_type="labor",
        description="Labor line",
        quantity=1,
        unit="ea",
        unit_cost=100.0,
        total_cost=100.0,
        sort_order=0,
    ))
    db.add(EstimateLineItem(
        estimate_id=estimate_id,
        line_type="material",
        description="Material line",
        quantity=2,
        unit="ea",
        unit_cost=100.0,
        total_cost=200.0,
        sort_order=1,
    ))
    await db.commit()
    return est


class TestListEstimateVersions:
    async def test_list_versions_empty(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=901)
        res = await test_client.get("/api/v3/estimates/901/versions")
        assert res.status_code == 200
        data = res.json()
        assert data == []

    async def test_list_versions_with_snapshots(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=902)
        db_session.add(EstimateVersion(
            estimate_id=902,
            version_number=1,
            snapshot_json={"grand_total": 376.75},
            change_summary="Initial",
        ))
        await db_session.commit()

        res = await test_client.get("/api/v3/estimates/902/versions")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["version_number"] == 1
        assert data[0]["change_summary"] == "Initial"

    async def test_list_versions_not_found(self, test_client: AsyncClient):
        res = await test_client.get("/api/v3/estimates/99999/versions")
        assert res.status_code == 404


class TestDiffEstimateVersion:
    async def test_diff_version_first_version(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=903)
        db_session.add(EstimateVersion(
            estimate_id=903,
            version_number=1,
            snapshot_json={
                "grand_total": 376.75,
                "line_items": [
                    {"description": "Labor line", "quantity": 1, "unit_cost": 100.0},
                    {"description": "Material line", "quantity": 2, "unit_cost": 100.0},
                ],
            },
            change_summary="Initial",
        ))
        await db_session.commit()

        result = await db_session.execute(select(EstimateVersion).where(EstimateVersion.estimate_id == 903))
        version = result.scalar_one()

        res = await test_client.get(f"/api/v3/estimates/903/versions/{version.id}/diff")
        assert res.status_code == 200
        data = res.json()
        assert data["from_version"] == 0
        assert data["to_version"] == 1
        assert data["to_total"] == 376.75
        assert len(data["added_line_items"]) == 2

    async def test_diff_version_with_changes(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=904)
        db_session.add(EstimateVersion(
            estimate_id=904,
            version_number=1,
            snapshot_json={
                "grand_total": 300.0,
                "line_items": [
                    {"description": "Labor line", "quantity": 1, "unit_cost": 100.0},
                ],
            },
            change_summary="V1",
        ))
        db_session.add(EstimateVersion(
            estimate_id=904,
            version_number=2,
            snapshot_json={
                "grand_total": 376.75,
                "line_items": [
                    {"description": "Labor line", "quantity": 1, "unit_cost": 100.0},
                    {"description": "Material line", "quantity": 2, "unit_cost": 100.0},
                ],
            },
            change_summary="V2",
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(EstimateVersion).where(EstimateVersion.version_number == 2, EstimateVersion.estimate_id == 904)
        )
        version = result.scalar_one()

        res = await test_client.get(f"/api/v3/estimates/904/versions/{version.id}/diff")
        assert res.status_code == 200
        data = res.json()
        assert data["from_version"] == 1
        assert data["to_version"] == 2
        assert data["total_delta"] == 76.75
        assert len(data["added_line_items"]) == 1
        assert data["added_line_items"][0]["description"] == "Material line"


class TestBranchEstimate:
    async def test_branch_estimate(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=901)
        res = await test_client.post(
            "/api/v3/estimates/901/branch",
            json={"title": "Branched Estimate", "notes": "Test branch"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Branched Estimate"
        assert data["branch_id"] is not None
        assert data["branch_id"] != ""
        assert data["status"] == "draft"
        assert len(data["line_items"]) == 2

    async def test_branch_estimate_default_title(self, test_client: AsyncClient, db_session):
        await _seed_estimate(db_session, estimate_id=902)
        res = await test_client.post(
            "/api/v3/estimates/902/branch",
            json={},
        )
        assert res.status_code == 200
        data = res.json()
        assert "(branch)" in data["title"]

    async def test_branch_not_found(self, test_client: AsyncClient):
        res = await test_client.post("/api/v3/estimates/99999/branch", json={})
        assert res.status_code == 404
