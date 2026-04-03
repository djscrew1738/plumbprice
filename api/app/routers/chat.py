from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.schemas.chat import ChatPriceRequest, ChatPriceResponse
from app.services.agent import process_chat_message
from app.services.estimate_service import persist_estimate

logger = structlog.get_logger()
router = APIRouter()


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


@router.post("/price", response_model=ChatPriceResponse)
async def chat_price(
    request: ChatPriceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat pricing endpoint. Accepts natural language plumbing queries
    and returns deterministic pricing with full trace.
    """
    try:
        result = await process_chat_message(
            message=request.message,
            county=request.county or None,
            preferred_supplier=request.preferred_supplier,
            job_type=request.job_type,
            db=db,
        )

        estimate_result = result.pop("_estimate_result", None)

        estimate_id = None
        if estimate_result is not None:
            estimate = await persist_estimate(
                db=db,
                result=estimate_result,
                title=request.message[:100] or "Chat Estimate",
                county=request.county or "Dallas",
                preferred_supplier=request.preferred_supplier,
                chat_context=request.message,
                source="chat",
            )
            estimate_id = estimate.id
            await db.commit()

        estimate_payload = result.get("estimate")
        if estimate_result is not None:
            estimate_payload = build_estimate_breakdown(estimate_result)

        classified_by = result.get("classification", {}).get("classified_by")

        return ChatPriceResponse(
            answer=result["answer"],
            estimate=estimate_payload,
            estimate_id=estimate_id,
            confidence=result["confidence"],
            confidence_label=result["confidence_label"],
            assumptions=result.get("assumptions", []),
            sources=result.get("sources", []),
            job_type_detected=result.get("job_type_detected"),
            template_used=result.get("template_used"),
            classified_by=classified_by,
        )

    except Exception as e:
        logger.error("Chat pricing error", error=str(e), message=request.message)
        raise HTTPException(status_code=500, detail=f"Pricing error: {str(e)}")
