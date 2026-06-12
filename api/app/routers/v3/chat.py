"""
Chat API v3 — Agentic pricing with structured outputs, tool calling, and streaming.
"""

import asyncio
import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.core.limiter import limiter
from app.database import get_db
from app.models.blueprints import BlueprintDetection, BlueprintPage
from app.models.estimates import Estimate
from app.models.projects import Project
from app.models.sessions import ChatSession, ChatMessage as ChatMessageModel
from app.models.users import User
from app.schemas.v3.chat import ChatPriceRequestV3, ChatPriceResponseV3, EstimateBreakdownV3, ToolCallInfo, MarketAdjustmentInfo
from app.services.agent_v3 import agent_v3, AgentV3Result
from app.services.estimate_service import persist_estimate
from app.services.llm_service import llm_service

logger = structlog.get_logger()
router = APIRouter()

# ── SSE Event Buffer (Last-Event-ID reconnect support) ──────────────────────
_SSE_BUFFER_TTL = 60.0
_SSE_BUFFER_MAX_SIZE = 50
_sse_buffers: dict[str, list[dict]] = {}


def _cleanup_sse_buffers() -> None:
    """Remove expired SSE event buffers."""
    now = time.monotonic()
    expired = [
        cid for cid, buf in _sse_buffers.items()
        if not buf or now - buf[-1]["ts"] > _SSE_BUFFER_TTL
    ]
    for cid in expired:
        del _sse_buffers[cid]


def _buffer_event(connection_id: str, event_id: str, data: str) -> None:
    """Add an event to the per-connection buffer."""
    buf = _sse_buffers.get(connection_id, [])
    buf.append({"id": event_id, "data": data, "ts": time.monotonic()})
    if len(buf) > _SSE_BUFFER_MAX_SIZE:
        buf = buf[-_SSE_BUFFER_MAX_SIZE:]
    _sse_buffers[connection_id] = buf


def _get_events_after_id(connection_id: str, last_event_id: str) -> list[str]:
    """Return buffered events after the given event ID for reconnect."""
    buf = _sse_buffers.get(connection_id, [])
    # Filter expired
    now = time.monotonic()
    buf = [e for e in buf if now - e["ts"] < _SSE_BUFFER_TTL]
    # Find index of last_event_id
    for i, e in enumerate(buf):
        if e["id"] == last_event_id:
            return [e["data"] for e in buf[i + 1 :]]
    return [e["data"] for e in buf]


# ── DB Write Retry Helper ───────────────────────────────────────────────────
async def _db_write_with_retry(db: AsyncSession, write_fn, max_retries: int = 3):
    """Execute a DB write with exponential backoff retry."""
    for attempt in range(1, max_retries + 1):
        try:
            return await write_fn()
        except Exception as exc:
            if attempt >= max_retries:
                raise
            delay = 0.5 * (2 ** (attempt - 1))
            logger.warning("chat.db_write_retry", attempt=attempt, delay=delay, error=str(exc))
            await asyncio.sleep(delay)
            try:
                await db.rollback()
            except Exception:
                pass


async def _extract_memories_background(user_id: int, session_id: int) -> None:
    """Best-effort background extraction of durable memories from a chat session."""
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            count = await memory_service.extract_from_session(db, user_id=user_id, session_id=session_id)
            if count:
                logger.info("chat.memory_extracted", session_id=session_id, count=count)
    except Exception as exc:
        logger.warning("chat.memory_extract_failed", session_id=session_id, error=str(exc))


# Fixture types detected by vision pipeline → task code prefixes that should
# be auto-seeded with the detected count.
_FIXTURE_TO_TASK_PATTERNS: dict[str, list[str]] = {
    "toilet": ["TOILET"],
    "water_closet": ["TOILET"],
    "wc": ["TOILET"],
    "lavatory": ["LAV_"],
    "lav": ["LAV_"],
    "bathroom_sink": ["LAV_", "SINK_REPLACE_BATH"],
    "sink": ["KITCHEN_FAUCET", "SINK_REPLACE_KITCHEN", "KITCHEN_SINK"],
    "kitchen_sink": ["KITCHEN_FAUCET", "SINK_REPLACE_KITCHEN", "KITCHEN_SINK"],
    "shower": ["SHOWER_"],
    "tub": ["TUB_"],
    "bathtub": ["TUB_"],
    "tub_shower": ["TUB_SHOWER", "TUB_", "SHOWER_"],
    "water_heater": ["WH_", "WATER_HEATER"],
    "wh": ["WH_", "WATER_HEATER"],
    "disposal": ["GARBAGE_DISPOSAL"],
    "garbage_disposal": ["GARBAGE_DISPOSAL"],
    "dishwasher": ["DISHWASHER"],
    "hose_bib": ["HOSE_BIB"],
    "prv": ["PRV_"],
}


