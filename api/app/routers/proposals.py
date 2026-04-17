from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.users import User
from app.services.proposal_service import send_proposal_email

logger = structlog.get_logger()
router = APIRouter()


class SendProposalRequest(BaseModel):
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    message: Optional[str] = None


@router.post("/{estimate_id}/send")
async def send_proposal(
    estimate_id: int,
    body: SendProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Email a proposal to a client. Records the send in proposals table."""
    result = await send_proposal_email(
        db=db,
        estimate_id=estimate_id,
        recipient_email=str(body.recipient_email),
        recipient_name=body.recipient_name,
        message=body.message,
        sent_by_user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send proposal"))
    return result


@router.get("/{estimate_id}/sends")
async def list_proposal_sends(
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all send records for an estimate."""
    from sqlalchemy import select
    from app.models.estimates import Proposal

    result = await db.execute(
        select(Proposal)
        .where(
            Proposal.estimate_id == estimate_id,
            Proposal.organization_id == current_user.organization_id,
        )
        .order_by(Proposal.created_at.desc())
    )
    proposals = result.scalars().all()
    return [
        {
            "id": p.id,
            "recipient_email": p.recipient_email,
            "recipient_name": p.recipient_name,
            "sent_at": p.sent_at,
            "created_at": p.created_at,
        }
        for p in proposals
    ]
