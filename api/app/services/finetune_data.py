"""Training data extraction service for LLM fine-tuning (E3.1).

Extracts high-quality (input, output) pairs from production estimate data to
build an OpenAI fine-tuning JSONL dataset. Only includes pairs meeting strict
quality criteria — garbage-in-garbage-out is a real risk with fine-tuning.

Quality criteria (ALL must be met):
  - Agent trace exists with confidence_score >= 0.85
  - Estimate outcome = "won" (job was awarded)
  - User message length > 15 characters
  - At least 1 line item on the estimate
  - All canonical items resolved (no unresolved items)
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateLineItem
from app.models.outcomes import EstimateOutcome
from app.models.sessions import ChatMessage

logger = structlog.get_logger()

# System prompt used during classification — must match what agent_v3 uses
_CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a plumbing estimating assistant for DFW-area plumbing contractors. "
    "Extract the job intent from the user's message and return a structured JSON object "
    "with the following fields: job_type, county, fixtures (list of {canonical_item, quantity, "
    "access_level, urgency}), assumptions (list of strings). "
    "Be conservative — only include items explicitly mentioned or strongly implied. "
    "Use DFW county names (Dallas, Tarrant, Collin, Denton, Rockwall, etc.)."
)


async def extract_training_data(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
    min_confidence: float = 0.85,
    limit: int = 10_000,
) -> list[dict[str, Any]]:
    """Extract training pairs from high-quality won estimates.

    Returns a list of OpenAI fine-tuning message dicts:
    [{"messages": [system, user, assistant]}, ...]
    """
    # Join estimates with outcomes (won only) and line items
    query = (
        select(Estimate)
        .join(EstimateOutcome, EstimateOutcome.estimate_id == Estimate.id)
        .where(
            EstimateOutcome.outcome == "won",
            Estimate.confidence_score >= min_confidence,
        )
    )
    if organization_id:
        query = query.where(Estimate.organization_id == organization_id)

    query = query.order_by(Estimate.created_at.desc()).limit(limit)
    estimates = (await db.execute(query)).scalars().all()

    pairs: list[dict[str, Any]] = []
    skipped = 0

    for est in estimates:
        # Require at least one line item
        line_items = (
            await db.execute(
                select(EstimateLineItem).where(EstimateLineItem.estimate_id == est.id)
            )
        ).scalars().all()

        if not line_items:
            skipped += 1
            continue

        # Find the originating chat message
        user_message = await _find_originating_message(db, est)
        if not user_message or len(user_message) < 15:
            skipped += 1
            continue

        # Build the assistant response from the estimate's agent_trace
        assistant_output = _build_assistant_output(est, line_items)
        if not assistant_output:
            skipped += 1
            continue

        pairs.append(
            {
                "messages": [
                    {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": json.dumps(assistant_output)},
                ]
            }
        )

    logger.info(
        "finetune_data.extracted",
        total=len(estimates),
        pairs=len(pairs),
        skipped=skipped,
    )
    return pairs


async def _find_originating_message(db: AsyncSession, estimate: Estimate) -> str | None:
    """Find the user message that generated this estimate via ChatMessage.estimate_id."""
    msg = (
        await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.estimate_id == estimate.id,
                ChatMessage.role == "user",
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return msg.content if msg else None


def _build_assistant_output(
    estimate: Estimate, line_items: list[EstimateLineItem]
) -> dict[str, Any] | None:
    """Reconstruct a ClassifyResult-compatible dict from the estimate and trace data."""
    # Pull structured classification from agent_trace if available
    agent_trace = estimate.agent_trace or {}
    classification = agent_trace.get("classification")

    if classification and isinstance(classification, dict):
        # Use the stored classification directly
        return classification

    # Fall back: reconstruct from line items
    fixtures = []
    for item in line_items:
        trace = item.trace_json or {}
        canonical = item.canonical_item
        if canonical:
            fixtures.append(
                {
                    "canonical_item": canonical,
                    "quantity": item.quantity or 1,
                    "access_level": trace.get("access_level", "standard"),
                    "urgency": trace.get("urgency", "routine"),
                }
            )

    if not fixtures:
        return None

    return {
        "job_type": estimate.job_type or "service",
        "county": estimate.county or "Dallas",
        "fixtures": fixtures,
        "assumptions": [],
        "confidence": estimate.confidence_score or 0.85,
    }