async def _load_blueprint_fixtures(db: AsyncSession, blueprint_job_id: int) -> dict[str, int]:
    """Aggregate fixture counts from a completed blueprint job."""
    result = await db.execute(
        select(BlueprintDetection.fixture_type, func.sum(BlueprintDetection.count))
        .join(BlueprintPage)
        .where(
            BlueprintPage.job_id == blueprint_job_id,
            BlueprintDetection.needs_review.is_(False),
        )
        .group_by(BlueprintDetection.fixture_type)
    )
    fixtures: dict[str, int] = {}
    for fixture_type, count in result.all():
        if fixture_type and count:
            fixtures[fixture_type.lower().strip()] = int(count)
    return fixtures


def _match_task_to_fixture(task_code: str, fixtures: dict[str, int]) -> tuple[int, str] | None:
    """Return (count, fixture_type) if the task code maps to a detected fixture."""
    if not task_code or not fixtures:
        return None
    tc = task_code.upper()
    for fixture_type, patterns in _FIXTURE_TO_TASK_PATTERNS.items():
        if fixture_type not in fixtures:
            continue
        for pat in patterns:
            if pat in tc:
                return (fixtures[fixture_type], fixture_type)
    return None


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

STREAM_TIMEOUT_SECONDS = 30


async def _upsert_session(
    db: AsyncSession,
    session_id: int | None,
    user_id: int,
    user_message: str,
    assistant_answer: str,
    county: str | None,
    estimate_id: int | None,
    preferred_supplier: str | None = None,
    job_type: str | None = None,
    access_type: str | None = None,
    blueprint_fixtures: dict[str, int] | None = None,
) -> tuple[int, int | None]:
    """Get-or-create a ChatSession and append the exchange as two ChatMessage rows.

    Returns (session_id, assistant_message_id).
    """
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
            title=user_message[:80],
            county=county,
            preferred_supplier=preferred_supplier,
            job_type=job_type,
            access_type=access_type,
            blueprint_fixtures=blueprint_fixtures,
        )
        db.add(session)
        await db.flush()
    else:
        # Enrich session context from latest classification
        if county and not session.county:
            session.county = county
        if preferred_supplier and not session.preferred_supplier:
            session.preferred_supplier = preferred_supplier
        if job_type and not session.job_type:
            session.job_type = job_type
        if access_type and not session.access_type:
            session.access_type = access_type
        if blueprint_fixtures and not session.blueprint_fixtures:
            session.blueprint_fixtures = blueprint_fixtures

    user_msg = ChatMessageModel(session_id=session.id, role="user", content=user_message)
    assistant_msg = ChatMessageModel(session_id=session.id, role="assistant", content=assistant_answer, estimate_id=estimate_id)
    db.add(user_msg)
    db.add(assistant_msg)
    await db.flush()
    return session.id, assistant_msg.id


