"""
Phase 5 — Autonomous Customer Agent.

Public, unauthenticated quote widget. Hard-coded guardrails so this can sit on
the marketing site without leaking margin or booking work outside our scope.

Workflow:
    1. Visitor types a message ("how much for a new toilet?") plus optional
       contact info (name/phone/email) and ZIP/county.
    2. We run their message through the normal chat agent (`process_chat_message`).
    3. We apply guardrails:
         - task_code must be in `public_agent_allowed_tasks`
         - grand_total must be <= `public_agent_max_total_usd`
         - confidence must not be "low"
    4. If guardrails pass → return the priced draft.
       If not → return a polite "we'll have a tech call you" message.
    5. Either way: if contact info was supplied, we persist a Project at
       `status="lead"` and (when priced) attach the estimate, so Cory sees
       every conversation in the pipeline.

Rate limiting is by client IP via slowapi.
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.limiter import limiter
from app.database import get_db
from app.models.projects import Project, ProjectActivity
from app.services.agent import process_chat_message
from app.services.estimate_service import persist_estimate

logger = structlog.get_logger()
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────


class PublicCustomer(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)
    address: Optional[str] = Field(default=None, max_length=500)
    zip_code: Optional[str] = Field(default=None, max_length=10)


class PublicQuoteRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=1500)
    county: Optional[str] = Field(default=None, max_length=100)
    customer: Optional[PublicCustomer] = None


class PublicQuoteEstimate(BaseModel):
    task_code: Optional[str]
    grand_total: float
    labor_total: float
    materials_total: float
    tax_total: float
    confidence_label: Optional[str]


class PublicQuoteResponse(BaseModel):
    status: str  # "ok" | "lead_only" | "out_of_scope" | "uncertain"
    answer: str
    task_code: Optional[str] = None
    estimate: Optional[PublicQuoteEstimate] = None
    lead_id: Optional[int] = None
    follow_up_required: bool = False


# ── Guardrail helpers ──────────────────────────────────────────────────────


def _allowed_task_set() -> set[str]:
    raw = settings.public_agent_allowed_tasks or ""
    return {t.strip().upper() for t in raw.split(",") if t.strip()}


def _passes_guardrails(task_code: Optional[str], grand_total: float, confidence_label: Optional[str]):
    """
    Returns (ok: bool, reason: str). `reason` is the short tag that drives
    which canned response we send back.
    """
    if not task_code:
        return False, "uncertain"
    if task_code.upper() not in _allowed_task_set():
        return False, "out_of_scope"
    if grand_total > settings.public_agent_max_total_usd:
        return False, "too_large"
    if (confidence_label or "").lower() in {"low", "very_low"}:
        return False, "uncertain"
    return True, "ok"


# ── Lead capture ───────────────────────────────────────────────────────────


async def _capture_lead(
    db: AsyncSession,
    *,
    customer: Optional[PublicCustomer],
    message: str,
    county: Optional[str],
    estimate_result,
    note: str,
) -> Optional[int]:
    """Create or update a `lead` Project for this visitor, if they gave contact info."""
    if customer is None or (not customer.email and not customer.phone):
        return None

    email_lower = (customer.email or "").strip().lower()
    project: Optional[Project] = None
    if email_lower:
        existing_q = await db.execute(
            select(Project).where(
                func.lower(Project.customer_email) == email_lower,
                Project.deleted_at.is_(None),
            ).limit(1)
        )
        project = existing_q.scalar_one_or_none()

    if project is None:
        project = Project(
            name=(customer.name or customer.email or customer.phone or "Public widget lead")[:255],
            job_type="service",
            status="lead",
            customer_name=customer.name,
            customer_email=(customer.email or None),
            customer_phone=customer.phone,
            address=customer.address,
            zip_code=customer.zip_code,
            county=county or "Dallas",
            city=county or "Dallas",
            notes=f"[public widget] {message[:1500]}",
            created_by=None,  # public widget has no user
            organization_id=None,
        )
        db.add(project)
        await db.flush()

    db.add(ProjectActivity(
        project_id=project.id,
        actor_user_id=None,
        kind="public_widget_message",
        payload={
            "message": message[:1500],
            "answer": note[:1500],
            "county": county,
            "customer_email": (customer.email if customer else None),
            "customer_phone": (customer.phone if customer else None),
        },
    ))
    await db.flush()

    if estimate_result is not None:
        try:
            await persist_estimate(
                db=db,
                result=estimate_result,
                title=f"Public widget — {message[:60]}",
                county=county or "Dallas",
                preferred_supplier=None,
                chat_context=message,
                source="public_widget",
                created_by=None,
                organization_id=None,
                project_id=project.id,
            )
        except Exception as e:
            # Don't fail the public response if persistence has a hiccup —
            # the lead row is the critical record.
            logger.warning("public_agent.persist_estimate_failed",
                           project_id=project.id, error=str(e))

    return project.id


# ── Endpoint ───────────────────────────────────────────────────────────────


@router.post("/quote", response_model=PublicQuoteResponse)
@limiter.limit(f"{settings.public_agent_rate_per_minute}/minute")
async def public_quote(
    request: Request,
    body: PublicQuoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public, unauthenticated quote endpoint for the marketing-site widget.
    """
    if not settings.public_agent_enabled:
        raise HTTPException(status_code=503, detail="Public quote widget is disabled")

    client_ip = (request.client.host if request.client else "?") or "?"
    logger.info("public_agent.request",
                ip=client_ip, msg_chars=len(body.message), county=body.county)

    result = await process_chat_message(
        message=body.message,
        county=body.county or None,
        preferred_supplier=None,
        job_type=None,
        history=None,
        db=db,
        user_id=None,
    )

    estimate_result = result.pop("_estimate_result", None)
    task_code = (getattr(estimate_result, "template_code", None) if estimate_result else None)
    answer = result.get("answer", "")
    confidence_label = (
        getattr(estimate_result, "confidence_label", None) if estimate_result else None
    )
    grand_total = float(getattr(estimate_result, "grand_total", 0.0) or 0.0) if estimate_result else 0.0

    ok, reason = _passes_guardrails(task_code, grand_total, confidence_label)

    estimate_summary: Optional[PublicQuoteEstimate] = None
    response_status = "ok" if ok else reason
    follow_up = False

    if ok and estimate_result is not None:
        estimate_summary = PublicQuoteEstimate(
            task_code=task_code,
            grand_total=grand_total,
            labor_total=float(getattr(estimate_result, "labor_total", 0.0) or 0.0),
            materials_total=float(getattr(estimate_result, "materials_total", 0.0) or 0.0),
            tax_total=float(getattr(estimate_result, "tax_total", 0.0) or 0.0),
            confidence_label=confidence_label,
        )
        public_answer = (
            f"{answer}\n\n"
            "This is an instant estimate based on typical DFW jobs. "
            "A licensed plumber will confirm the price before any work begins."
        )
    else:
        follow_up = True
        if reason == "too_large":
            public_answer = (
                "Thanks — that sounds like a larger project than our instant-quote "
                "tool can handle. Leave your contact info below and a CTL Plumbing "
                "estimator will reach out within one business day."
            )
        elif reason == "out_of_scope":
            public_answer = (
                "We do handle that, but the quote depends on conditions on site. "
                "Drop your contact info and we'll have a plumber reach out shortly."
            )
        else:  # uncertain / no task
            public_answer = (
                "I'm not sure I have enough detail to price this confidently. "
                "Share your contact info and we'll have a plumber follow up — "
                "it's free and usually same-day."
            )

    lead_id = await _capture_lead(
        db,
        customer=body.customer,
        message=body.message,
        county=body.county,
        estimate_result=estimate_result if ok else None,
        note=public_answer,
    )
    await db.commit()

    logger.info("public_agent.response",
                ip=client_ip, status=response_status, task_code=task_code,
                grand_total=grand_total, lead_id=lead_id)

    return PublicQuoteResponse(
        status=response_status,
        answer=public_answer,
        task_code=task_code,
        estimate=estimate_summary,
        lead_id=lead_id,
        follow_up_required=follow_up,
    )


@router.get("/quote/config")
async def public_quote_config():
    """
    Lightweight metadata so the marketing-site widget can branch its UI
    (disable when off, show "max ticket size" copy, etc.).
    """
    return {
        "enabled": settings.public_agent_enabled,
        "max_total_usd": settings.public_agent_max_total_usd,
        "allowed_task_count": len(_allowed_task_set()),
        "rate_per_minute": settings.public_agent_rate_per_minute,
    }
