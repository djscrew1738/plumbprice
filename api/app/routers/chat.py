import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter  # noqa: F401
from slowapi.util import get_remote_address  # noqa: F401  (kept for compat)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.projects import Project
from app.models.sessions import ChatSession, ChatMessage as ChatMessageModel
from app.models.users import User
from app.schemas.chat import ChatPriceRequest, ChatPriceResponse
from app.services.agent import process_chat_message
from app.services.estimate_service import persist_estimate
from app.services.llm_service import llm_service
from app.core.limiter import limiter

logger = structlog.get_logger()
router = APIRouter()

STREAM_TIMEOUT_SECONDS = 20


async def _upsert_session(
    db: AsyncSession,
    session_id: int | None,
    user_id: int,
    organization_id: int | None,
    user_message: str,
    assistant_answer: str,
    county: str | None,
    estimate_id: int | None,
) -> int:
    """Get-or-create a ChatSession and append the exchange as two ChatMessageModel rows."""
    from sqlalchemy import select

    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
    else:
        session = None

    if session is None:
        session = ChatSession(
            user_id=user_id,
            organization_id=organization_id,
            title=user_message[:80],
            county=county,
        )
        db.add(session)
        await db.flush()  # get session.id before adding messages

    db.add(ChatMessageModel(session_id=session.id, role="user", content=user_message))
    db.add(ChatMessageModel(session_id=session.id, role="assistant", content=assistant_answer, estimate_id=estimate_id))
    return session.id


def build_estimate_breakdown(estimate_result):
    if estimate_result is None:
        return None

    return {
        "labor_total": estimate_result.labor_total,
        "materials_total": estimate_result.materials_total,
        "tax_total": estimate_result.tax_total,
        "markup_total": estimate_result.markup_total,
        "misc_total": estimate_result.misc_total,
        "subtotal": estimate_result.subtotal,
        "grand_total": estimate_result.grand_total,
        "line_items": [
            {
                "line_type": item.line_type,
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
                "supplier": item.supplier,
                "sku": item.sku,
                "canonical_item": item.canonical_item,
                "trace_json": item.trace_json,
            }
            for item in estimate_result.line_items
        ],
    }