def _build_response(result: AgentV3Result, estimate_id: int | None = None, session_id: int | None = None) -> ChatPriceResponseV3:
    """Convert AgentV3Result to ChatPriceResponseV3."""
    est = result.estimate
    return ChatPriceResponseV3(
        answer=result.narrative or "",
        estimate=EstimateBreakdownV3(
            labor_total=est.labor_total,
            materials_total=est.materials_total,
            tax_total=est.tax_total,
            markup_total=est.markup_total,
            misc_total=est.misc_total,
            subtotal=est.subtotal,
            grand_total=est.grand_total,
            line_items=[
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                    "supplier": li.supplier,
                    "sku": li.sku,
                    "canonical_item": li.canonical_item,
                    "trace_json": li.trace_json,
                }
                for li in est.line_items
            ],
            market_adjustment_applied=result.overall_market_factor,
            confidence_components=est.confidence_components,
        ) if est.line_items else None,
        estimate_id=estimate_id,
        session_id=session_id,
        confidence=est.confidence_score,
        confidence_label=est.confidence_label,
        assumptions=est.assumptions,
        sources=est.sources,
        job_type_detected=est.job_type,
        template_used=est.template_code,
        classified_by=result.classified_by,
        clarification_questions=result.clarification_questions,
        tool_calls=[
            ToolCallInfo(
                tool_name=tc.tool_name,
                latency_ms=tc.latency_ms,
                error=tc.error,
            )
            for tc in result.tool_calls
        ],
        market_adjustments=[
            MarketAdjustmentInfo(
                name=ma["name"],
                category=ma["category"],
                factor=ma["factor"],
            )
            for ma in result.market_adjustments_applied
        ],
        agent_trace=result.agent_trace,
        estimate_diff=result.estimate_diff,
        blueprint_seeded=result.blueprint_seeded,
        suggested_context=[
            {
                "field": sc.field,
                "value": sc.value,
                "reason": sc.reason,
                "confidence": sc.confidence,
            }
            for sc in (result.suggested_context or [])
        ],
        intake_result=result.intake_result.to_dict() if result.intake_result else None,
        revision_suggestions=[s.to_dict() for s in (result.revision_suggestions or [])],
    )


def _build_stream_pricing_data(result: AgentV3Result, estimate_id: int | None = None, session_id: int | None = None) -> dict:
    """Build the pricing event payload for SSE streaming."""
    est = result.estimate
    payload: dict = {
        "estimate": {
            "labor_total": est.labor_total,
            "materials_total": est.materials_total,
            "tax_total": est.tax_total,
            "markup_total": est.markup_total,
            "misc_total": est.misc_total,
            "subtotal": est.subtotal,
            "grand_total": est.grand_total,
            "line_items": [
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                    "supplier": li.supplier,
                }
                for li in est.line_items
            ],
        },
        "estimate_id": estimate_id,
        "session_id": session_id,
        "confidence": est.confidence_score,
        "confidence_label": est.confidence_label,
        "assumptions": est.assumptions,
        "market_adjustment_applied": result.overall_market_factor,
    }
    if est.template_code:
        payload["template_used"] = est.template_code
    if est.job_type:
        payload["job_type_detected"] = est.job_type
    if result.classified_by:
        payload["classified_by"] = result.classified_by
    if result.estimate_diff:
        payload["estimate_diff"] = result.estimate_diff
    if result.suggested_context:
        payload["suggested_context"] = [
            {"field": sc.field, "value": sc.value, "reason": sc.reason, "confidence": sc.confidence}
            for sc in result.suggested_context
        ]
    if result.blueprint_seeded:
        payload["blueprint_seeded"] = True
    if result.intake_result:
        payload["intake_result"] = result.intake_result.to_dict()
    if result.revision_suggestions:
        payload["revision_suggestions"] = [s.to_dict() for s in result.revision_suggestions]
    return payload


async def _resolve_blueprint_fixtures(
    db: AsyncSession,
    session_id: int | None,
    blueprint_job_id: int | None,
) -> dict[str, int]:
    """Load fixture counts from a blueprint job or from a previous session."""
    if blueprint_job_id:
        return await _load_blueprint_fixtures(db, blueprint_job_id)
    if session_id:
        result = await db.execute(
            select(ChatSession.blueprint_fixtures).where(ChatSession.id == session_id)
        )
        fixtures = result.scalar_one_or_none()
        if fixtures and isinstance(fixtures, dict):
            return fixtures
    return {}


