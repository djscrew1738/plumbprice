"""Tests for task_code_embeddings semantic retrieval."""
from __future__ import annotations

import pytest

from app.models.sessions import ChatEmbedding
from app.services.task_code_embeddings import task_code_embedding_service, _COMMON_TASK_CODES


@pytest.mark.asyncio
async def test_search_similar_returns_common_codes_on_empty_db(db_session):
    """When no embeddings exist, search_similar falls back to common codes."""
    result = await task_code_embedding_service.search_similar(
        db_session, "replace toilet", top_k=20
    )
    assert isinstance(result, list)
    assert len(result) >= len(_COMMON_TASK_CODES)
    # All returned codes should be uppercase task codes
    assert all(c.isupper() for c in result)
    assert "TOILET_REPLACE_STANDARD" in result


@pytest.mark.asyncio
async def test_search_similar_with_embeddings(db_session):
    """When embeddings exist, search_similar returns them + common codes."""
    db_session.add(
        ChatEmbedding(
            task_code="TOILET_COMFORT_HEIGHT",
            description="Comfort height toilet installation",
            embedding=[0.1] * 1024,
            model_name="test-model",
        )
    )
    db_session.add(
        ChatEmbedding(
            task_code="WH_50G_GAS_STANDARD",
            description="50 gallon gas water heater standard",
            embedding=[0.2] * 1024,
            model_name="test-model",
        )
    )
    await db_session.commit()

    result = await task_code_embedding_service.search_similar(
        db_session, "replace toilet", top_k=5
    )
    assert "TOILET_COMFORT_HEIGHT" in result
    # Common codes should still be present
    assert "TOILET_REPLACE_STANDARD" in result


@pytest.mark.asyncio
async def test_build_description():
    """Description builder combines task code, name, category, and tags."""
    from app.services.labor_engine import LaborTemplateData

    template = LaborTemplateData(
        code="TOILET_REPLACE_STANDARD",
        name="Standard Toilet Replacement",
        category="service",
        base_hours=2.5,
        tags=["residential", "bathroom"],
        notes="Includes wax ring and supply line",
    )
    desc = task_code_embedding_service.build_description(template)
    assert "TOILET REPLACE STANDARD" in desc
    assert "Standard Toilet Replacement" in desc
    assert "category: service" in desc
    assert "tags: residential, bathroom" in desc
    assert "Includes wax ring and supply line" in desc


@pytest.mark.asyncio
async def test_seed_all_skips_existing(db_session):
    """seed_all skips items that already have embeddings."""
    db_session.add(
        ChatEmbedding(
            task_code="TOILET_REPLACE_STANDARD",
            description="Standard toilet replacement",
            embedding=[0.1] * 1024,
            model_name="test-model",
        )
    )
    await db_session.commit()

    # Mock embed to avoid Ollama dependency
    original_embed = task_code_embedding_service.embed
    async def _mock_embed(text: str) -> list[float]:
        return [0.5] * 1024
    task_code_embedding_service.embed = _mock_embed

    try:
        stats = await task_code_embedding_service.seed_all(db_session)
        assert stats["skipped"] >= 1
        assert stats["errors"] == 0
    finally:
        task_code_embedding_service.embed = original_embed


@pytest.mark.asyncio
async def test_seed_all_handles_embed_failure(db_session):
    """seed_all counts errors when embedding fails."""
    # Clean up from previous tests in this session-scoped DB
    from sqlalchemy import delete
    from app.models.sessions import ChatEmbedding
    await db_session.execute(delete(ChatEmbedding))
    await db_session.commit()

    original_embed = task_code_embedding_service.embed
    async def _mock_embed_fail(text: str) -> list[float]:
        return []
    task_code_embedding_service.embed = _mock_embed_fail

    try:
        stats = await task_code_embedding_service.seed_all(db_session)
        assert stats["created"] == 0
        assert stats["errors"] >= 1
    finally:
        task_code_embedding_service.embed = original_embed
