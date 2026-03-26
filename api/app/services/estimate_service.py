"""
Shared estimate persistence logic used by all estimate-creating endpoints.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateLineItem
from app.services.audit_service import audit_service
from app.services.pricing_engine import EstimateResult

logger = structlog.get_logger()


async def persist_estimate(
    db: AsyncSession,
    result: EstimateResult,
    title: str,
    county: str,
    preferred_supplier: Optional[str] = None,
    project_id: Optional[int] = None,
    chat_context: Optional[str] = None,
    source: str = "api",
) -> Estimate:
    """
    Persist an EstimateResult to the database.
    Flushes, writes line items, logs audit, and refreshes the returned model.
    """
    estimate = Estimate(
        title=title,
        job_type=result.job_type,
        status="draft",
        labor_total=result.labor_total,
        materials_total=result.materials_total,
        tax_total=result.tax_total,
        markup_total=result.markup_total,
        misc_total=result.misc_total,
        subtotal=result.subtotal,
        grand_total=result.grand_total,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        assumptions=result.assumptions,
        sources=result.sources,
        county=county,
        tax_rate=result.tax_rate,
        preferred_supplier=preferred_supplier,
        project_id=project_id,
        chat_context=chat_context,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(estimate)
    await db.flush()

    for i, item in enumerate(result.line_items):
        db.add(EstimateLineItem(
            estimate_id=estimate.id,
            line_type=item.line_type,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_cost=item.unit_cost,
            total_cost=item.total_cost,
            supplier=item.supplier,
            sku=item.sku,
            canonical_item=item.canonical_item,
            sort_order=i,
            trace_json=item.trace_json,
        ))

    await audit_service.log(
        db,
        "estimates",
        "create",
        estimate.id,
        new_values={"grand_total": result.grand_total, "source": source},
    )

    await db.refresh(estimate)
    return estimate
