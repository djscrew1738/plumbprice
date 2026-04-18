"""Unauthenticated customer-facing proposal routes.

These endpoints serve the public proposal viewer and acceptance loop.
Security hinges on an unguessable ``public_token`` emitted when a proposal is
sent. Tokens expire (``token_expires_at``); expired or invalid tokens yield a
404 to avoid leaking existence. Accept/decline are idempotent.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.models.estimates import Estimate, Proposal
from app.models.users import User
from app.models.projects import Project
from app.services.proposal_service import proposal_status, send_notification_email
from app.services import activity_service

logger = structlog.get_logger()
router = APIRouter()


class AcceptRequest(BaseModel):
    signature: str = Field(..., min_length=1, max_length=200)


class DeclineRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=2000)


def _client_ip(request: Request) -> Optional[str]:
    """Return the best-guess client IP, honouring X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # Last hop in the chain is typically the closest proxy's view of the client.
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1][:45]
    client = request.client
    return client.host[:45] if client and client.host else None


def _user_agent(request: Request) -> Optional[str]:
    ua = request.headers.get("user-agent")
    return ua[:500] if ua else None


async def _load_proposal(db: AsyncSession, token: str) -> Proposal:
    """Fetch a proposal by public token or raise 404. Does not check expiry."""
    if not token or len(token) > 64:
        raise HTTPException(status_code=404, detail="Proposal not found")
    result = await db.execute(
        select(Proposal).where(Proposal.public_token == token)
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


def _is_expired(proposal: Proposal) -> bool:
    exp = proposal.token_expires_at
    if exp is None:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)


async def _serialize(proposal: Proposal, estimate_id: int, db: AsyncSession) -> dict:
    from app.models.estimates import EstimateLineItem
    est_res = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = est_res.scalar_one()
    li_res = await db.execute(
        select(EstimateLineItem)
        .where(EstimateLineItem.estimate_id == estimate_id)
        .order_by(EstimateLineItem.sort_order)
    )
    items = li_res.scalars().all()
    line_items = [
        {
            "description": li.description,
            "quantity": li.quantity,
            "unit": li.unit,
            "unit_cost": li.unit_cost,
            "total_cost": li.total_cost,
        }
        for li in items
    ]
    return {
        "token": proposal.public_token,
        "status": proposal_status(proposal),
        "recipient_name": proposal.recipient_name,
        "message": proposal.message,
        "expires_at": proposal.token_expires_at,
        "opened_at": proposal.opened_at,
        "accepted_at": proposal.accepted_at,
        "declined_at": proposal.declined_at,
        "client_signature": proposal.client_signature,
        "estimate": {
            "id": estimate.id,
            "title": estimate.title,
            "job_type": estimate.job_type,
            "county": estimate.county,
            "tax_rate": estimate.tax_rate,
            "labor_total": estimate.labor_total,
            "materials_total": estimate.materials_total,
            "tax_total": estimate.tax_total,
            "subtotal": estimate.subtotal,
            "grand_total": estimate.grand_total,
            "line_items": line_items,
        },
    }


@router.get("/proposals/{token}")
async def get_public_proposal(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Sanitised read view of a proposal. Marks opened_at on first fetch."""
    proposal = await _load_proposal(db, token)
    if _is_expired(proposal) and proposal.accepted_at is None and proposal.declined_at is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    estimate_res = await db.execute(
        select(Estimate).where(Estimate.id == proposal.estimate_id)
    )
    estimate = estimate_res.scalar_one_or_none()
    if estimate is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    estimate_id = estimate.id

    if proposal.opened_at is None:
        proposal.opened_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(proposal)

    return await _serialize(proposal, estimate_id, db)


async def _notify_sender(proposal: Proposal, estimate_title: str, estimate_id: int, event: str) -> None:
    """Email the original sender that the proposal was accepted/declined."""
    try:
        from app.config import settings
        subject = f"Proposal {event} – {estimate_title}"
        signer = proposal.client_signature or proposal.recipient_email
        body = (
            f"<p>Proposal <strong>#{proposal.id}</strong> for estimate "
            f"<strong>{estimate_title}</strong> (#{estimate_id}) was {event} by "
            f"<strong>{signer}</strong>.</p>"
        )
        await send_notification_email(
            to_email=settings.email_from,
            subject=subject,
            html_body=body,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("proposal.notify_sender_failed", error=str(e))


@router.post("/proposals/{token}/accept")
async def accept_public_proposal(
    token: str,
    body: AcceptRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    proposal = await _load_proposal(db, token)

    estimate_res = await db.execute(
        select(Estimate).where(Estimate.id == proposal.estimate_id)
    )
    estimate = estimate_res.scalar_one_or_none()
    if estimate is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    estimate_id = estimate.id
    estimate_project_id = estimate.project_id
    estimate_title = estimate.title

    if proposal.accepted_at is not None:
        # Idempotent — return current state.
        return await _serialize(proposal, estimate_id, db)
    if proposal.declined_at is not None:
        raise HTTPException(status_code=409, detail="Proposal already declined")
    if _is_expired(proposal):
        raise HTTPException(status_code=409, detail="Proposal has expired")

    now = datetime.now(timezone.utc)
    proposal.accepted_at = now
    proposal.client_signature = body.signature.strip()[:200]
    proposal.client_ip = _client_ip(request)
    proposal.client_user_agent = _user_agent(request)
    if proposal.opened_at is None:
        proposal.opened_at = now

    # Log activity if the estimate is tied to a project.
    if estimate_project_id is not None:
        try:
            await activity_service.log(
                db=db,
                project_id=estimate_project_id,
                actor_user_id=None,
                kind="proposal_accepted",
                payload={
                    "proposal_id": proposal.id,
                    "estimate_id": estimate_id,
                    "signature": proposal.client_signature,
                },
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("proposal.accept_activity_failed", error=str(e))

    await db.commit()
    await db.refresh(proposal)

    await _notify_sender(proposal, estimate_title, estimate_id, event="accepted")

    return await _serialize(proposal, estimate_id, db)


@router.post("/proposals/{token}/decline")
async def decline_public_proposal(
    token: str,
    body: DeclineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    proposal = await _load_proposal(db, token)

    estimate_res = await db.execute(
        select(Estimate).where(Estimate.id == proposal.estimate_id)
    )
    estimate = estimate_res.scalar_one_or_none()
    if estimate is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    estimate_id = estimate.id
    estimate_title = estimate.title

    if proposal.declined_at is not None:
        return await _serialize(proposal, estimate_id, db)
    if proposal.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Proposal already accepted")
    if _is_expired(proposal):
        raise HTTPException(status_code=409, detail="Proposal has expired")

    now = datetime.now(timezone.utc)
    proposal.declined_at = now
    proposal.decline_reason = (body.reason or None)
    proposal.client_ip = _client_ip(request)
    proposal.client_user_agent = _user_agent(request)
    if proposal.opened_at is None:
        proposal.opened_at = now

    await db.commit()
    await db.refresh(proposal)

    await _notify_sender(proposal, estimate_title, estimate_id, event="declined")

    return await _serialize(proposal, estimate_id, db)
