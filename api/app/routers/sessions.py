"""Chat session persistence — list, get, and delete conversation threads."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.sessions import ChatSession, ChatMessage
from app.models.users import User

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent chat sessions for the current user, newest first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "county": s.county,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a session with its full message history."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "title": session.title,
        "county": session.county,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "estimate_id": m.estimate_id,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    }


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