@router.post("/price", response_model=ChatPriceResponseV3)
@limiter.limit("30/minute")
async def chat_price_v3(
    request: Request,
    req: ChatPriceRequestV3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a priced estimate from a chat message using the v3 agentic pipeline."""
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    blueprint_fixtures = await _resolve_blueprint_fixtures(db, req.session_id, req.blueprint_job_id)
    blueprint_context = {"fixtures": blueprint_fixtures} if blueprint_fixtures else None

    result = await agent_v3.process_message(
        message=req.message,
        county=req.county,
        preferred_supplier=req.preferred_supplier,
        history=history,
        db=db,
        user_id=current_user.id,
        blueprint_context=blueprint_context,
        previous_estimate=req.previous_estimate.model_dump() if req.previous_estimate else None,
        confirmed_intake=req.confirmed_intake.model_dump() if req.confirmed_intake else None,
    )

    # Resolve customer → project (lead capture)
    org_id = getattr(current_user, "organization_id", None)
    resolved_project_id = await _resolve_customer_project(
        db=db,
        customer=req.customer,
        project_id=req.project_id,
        organization_id=org_id,
        created_by=current_user.id,
    )

    # Persist estimate if one was generated
    estimate_id = None
    if result.estimate.template_code and result.clarification_questions is None:
        async def _persist_estimate():
            nonlocal estimate_id
            est = await persist_estimate(
                db=db,
                result=result.estimate,
                county=result.estimate.county or req.county,
                title=f"Chat: {req.message[:60]}",
                created_by=current_user.id,
                organization_id=org_id,
                project_id=resolved_project_id,
            )
            estimate_id = est.id
            if estimate_id:
                await db.execute(
                    update(Estimate)
                    .where(Estimate.id == estimate_id)
                    .values(
                        agent_trace=result.agent_trace,
                        market_adjustment_applied=result.overall_market_factor,
                        confidence_components=result.estimate.confidence_components,
                    )
                )
            await db.commit()

        try:
            await _db_write_with_retry(db, _persist_estimate)
        except Exception as exc:
            logger.warning("chat_v3.persist_failed", error=str(exc))

    # Persist session
    session_id = None
    async def _persist_session():
        nonlocal session_id
        sid, _ = await _upsert_session(
            db=db,
            session_id=req.session_id,
            user_id=current_user.id,
            user_message=req.message,
            assistant_answer=result.narrative or "",
            county=req.county or result.classification.county,
            estimate_id=estimate_id,
            preferred_supplier=result.classification.preferred_supplier,
            job_type=result.estimate.job_type if result.estimate else None,
            access_type=result.classification.access_type,
            blueprint_fixtures=blueprint_fixtures if blueprint_fixtures else None,
        )
        session_id = sid
        await db.commit()

    try:
        await _db_write_with_retry(db, _persist_session)
        # Fire-and-forget memory extraction
        if session_id:
            asyncio.create_task(
                _extract_memories_background(current_user.id, session_id)
            )
    except Exception as exc:
        logger.warning("chat_v3.session_persist_failed", error=str(exc))

    return _build_response(result, estimate_id, session_id)


@router.post("/price/stream")
@limiter.limit("20/minute")
async def chat_price_stream_v3(
    request: Request,
    req: ChatPriceRequestV3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE streaming variant of the v3 chat pricing endpoint.

    Emits events:
      - reasoning: agent chain-of-thought
      - tool_call: tool execution
      - pricing: full estimate result
      - token: narrative text chunks (true token-by-token streaming)
      - clarification: follow-up questions needed
      - done: stream terminator
    """
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    blueprint_fixtures = await _resolve_blueprint_fixtures(db, req.session_id, req.blueprint_job_id)
    blueprint_context = {"fixtures": blueprint_fixtures} if blueprint_fixtures else None

    async def event_stream():
        connection_id = str(uuid.uuid4())
        event_seq = 0

        def _next_event_id() -> str:
            nonlocal event_seq
            event_id = f"{connection_id}-{event_seq}"
            event_seq += 1
            return event_id

        def _format_event(event_type: str, data: dict) -> str:
            event_id = _next_event_id()
            return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(data)}\n\n"

        # Handle Last-Event-ID reconnect
        last_event_id = request.headers.get("Last-Event-ID")
        if last_event_id:
            parts = last_event_id.rsplit("-", 1)
            if len(parts) == 2:
                reconnect_cid = parts[0]
                replay_events = _get_events_after_id(reconnect_cid, last_event_id)
                for ev_data in replay_events:
                    yield ev_data
                # If the done event was already buffered, stop here
                if any("event: done" in ev for ev in replay_events):
                    return

        result = await agent_v3.process_message(
            message=req.message,
            county=req.county,
            preferred_supplier=req.preferred_supplier,
            history=history,
            db=db,
            user_id=current_user.id,
            skip_llm_response=True,
            blueprint_context=blueprint_context,
            previous_estimate=req.previous_estimate.model_dump() if req.previous_estimate else None,
            confirmed_intake=req.confirmed_intake.model_dump() if req.confirmed_intake else None,
        )

        # Emit intake result for confirmation
        if result.intake_result:
            ev = _format_event("intake", {"result": result.intake_result.to_dict()})
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            yield ev

        # Emit reasoning
        if result.classification.reasoning:
            ev = _format_event("reasoning", {"content": result.classification.reasoning})
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            yield ev

        # Emit tool calls
        for tc in result.tool_calls:
            ev = _format_event("tool_call", {"tool": tc.tool_name, "latency_ms": tc.latency_ms})
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            yield ev

        # Emit clarification if needed
        if result.clarification_questions:
            ev = _format_event("clarification", {"questions": result.clarification_questions})
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            # Persist clarification session
            try:
                await _db_write_with_retry(
                    db,
                    lambda: _upsert_session(
                        db=db,
                        session_id=req.session_id,
                        user_id=current_user.id,
                        user_message=req.message,
                        assistant_answer="",
                        county=req.county or result.classification.county,
                        estimate_id=None,
                        preferred_supplier=result.classification.preferred_supplier,
                        job_type=None,
                        access_type=result.classification.access_type,
                        blueprint_fixtures=blueprint_fixtures if blueprint_fixtures else None,
                    ),
                )
                await _db_write_with_retry(db, lambda: db.commit())
            except Exception as exc:
                logger.warning("chat_v3_stream.session_persist_failed", error=str(exc))
            ev_done = _format_event("done", {})
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev_done)
            yield ev_done
            return

        # Resolve customer → project (lead capture)
        org_id = getattr(current_user, "organization_id", None)
        resolved_project_id = await _resolve_customer_project(
            db=db,
            customer=req.customer,
            project_id=req.project_id,
            organization_id=org_id,
            created_by=current_user.id,
        )

        # Persist estimate and session with retry
        estimate_id = None
        session_id = None
        assistant_message_id = None

        if result.estimate.template_code:
            async def _do_persist():
                nonlocal estimate_id, session_id, assistant_message_id
                est = await persist_estimate(
                    db=db,
                    result=result.estimate,
                    county=result.estimate.county or req.county,
                    title=f"Chat: {req.message[:60]}",
                    created_by=current_user.id,
                    organization_id=org_id,
                    project_id=resolved_project_id,
                )
                estimate_id = est.id
                if estimate_id:
                    await db.execute(
                        update(Estimate)
                        .where(Estimate.id == estimate_id)
                        .values(
                            agent_trace=result.agent_trace,
                            market_adjustment_applied=result.overall_market_factor,
                            confidence_components=result.estimate.confidence_components,
                        )
                    )
                sid, amid = await _upsert_session(
                    db=db,
                    session_id=req.session_id,
                    user_id=current_user.id,
                    user_message=req.message,
                    assistant_answer="",
                    county=req.county or result.classification.county,
                    estimate_id=estimate_id,
                    preferred_supplier=result.classification.preferred_supplier,
                    job_type=result.estimate.job_type if result.estimate else None,
                    access_type=result.classification.access_type,
                    blueprint_fixtures=blueprint_fixtures if blueprint_fixtures else None,
                )
                session_id = sid
                assistant_message_id = amid
                await db.commit()

            try:
                await _db_write_with_retry(db, _do_persist)
                if session_id:
                    asyncio.create_task(
                        _extract_memories_background(current_user.id, session_id)
                    )
            except Exception as exc:
                logger.error("chat_v3_stream.persist_failed", error=str(exc))
                ev_err = _format_event("error", {"error": "Failed to save estimate. Please try again."})
                _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev_err)
                yield ev_err
                ev_done = _format_event("done", {})
                _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev_done)
                yield ev_done
                return

        # Emit pricing
        if result.estimate.template_code:
            pricing_data = _build_stream_pricing_data(result, estimate_id, session_id)
            ev = _format_event("pricing", pricing_data)
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            yield ev

        # Emit proactive revision suggestions
        if result.revision_suggestions:
            ev = _format_event("suggestions", {
                "suggestions": [s.to_dict() for s in result.revision_suggestions]
            })
            _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
            yield ev

        # Stream LLM narrative tokens with timeout protection
        collected_tokens: list[str] = []
        if result.estimate.template_code:
            try:
                async with asyncio.timeout(STREAM_TIMEOUT_SECONDS):
                    async for token_data in llm_service.generate_response_stream(
                        message=req.message,
                        grand_total=result.estimate.grand_total,
                        labor_total=result.estimate.labor_total,
                        materials_total=result.estimate.materials_total,
                        tax_total=result.estimate.tax_total,
                        template_name=result.estimate.template_code or result.classification.task_code or "",
                        county=result.classification.county,
                        quantity=result.classification.quantity,
                        history=history,
                    ):
                        token_text = token_data.get("text", "") or token_data.get("content", "")
                        if token_text:
                            collected_tokens.append(token_text)
                        ev = _format_event("token", token_data)
                        _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
                        yield ev
            except asyncio.TimeoutError:
                logger.warning("chat_v3_stream.narrative_timeout", timeout=STREAM_TIMEOUT_SECONDS)
                if result.estimate.template_code:
                    fallback = llm_service.make_static_narrative(
                        result.estimate.template_code or "",
                        result.estimate.grand_total,
                        result.estimate.labor_total,
                        result.estimate.materials_total,
                        result.classification.county,
                        result.classification.quantity,
                    )
                    fb_text = fallback.get("text", "") or fallback.get("content", "")
                    if fb_text:
                        collected_tokens.append(fb_text)
                    ev = _format_event("token", fallback)
                    _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
                    yield ev
            except Exception as exc:
                logger.warning("chat_v3_stream.narrative_failed", error=str(exc))
                ev = _format_event("error", {"error": "Narrative generation failed."})
                _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev)
                yield ev

        # Update assistant message with full narrative
        full_narrative = "".join(collected_tokens)
        if assistant_message_id and full_narrative:
            try:
                await _db_write_with_retry(
                    db,
                    lambda: db.execute(
                        update(ChatMessageModel)
                        .where(ChatMessageModel.id == assistant_message_id)
                        .values(content=full_narrative)
                    ),
                )
                await _db_write_with_retry(db, lambda: db.commit())
            except Exception as exc:
                logger.warning("chat_v3_stream.narrative_persist_failed", error=str(exc))

        ev_done = _format_event("done", {})
        _buffer_event(connection_id, f"{connection_id}-{event_seq - 1}", ev_done)
        yield ev_done

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Compare Endpoints ─────────────────────────────────────────────────────────

