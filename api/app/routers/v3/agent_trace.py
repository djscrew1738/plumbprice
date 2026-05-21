"""
Agent Trace API v3 — Retrieve tool call traces and reasoning for estimates.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.estimates import Estimate
from app.models.agent_tool_calls import AgentToolCall

router = APIRouter()


@router.get("/estimates/{estimate_id}")
async def get_estimate_trace(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full agent trace for an estimate — tool calls, reasoning, latencies."""
    # Verify estimate ownership
    stmt = select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None))
    result = await db.execute(stmt)
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    if estimate.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    # Fetch tool calls
    stmt = select(AgentToolCall).where(AgentToolCall.estimate_id == estimate_id).order_by(AgentToolCall.created_at)
    result = await db.execute(stmt)
    tool_calls = result.scalars().all()

    return {
        "estimate_id": estimate_id,
        "agent_trace": estimate.agent_trace,
        "market_adjustment_applied": estimate.market_adjustment_applied,
        "confidence_components": estimate.confidence_components,
        "tool_calls": [
            {
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "result": tc.result,
                "latency_ms": tc.latency_ms,
                "created_at": tc.created_at.isoformat() if tc.created_at else None,
            }
            for tc in tool_calls
        ],
    }


@router.get("/estimates/{estimate_id}/tool-calls")
async def list_tool_calls(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List individual tool calls for an estimate."""
    stmt = select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None))
    result = await db.execute(stmt)
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    if estimate.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    stmt = select(AgentToolCall).where(AgentToolCall.estimate_id == estimate_id).order_by(AgentToolCall.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()
