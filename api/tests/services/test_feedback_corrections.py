"""Tests for feedback_corrections service."""
import pytest
import pytest_asyncio
from sqlalchemy import select, delete

from app.services.feedback_corrections import (
    analyze_task_code_feedback,
    generate_recommendation_from_feedback,
    _get_primary_task_code,
)
from app.models.estimates import Estimate, EstimateFeedback, EstimateLineItem
from app.models.pricing_intelligence import PricingRecommendation
from app.models.users import User


@pytest_asyncio.fixture
async def sample_estimate(db_session):
    user = User(
        email="feedback_test@example.com",
        hashed_password="$2b$12$testtesttesttesttesttesttesttesttesttesttesttesttestt",
        full_name="Feedback Test",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()

    est = Estimate(
        title="Test Estimate",
        job_type="service",
        status="draft",
        grand_total=1000.0,
        labor_total=400.0,
        materials_total=400.0,
        tax_total=82.5,
        markup_total=100.0,
        misc_total=17.5,
        subtotal=917.5,
        created_by=user.id,
        county="Dallas",
    )
    db_session.add(est)
    await db_session.flush()

    li = EstimateLineItem(
        estimate_id=est.id,
        line_type="labor",
        description="WH_40G_GAS_STANDARD",
        quantity=1,
        unit="ea",
        unit_cost=400.0,
        total_cost=400.0,
        trace_json={"task_code": "WH_40G_GAS_STANDARD"},
    )
    db_session.add(li)
    await db_session.flush()

    est_id = est.id
    user_id = user.id
    yield {"id": est_id, "user_id": user_id}

    # Cleanup — use captured IDs, not ORM object (avoids lazy-load after commit)
    await db_session.execute(delete(EstimateLineItem).where(EstimateLineItem.estimate_id == est_id))
    await db_session.execute(delete(EstimateFeedback).where(EstimateFeedback.estimate_id == est_id))
    await db_session.execute(delete(Estimate).where(Estimate.id == est_id))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.execute(delete(PricingRecommendation).where(PricingRecommendation.task_code == "WH_40G_GAS_STANDARD"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_analyze_task_code_feedback_empty(db_session):
    stats = await analyze_task_code_feedback(db_session, "WH_40G_GAS_STANDARD")
    assert stats["up_count"] == 0
    assert stats["down_count"] == 0
    assert stats["total"] == 0
    assert stats["threshold_met"] is False


@pytest.mark.asyncio
async def test_analyze_task_code_feedback_with_votes(db_session, sample_estimate):
    # Add down votes
    for _ in range(3):
        db_session.add(EstimateFeedback(
            estimate_id=sample_estimate["id"],
            user_id=sample_estimate["user_id"],
            vote="down",
        ))
    # Add 1 up vote
    db_session.add(EstimateFeedback(
        estimate_id=sample_estimate["id"],
        user_id=sample_estimate["user_id"],
        vote="up",
    ))
    await db_session.commit()

    stats = await analyze_task_code_feedback(db_session, "WH_40G_GAS_STANDARD")
    assert stats["up_count"] == 1
    assert stats["down_count"] == 3
    assert stats["total"] == 4
    assert stats["down_ratio"] == 0.75
    assert stats["threshold_met"] is True


@pytest.mark.asyncio
async def test_generate_recommendation_from_feedback(db_session, sample_estimate):
    # Add enough down votes to trigger threshold
    for _ in range(3):
        db_session.add(EstimateFeedback(
            estimate_id=sample_estimate["id"],
            user_id=sample_estimate["user_id"],
            vote="down",
        ))
    await db_session.commit()

    rec = await generate_recommendation_from_feedback(
        db_session, "WH_40G_GAS_STANDARD"
    )
    assert rec is not None
    assert rec.task_code == "WH_40G_GAS_STANDARD"
    assert rec.source == "feedback"
    assert rec.status == "pending"
    assert rec.recommendation_type == "feedback_review"
    assert rec.sample_count == 3

    # Verify it's in the DB
    result = await db_session.execute(
        select(PricingRecommendation).where(PricingRecommendation.id == rec.id)
    )
    db_rec = result.scalar_one()
    assert db_rec.source == "feedback"


@pytest.mark.asyncio
async def test_generate_recommendation_updates_existing(db_session, sample_estimate):
    # Create initial recommendation
    for _ in range(3):
        db_session.add(EstimateFeedback(
            estimate_id=sample_estimate["id"],
            user_id=sample_estimate["user_id"],
            vote="down",
        ))
    await db_session.commit()

    est_id = sample_estimate["id"]
    user_id = sample_estimate["user_id"]

    rec1 = await generate_recommendation_from_feedback(
        db_session, "WH_40G_GAS_STANDARD"
    )
    assert rec1 is not None

    # Add more votes and call again
    for _ in range(2):
        db_session.add(EstimateFeedback(
            estimate_id=est_id,
            user_id=user_id,
            vote="down",
        ))
    await db_session.commit()

    rec2 = await generate_recommendation_from_feedback(
        db_session, "WH_40G_GAS_STANDARD"
    )
    assert rec2 is not None
    assert rec2.id == rec1.id
    assert rec2.sample_count == 5


@pytest.mark.asyncio
async def test_get_primary_task_code(db_session, sample_estimate):
    code = await _get_primary_task_code(db_session, sample_estimate["id"])
    assert code == "WH_40G_GAS_STANDARD"
