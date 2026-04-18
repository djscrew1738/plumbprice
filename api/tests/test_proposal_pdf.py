"""Tests for the authenticated proposal PDF endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate
from app.models.users import User
from app.core.auth import get_current_user
from app.main import app

pytestmark = pytest.mark.asyncio


async def _make_estimate(db_session: AsyncSession, *, created_by: int = 1,
                         organization_id: int | None = None) -> Estimate:
    est = Estimate(
        title="PDF Estimate",
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
        created_by=created_by,
        organization_id=organization_id,
    )
    db_session.add(est)
    await db_session.commit()
    await db_session.refresh(est)
    return est


async def test_pdf_endpoint_returns_pdf_bytes(test_client: AsyncClient, db_session):
    est = await _make_estimate(db_session)
    r = await test_client.get(f"/api/v1/proposals/{est.id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


async def test_pdf_endpoint_404_for_non_owner(test_client: AsyncClient, db_session):
    # Estimate owned by someone else, scoped to a different org; caller is non-admin
    est = await _make_estimate(db_session, created_by=999, organization_id=42)

    async def other_user():
        return User(id=5, email="other@example.com", full_name="Other", is_active=True, is_admin=False,
                    organization_id=7)

    app.dependency_overrides[get_current_user] = other_user
    try:
        r = await test_client.get(f"/api/v1/proposals/{est.id}/pdf")
        assert r.status_code == 404
    finally:
        # Restore default admin override from conftest
        from tests.conftest import override_get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
