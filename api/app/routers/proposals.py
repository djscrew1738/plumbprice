from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate, Proposal
from app.models.users import User
from app.services.proposal_service import send_proposal_email, render_pdf, proposal_status
from app.core.limiter import limiter

logger = structlog.get_logger()
router = APIRouter()


class SendProposalRequest(BaseModel):
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    message: Optional[str] = None


async def _load_estimate_for_user(
    db: AsyncSession, estimate_id: int, current_user: User
) -> Estimate:
    """Fetch an estimate if the caller owns it (org or creator); else 404."""
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
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.post("/{estimate_id}/send")
@limiter.limit("20/hour")
async def send_proposal(
    request: Request,
    estimate_id: int,
    body: SendProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Email a proposal to a client. Records the send in proposals table."""
    await _load_estimate_for_user(db, estimate_id, current_user)
    user_org = getattr(current_user, "organization_id", None)

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


@router.get("/{estimate_id}/pdf")
async def download_proposal_pdf(
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Render the current estimate as a PDF proposal. Same ownership check as send."""
    estimate = await _load_estimate_for_user(db, estimate_id, current_user)
    try:
        pdf_bytes = render_pdf(estimate)
    except Exception as e:
        logger.error("proposal.pdf_failed", estimate_id=estimate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to render PDF")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="estimate-{estimate_id}.pdf"',
        },
    )


@router.get("/{estimate_id}/sends")
async def list_proposal_sends(
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all send records for an estimate."""
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
            "public_token": p.public_token,
            "token_expires_at": p.token_expires_at,
            "opened_at": p.opened_at,
            "accepted_at": p.accepted_at,
            "declined_at": p.declined_at,
            "client_signature": p.client_signature,
            "status": proposal_status(p),
        }
        for p in proposals
    ]
