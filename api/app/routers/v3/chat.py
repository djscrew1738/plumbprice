"""
Chat API v3 — Agentic pricing with structured outputs, tool calling, and streaming.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.services.agent_v3 import agent_v3, AgentV3Result
from app.services.estimate_service import persist_estimate
from app.schemas.v3.chat import ChatPriceRequestV3, ChatPriceResponseV3, EstimateBreakdownV3, ToolCallInfo, MarketAdjustmentInfo

logger = structlog.get_logger()
router = APIRouter()


def _build_response(result: AgentV3Result, estimate_id: int | None = None) -> ChatPriceResponseV3:
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
            confidence_components=est.confidence_components if hasattr(est, "confidence_components") else {},
        ) if est.line_items else None,
        estimate_id=estimate_id,
        confidence=est.confidence_score,
        confidence_label=est.confidence_label,
        assumptions=est.assumptions,
        sources=est.sources if hasattr(est, "sources") else [],
        job_type_detected=est.job_type if hasattr(est, "job_type") else None,
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
    )


@router.post("/price", response_model=ChatPriceResponseV3)
async def chat_price_v3(
    req: ChatPriceRequestV3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a priced estimate from a chat message using the v3 agentic pipeline."""
    result = await agent_v3.process_message(
        message=req.message,
        county=req.county,
        preferred_supplier=req.preferred_supplier,
        history=[{"role": m.role, "content": m.content} for m in (req.history or [])],
        db=db,
        user_id=current_user.id,
    )

    # Persist estimate if one was generated
    estimate_id = None
    if result.estimate.template_code and result.clarification_questions is None:
        try:
            estimate_id = await persist_estimate(
                db=db,
                estimate_result=result.estimate,
                user_id=current_user.id,
                title=f"Chat: {req.message[:60]}",
                project_id=req.project_id,
            )
            # Store agent trace
            if estimate_id:
                from sqlalchemy import update
                from app.models.estimates import Estimate
                await db.execute(
                    update(Estimate)
                    .where(Estimate.id == estimate_id)
                    .values(
                        agent_trace=result.agent_trace,
                        market_adjustment_applied=result.overall_market_factor,
                        confidence_components=result.estimate.confidence_components if hasattr(result.estimate, "confidence_components") else {},
                    )
                )
                await db.commit()
        except Exception as exc:
            logger.warning("chat_v3.persist_failed", error=str(exc))

    return _build_response(result, estimate_id)


@router.post("/price/stream")
async def chat_price_stream_v3(
    req: ChatPriceRequestV3,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE streaming variant of the v3 chat pricing endpoint.

    Emits events:
      - reasoning: agent chain-of-thought
      - tool_call: tool execution start
      - tool_result: tool execution complete
      - pricing: full estimate result
      - token: narrative text chunks
      - clarification: follow-up questions needed
      - done: stream terminator
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio

    async def event_stream():
        result = await agent_v3.process_message(
            message=req.message,
            county=req.county,
            preferred_supplier=req.preferred_supplier,
            history=[{"role": m.role, "content": m.content} for m in (req.history or [])],
            db=db,
            user_id=current_user.id,
            skip_llm_response=True,  # We'll stream narrative separately
        )

        # Emit reasoning
        if result.classification.reasoning:
            yield f"event: reasoning\ndata: {json.dumps({'content': result.classification.reasoning})}\n\n"

        # Emit tool calls
        for tc in result.tool_calls:
            yield f"event: tool_call\ndata: {json.dumps({'tool': tc.tool_name, 'latency_ms': tc.latency_ms})}\n\n"

        # Emit clarification if needed
        if result.clarification_questions:
            yield f"event: clarification\ndata: {json.dumps({'questions': result.clarification_questions})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        # Emit pricing
        if result.estimate.template_code:
            est = result.estimate
            pricing_data = {
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
                "confidence": est.confidence_score,
                "confidence_label": est.confidence_label,
                "assumptions": est.assumptions,
                "market_adjustment_applied": result.overall_market_factor,
            }
            yield f"event: pricing\ndata: {json.dumps(pricing_data)}\n\n"

        # Stream narrative tokens
        if result.estimate.template_code:
            from app.services.llm_service import llm_service
            narrative_stream = llm_service.generate_response_stream(
                message=req.message,
                grand_total=result.estimate.grand_total,
                labor_total=result.estimate.labor_total,
                materials_total=result.estimate.materials_total,
                tax_total=result.estimate.tax_total,
                template_name=result.estimate.template_name or result.classification.task_code or "",
                county=result.classification.county,
                quantity=result.classification.quantity,
                history=[{"role": m.role, "content": m.content} for m in (req.history or [])],
            )
            async for chunk in narrative_stream:
                yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"

        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
