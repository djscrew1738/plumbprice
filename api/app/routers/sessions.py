"""Chat session persistence — list, get, and delete conversation threads."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
        .options(selectinload(ChatSession.messages))
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
            "message_count": len(s.messages),
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
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(
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


@router.post("/{session_id}/clone", status_code=201)
async def clone_session(session_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Clone a chat session (no messages)."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Session not found")

    new_session = ChatSession(
        title=f"Copy of {original.title}",
        county=original.county,
        user_id=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
    )
    db.add(new_session)
    await db.flush()
    await db.commit()
    return {
        "id": new_session.id,
        "title": new_session.title,
        "county": new_session.county,
        "created_at": new_session.created_at,
        "updated_at": new_session.updated_at,
        "message_count": 0,
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


# ── d1: multi-modal attachments ─────────────────────────────────────────────
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.models.sessions import ChatAttachment


VALID_KINDS = {"photo", "voice", "blueprint", "estimate", "document"}


class AttachmentCreate(BaseModel):
    kind: str = Field(..., description="photo|voice|blueprint|estimate|document")
    ref_id: Optional[int] = None
    message_id: Optional[int] = None
    status: Literal["requested", "attached", "failed"] = "attached"
    note: Optional[str] = None


class AttachmentUpdate(BaseModel):
    ref_id: Optional[int] = None
    status: Optional[Literal["requested", "attached", "failed"]] = None
    note: Optional[str] = None


def _serialize_attachment(a: ChatAttachment) -> dict:
    return {
        "id": a.id,
        "session_id": a.session_id,
        "message_id": a.message_id,
        "kind": a.kind,
        "ref_id": a.ref_id,
        "status": a.status,
        "note": a.note,
        "created_at": a.created_at,
    }


async def _owned_session(
    db: AsyncSession, session_id: int, user: User
) -> ChatSession:
    res = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


@router.get("/{session_id}/attachments")
async def list_attachments(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_session(db, session_id, current_user)
    res = await db.execute(
        select(ChatAttachment)
        .where(ChatAttachment.session_id == session_id)
        .order_by(ChatAttachment.created_at)
    )
    return [_serialize_attachment(a) for a in res.scalars().all()]


@router.post("/{session_id}/attachments", status_code=201)
async def create_attachment(
    session_id: int,
    body: AttachmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach (or request) a multi-modal artifact for a chat session.

    The agent uses status='requested' with no ref_id to ask the user
    for a photo / voice clip mid-conversation; the client uploads the
    artifact and PATCHes ref_id + status='attached' once it's persisted.
    """
    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=422, detail=f"invalid kind '{body.kind}'")
    await _owned_session(db, session_id, current_user)
    att = ChatAttachment(
        session_id=session_id,
        message_id=body.message_id,
        kind=body.kind,
        ref_id=body.ref_id,
        status=body.status,
        note=body.note,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return _serialize_attachment(att)


@router.patch("/{session_id}/attachments/{attachment_id}")
async def update_attachment(
    session_id: int,
    attachment_id: int,
    body: AttachmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_session(db, session_id, current_user)
    res = await db.execute(
        select(ChatAttachment).where(
            ChatAttachment.id == attachment_id,
            ChatAttachment.session_id == session_id,
        )
    )
    att = res.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if body.ref_id is not None:
        att.ref_id = body.ref_id
    if body.status is not None:
        att.status = body.status
    if body.note is not None:
        att.note = body.note
    await db.commit()
    await db.refresh(att)
    return _serialize_attachment(att)


@router.delete("/{session_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    session_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_session(db, session_id, current_user)
    res = await db.execute(
        select(ChatAttachment).where(
            ChatAttachment.id == attachment_id,
            ChatAttachment.session_id == session_id,
        )
    )
    att = res.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await db.delete(att)
    await db.commit()
