"""Admin review endpoints for public-agent audit log (Track D5).

* GET  /api/v1/admin/public-agent/audits         — paginated list
       query: ?min_score=0.5&unreviewed=1&limit=50
* POST /api/v1/admin/public-agent/audits/{id}/review
       body: {note?: str}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.public_agent_audit import PublicAgentAudit
from app.models.users import User

logger = structlog.get_logger()
router = APIRouter()


class ReviewBody(BaseModel):
    note: Optional[str] = None


def _serialize(a: PublicAgentAudit) -> dict:
    return {
        "id": a.id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "client_ip": a.client_ip,
        "user_agent": a.user_agent,
        "message": a.message,
        "county": a.county,
        "customer_email": a.customer_email,
        "status": a.status,
        "task_code": a.task_code,
        "grand_total": a.grand_total,
        "lead_id": a.lead_id,
        "anomaly_score": a.anomaly_score,
        "anomaly_flags": a.anomaly_flags or [],
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "reviewed_by": a.reviewed_by,
        "review_note": a.review_note,
    }


@router.get("/audits")
async def list_audits(
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    unreviewed: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")
    q = select(PublicAgentAudit).where(PublicAgentAudit.anomaly_score >= min_score)
    if unreviewed:
        q = q.where(PublicAgentAudit.reviewed_at.is_(None))
    q = q.order_by(PublicAgentAudit.anomaly_score.desc(), PublicAgentAudit.created_at.desc()).limit(limit)
    res = await db.execute(q)
    rows = res.scalars().all()
    return [_serialize(r) for r in rows]


@router.post("/audits/{audit_id}/review")
async def mark_reviewed(
    audit_id: int,
    body: ReviewBody = ReviewBody(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await db.execute(select(PublicAgentAudit).where(PublicAgentAudit.id == audit_id))
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    audit.reviewed_at = datetime.now(timezone.utc)
    audit.reviewed_by = current_user.id
    if body.note is not None:
        audit.review_note = body.note
    await db.commit()
    return _serialize(audit)