from app.schemas.v3.chat import ChatCompareRequestV3, ChatCompareResponseV3


@router.post("/compare", response_model=ChatCompareResponseV3)
@limiter.limit("20/minute")
async def chat_compare_v3(
    request: Request,
    req: ChatCompareRequestV3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate multiple estimate variants (budget/standard/premium) for comparison."""
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    blueprint_fixtures = await _resolve_blueprint_fixtures(db, req.session_id, req.blueprint_job_id)
    blueprint_context = {"fixtures": blueprint_fixtures} if blueprint_fixtures else None

    variants = await agent_v3.generate_variants(
        message=req.message,
        county=req.county,
        preferred_supplier=req.preferred_supplier,
        history=history,
        db=db,
        user_id=current_user.id,
        blueprint_context=blueprint_context,
        previous_estimate=req.previous_estimate.model_dump() if req.previous_estimate else None,
        tiers=req.variant_tiers,
        confirmed_intake=req.confirmed_intake,
    )

    org_id = getattr(current_user, "organization_id", None)
    resolved_project_id = await _resolve_customer_project(
        db=db,
        customer=req.customer,
        project_id=req.project_id,
        organization_id=org_id,
        created_by=current_user.id,
    )

    variant_group_id = str(uuid.uuid4())
    variant_responses: list[ChatPriceResponseV3] = []
    estimate_ids: list[int] = []
    session_id = None

    for variant in variants:
        if variant.clarification_questions:
            # If clarification needed, return just the standard with questions
            return ChatCompareResponseV3(
                variant_group_id="",
                classification=variant.classification.model_dump(),
                variants=[_build_response(variant, None, None)],
                assumptions=variant.estimate.assumptions if variant.estimate else [],
            )

        est_id = None
        tier_label = "standard"
        if variant.estimate.template_code:
            tier_label = variant.classified_by.split("_variant_")[-1] if "_variant_" in variant.classified_by else "standard"

            async def _persist_variant_estimate():
                nonlocal est_id
                estimate = await persist_estimate(
                    db=db,
                    result=variant.estimate,
                    county=variant.estimate.county or req.county,
                    title=f"{tier_label.capitalize()}: {req.message[:50]}",
                    created_by=current_user.id,
                    organization_id=org_id,
                    project_id=resolved_project_id,
                    variant_group_id=variant_group_id,
                    variant_label=tier_label.capitalize(),
                )
                est_id = estimate.id
                if est_id:
                    await db.execute(
                        update(Estimate)
                        .where(Estimate.id == est_id)
                        .values(
                            agent_trace=variant.agent_trace,
                            market_adjustment_applied=variant.overall_market_factor,
                            confidence_components=variant.estimate.confidence_components,
                        )
                    )
                await db.commit()

            try:
                await _db_write_with_retry(db, _persist_variant_estimate)
                if est_id:
                    estimate_ids.append(est_id)
            except Exception as exc:
                logger.warning("chat_v3_compare.persist_failed", error=str(exc))

        resp = _build_response(variant, est_id, None)
        resp.variant_label = tier_label.capitalize() if "_variant_" in variant.classified_by else "Standard"
        variant_responses.append(resp)

    # Persist session once for the whole comparison
    async def _persist_compare_session():
        nonlocal session_id
        sid, _ = await _upsert_session(
            db=db,
            session_id=req.session_id,
            user_id=current_user.id,
            user_message=req.message,
            assistant_answer=f"Generated {len(variants)} estimate variants for comparison.",
            county=req.county or variants[0].classification.county,
            estimate_id=estimate_ids[0] if estimate_ids else None,
            preferred_supplier=variants[0].classification.preferred_supplier,
            job_type=variants[0].estimate.job_type if variants[0].estimate else None,
            access_type=variants[0].classification.access_type,
            blueprint_fixtures=blueprint_fixtures if blueprint_fixtures else None,
        )
        session_id = sid
        await db.commit()

    try:
        await _db_write_with_retry(db, _persist_compare_session)
        if session_id:
            asyncio.create_task(
                _extract_memories_background(current_user.id, session_id)
            )
    except Exception as exc:
        logger.warning("chat_v3_compare.session_persist_failed", error=str(exc))

    return ChatCompareResponseV3(
        variant_group_id=variant_group_id,
        classification=variants[0].classification.model_dump(),
        variants=variant_responses,
        assumptions=variants[0].estimate.assumptions if variants[0].estimate else [],
        session_id=session_id,
    )


# ── Session Management ────────────────────────────────────────────────────────

from app.services.memory_service import memory_service
from pydantic import BaseModel


class ChatSessionListItem(BaseModel):
    id: int
    title: str | None
    county: str | None
    preferred_supplier: str | None
    job_type: str | None
    access_type: str | None
    created_at: str | None
    updated_at: str | None
    message_count: int


class ChatMessageItem(BaseModel):
    id: int
    role: str
    content: str
    estimate_id: int | None
    created_at: str | None


class ChatSessionDetail(BaseModel):
    id: int
    title: str | None
    county: str | None
    preferred_supplier: str | None
    job_type: str | None
    access_type: str | None
    created_at: str | None
    updated_at: str | None
    messages: list[ChatMessageItem]


@router.get("/sessions", response_model=list[ChatSessionListItem])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """List the current user's chat sessions, newest first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = result.scalars().all()

    # Count messages per session
    session_ids = [s.id for s in sessions]
    counts = {}
    if session_ids:
        count_result = await db.execute(
            select(ChatMessageModel.session_id, func.count(ChatMessageModel.id))
            .where(ChatMessageModel.session_id.in_(session_ids))
            .group_by(ChatMessageModel.session_id)
        )
        counts = {sid: c for sid, c in count_result.fetchall()}

    return [
        ChatSessionListItem(
            id=s.id,
            title=s.title,
            county=s.county,
            preferred_supplier=s.preferred_supplier,
            job_type=s.job_type,
            access_type=s.access_type,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
            message_count=counts.get(s.id, 0),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single chat session with its full message history."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.created_at.asc())
    )
    messages = [
        ChatMessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            estimate_id=m.estimate_id,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in msgs.scalars().all()
    ]

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        county=session.county,
        preferred_supplier=session.preferred_supplier,
        job_type=session.job_type,
        access_type=session.access_type,
        created_at=session.created_at.isoformat() if session.created_at else None,
        updated_at=session.updated_at.isoformat() if session.updated_at else None,
        messages=messages,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    from fastapi import HTTPException
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
    return None


# ─── Session Sharing ─────────────────────────────────────────────────────────

import secrets
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.models.sessions import ChatSessionShare


class ShareCreateRequest(BaseModel):
    permission: str = "read"  # read | comment
    expires_in_days: int | None = 7  # None = never expires


class ShareCreateResponse(BaseModel):
    token: str
    url: str
    expires_at: str | None
    permission: str


@router.post("/sessions/{session_id}/share", response_model=ShareCreateResponse)
async def create_session_share(
    session_id: int,
    body: ShareCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a shareable link for a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    token = secrets.token_urlsafe(32)
    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    share = ChatSessionShare(
        session_id=session_id,
        token=token,
        permission=body.permission,
        expires_at=expires_at,
        created_by=current_user.id,
    )
    db.add(share)
    await db.commit()

    return ShareCreateResponse(
        token=token,
        url=f"/share/{token}",
        expires_at=expires_at.isoformat() if expires_at else None,
        permission=body.permission,
    )


@router.delete("/sessions/{session_id}/share/{token}", status_code=204)
async def revoke_session_share(
    session_id: int,
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a share link."""
    result = await db.execute(
        select(ChatSessionShare).where(
            ChatSessionShare.token == token,
            ChatSessionShare.session_id == session_id,
            ChatSessionShare.created_by == current_user.id,
        )
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    await db.delete(share)
    await db.commit()
    return None


class SharedSessionResponse(BaseModel):
    session: ChatSessionDetail
    permission: str


@router.get("/share/{token}", response_model=SharedSessionResponse)
async def get_shared_session(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Guest view: get a shared session by token."""
    result = await db.execute(
        select(ChatSessionShare).where(
            ChatSessionShare.token == token,
        )
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")

    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link has expired")

    # Load session
    session_result = await db.execute(
        select(ChatSession).where(ChatSession.id == share.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = await db.execute(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == share.session_id)
        .order_by(ChatMessageModel.created_at.asc())
    )
    messages = [
        ChatMessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            estimate_id=m.estimate_id,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in msgs.scalars().all()
    ]

    return SharedSessionResponse(
        session=ChatSessionDetail(
            id=session.id,
            title=session.title,
            county=session.county,
            preferred_supplier=session.preferred_supplier,
            job_type=session.job_type,
            access_type=session.access_type,
            created_at=session.created_at.isoformat() if session.created_at else None,
            updated_at=session.updated_at.isoformat() if session.updated_at else None,
            messages=messages,
        ),
        permission=share.permission,
    )


# ─── Prompt Templates ────────────────────────────────────────────────────────

from app.models.sessions import PromptTemplate


class PromptTemplateCreate(BaseModel):
    name: str
    template: str
    is_personal: bool = False


class PromptTemplateResponse(BaseModel):
    id: int
    name: str
    template: str
    is_personal: bool
    is_active: bool
    created_at: str | None


@router.get("/templates", response_model=list[PromptTemplateResponse])
async def list_prompt_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List prompt templates for the user's organization."""
    org_id = getattr(current_user, "organization_id", None)
    if not org_id:
        return []

    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.organization_id == org_id,
            PromptTemplate.is_active.is_(True),
        ).order_by(PromptTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return [
        PromptTemplateResponse(
            id=t.id,
            name=t.name,
            template=t.template,
            is_personal=t.is_personal,
            is_active=t.is_active,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in templates
    ]


@router.post("/templates", response_model=PromptTemplateResponse)
async def create_prompt_template(
    body: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new prompt template."""
    org_id = getattr(current_user, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=403, detail="User must belong to an organization")

    template = PromptTemplate(
        organization_id=org_id,
        created_by=current_user.id,
        name=body.name,
        template=body.template,
        is_personal=body.is_personal,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return PromptTemplateResponse(
        id=template.id,
        name=template.name,
        template=template.template,
        is_personal=template.is_personal,
        is_active=template.is_active,
        created_at=template.created_at.isoformat() if template.created_at else None,
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_prompt_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a prompt template."""
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.id == template_id,
            PromptTemplate.created_by == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.is_active = False
    await db.commit()
    return None
