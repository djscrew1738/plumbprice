from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate
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
    # Verify the estimate exists and belongs to the caller's org (or they created it).
    # This prevents cross-org sends and information disclosure via 500 errors.
    existing = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = existing.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    user_org = getattr(current_user, "organization_id", None)
    owns_estimate = (
        (estimate.organization_id is not None and estimate.organization_id == user_org)
        or estimate.created_by == current_user.id
        or getattr(current_user, "is_admin", False)
    )
    if not owns_estimate:
        # Use 404 not 403 to avoid leaking estimate existence
        raise HTTPException(status_code=404, detail="Estimate not found")

    result = await send_proposal_email(
        db=db,
        estimate_id=estimate_id,
        recipient_email=str(body.recipient_email),
        recipient_name=body.recipient_name,
        message=body.message,
        sent_by_user_id=current_user.id,
        organization_id=user_org,
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
    from app.models.estimates import Proposal

    # Scope to caller's org; admins see their own-org records via same filter.
    user_org = getattr(current_user, "organization_id", None)

    result = await db.execute(
        select(Proposal)
        .where(
            Proposal.estimate_id == estimate_id,
            Proposal.organization_id == user_org,
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