async def _resolve_customer_project(
    db: AsyncSession,
    customer,
    project_id: int | None,
    organization_id: int | None,
    created_by: int,
) -> int | None:
    """Auto-create or link a Project based on customer email.

    Returns a project_id (int) or None if no customer email provided.
    If project_id is already supplied, returns it unchanged.
    """
    if project_id is not None:
        return project_id
    if customer is None or not customer.email:
        return None

    email_lower = customer.email.strip().lower()

    # Look up existing lead project with this email in the same org
    query = select(Project).where(
        func.lower(Project.customer_email) == email_lower,
        Project.deleted_at.is_(None),
    )
    if organization_id is not None:
        query = query.where(Project.organization_id == organization_id)
    else:
        query = query.where(Project.created_by == created_by)

    result = await db.execute(query.limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    project = Project(
        name=customer.name or customer.email,
        job_type="service",
        status="lead",
        customer_name=customer.name,
        customer_email=customer.email.strip(),
        customer_phone=customer.phone,
        address=customer.address,
        city="Dallas",
        county="Dallas",
        created_by=created_by,
        organization_id=organization_id,
    )
    db.add(project)
    await db.flush()
    return project.id


@router.post("/price", response_model=ChatPriceResponse)
@limiter.limit("30/minute")
async def chat_price(    request: Request,
    body: ChatPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Main chat pricing endpoint. Requires authentication.
    Rate-limited to 30 requests/minute per IP.
    """
    history = [
        {"role": m.role, "content": m.content}
        for m in (body.history or [])
    ]
    try:
        result = await process_chat_message(
            message=body.message,
            county=body.county or None,
            preferred_supplier=body.preferred_supplier,
            job_type=body.job_type,
            history=history or None,
            db=db,
        )

        estimate_result = result.pop("_estimate_result", None)

        estimate_id = None
        if estimate_result is not None:
            org_id = current_user.organization_id if hasattr(current_user, "organization_id") else None
            resolved_project_id = await _resolve_customer_project(
                db=db,
                customer=body.customer,
                project_id=body.project_id,
                organization_id=org_id,
                created_by=current_user.id,
            )
            estimate = await persist_estimate(
                db=db,
                result=estimate_result,
                title=body.message[:100] or "Chat Estimate",
                county=body.county or "Dallas",
                preferred_supplier=body.preferred_supplier,
                chat_context=body.message,
                source="chat",
                created_by=current_user.id,
                organization_id=org_id,
                project_id=resolved_project_id,
            )
            estimate_id = estimate.id

        answer = result["answer"]
        session_id = await _upsert_session(
            db=db,
            session_id=body.session_id,
            user_id=current_user.id,
            organization_id=getattr(current_user, "organization_id", None),
            user_message=body.message,
            assistant_answer=answer,
            county=body.county,
            estimate_id=estimate_id,
        )
        await db.commit()

        estimate_payload = result.get("estimate")
        if estimate_result is not None:
            estimate_payload = build_estimate_breakdown(estimate_result)

        classified_by = result.get("classification", {}).get("classified_by")

        return ChatPriceResponse(
            answer=answer,
            estimate=estimate_payload,
            estimate_id=estimate_id,
            session_id=session_id,
            confidence=result["confidence"],
            confidence_label=result["confidence_label"],
            assumptions=result.get("assumptions", []),
            sources=result.get("sources", []),
            conversation_id=body.conversation_id,
            job_type_detected=result.get("job_type_detected"),
            template_used=result.get("template_used"),
            classified_by=classified_by,
        )

    except Exception as e:
        logger.error("Chat pricing error", error=str(e), message=body.message, user_id=current_user.id, exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")


@router.post("/price/stream")
@limiter.limit("20/minute")
async def chat_price_stream(
    request: Request,
    body: ChatPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SSE streaming variant of /price.

    Emits three event types:
      event: pricing   — full deterministic estimate JSON (immediate)
      event: token     — individual LLM narrative text chunks
      event: done      — signals end of stream
    """
    history = [
        {"role": m.role, "content": m.content}
        for m in (body.history or [])
    ]

    try:
        result = await process_chat_message(
            message=body.message,
            county=body.county or None,
            preferred_supplier=body.preferred_supplier,
            job_type=body.job_type,
            history=history or None,
            db=db,
            skip_llm_response=True,   # streaming endpoint generates LLM tokens below
        )
    except Exception as e:
        logger.error("Chat stream pricing error", error=str(e), user_id=current_user.id, exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")

    estimate_result = result.pop("_estimate_result", None)

    estimate_id = None
    if estimate_result is not None:
        try:
            estimate = await persist_estimate(
                db=db,
                result=estimate_result,
                title=body.message[:100] or "Chat Estimate",
                county=body.county or "Dallas",
                preferred_supplier=body.preferred_supplier,
                chat_context=body.message,
                source="chat_stream",
                created_by=current_user.id,
                organization_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            )
            estimate_id = estimate.id
        except Exception as e:
            logger.warning("Stream estimate persist failed", error=str(e))

    # Persist the exchange to a session (best-effort; non-fatal if it fails)
    stream_session_id: int | None = None
    try:
        stream_session_id = await _upsert_session(
            db=db,
            session_id=body.session_id,
            user_id=current_user.id,
            organization_id=getattr(current_user, "organization_id", None),
            user_message=body.message,
            assistant_answer="",  # placeholder; streaming answer assembled client-side
            county=body.county,
            estimate_id=estimate_id,
        )
        await db.commit()
    except Exception as e:
        logger.warning("Stream session persist failed", error=str(e))

    pricing_event = {
        "estimate": build_estimate_breakdown(estimate_result) if estimate_result else None,
        "estimate_id": estimate_id,
        "session_id": stream_session_id,
        "confidence": result["confidence"],
        "confidence_label": result["confidence_label"],
        "assumptions": result.get("assumptions", []),
        "sources": result.get("sources", []),
        "conversation_id": body.conversation_id,
        "job_type_detected": result.get("job_type_detected"),
        "template_used": result.get("template_used"),
        "classified_by": result.get("classification", {}).get("classified_by"),
    }

    # Use template_name already resolved by process_chat_message (avoids redundant lookup)
    template_name = result.get("_template_name") or result.get("template_used") or ""
    rag_context = result.get("_rag_context") or ""
    quantity = result.get("classification", {}).get("quantity", 1) if result.get("classification") else 1
    est = pricing_event["estimate"]

    async def event_stream():
        # 1. Send pricing data immediately
        yield f"event: pricing\ndata: {json.dumps(pricing_event)}\n\n"

        # 2. Stream LLM narrative tokens with timeout protection
        try:
            async with asyncio.timeout(STREAM_TIMEOUT_SECONDS):
                if est:
                    async for token in llm_service.generate_response_stream(
                        message=body.message,
                        grand_total=est["grand_total"] if isinstance(est, dict) else est.grand_total,
                        labor_total=est["labor_total"] if isinstance(est, dict) else est.labor_total,
                        materials_total=est["materials_total"] if isinstance(est, dict) else est.materials_total,
                        tax_total=est["tax_total"] if isinstance(est, dict) else est.tax_total,
                        template_name=template_name,
                        county=body.county or "Dallas",
                        quantity=quantity,
                        history=history or None,
                        context=rag_context
                    ):
                        yield f"event: token\ndata: {json.dumps(token)}\n\n"
                else:
                    yield f"event: token\ndata: {json.dumps(result.get('answer', ''))}\n\n"
        except asyncio.TimeoutError:
            logger.warning("LLM stream timeout", timeout=STREAM_TIMEOUT_SECONDS)
            if est:
                gt = est["grand_total"] if isinstance(est, dict) else est.grand_total
                lt = est["labor_total"] if isinstance(est, dict) else est.labor_total
                mt = est["materials_total"] if isinstance(est, dict) else est.materials_total
                fallback = llm_service.make_static_narrative(
                    template_name, gt, lt, mt, body.county or "Dallas", quantity
                )
                yield f"event: token\ndata: {json.dumps(fallback)}\n\n"
            else:
                yield f'event: error\ndata: {json.dumps({"error": "Response generation timed out."})}\n\n'
        except Exception as e:
            logger.error("LLM stream error", error=str(e))
            yield f'event: error\ndata: {json.dumps({"error": "An error occurred generating the narrative response."})}\n\n'

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
