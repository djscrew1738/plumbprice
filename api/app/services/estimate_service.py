"""
Shared estimate persistence logic used by all estimate-creating endpoints.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.services.audit_service import audit_service
from app.services.pricing_engine import EstimateResult

logger = structlog.get_logger()


def build_estimate_snapshot(estimate: Estimate, line_items: list[EstimateLineItem]) -> dict:
    return {
        "estimate_id": estimate.id,
        "title": estimate.title,
        "job_type": estimate.job_type,
        "status": estimate.status,
        "county": estimate.county,
        "tax_rate": estimate.tax_rate,
        "preferred_supplier": estimate.preferred_supplier,
        "labor_total": estimate.labor_total,
        "materials_total": estimate.materials_total,
        "tax_total": estimate.tax_total,
        "markup_total": estimate.markup_total,
        "misc_total": estimate.misc_total,
        "subtotal": estimate.subtotal,
        "grand_total": estimate.grand_total,
        "confidence_score": estimate.confidence_score,
        "confidence_label": estimate.confidence_label,
        "assumptions": estimate.assumptions or [],
        "sources": estimate.sources or [],
        "chat_context": estimate.chat_context,
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
                "sort_order": item.sort_order,
                "trace_json": item.trace_json,
            }
            for item in line_items
        ],
    }


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

    line_item_rows: list[EstimateLineItem] = []
    for i, item in enumerate(result.line_items):
        row = EstimateLineItem(
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
        )
        db.add(row)
        line_item_rows.append(row)

    await audit_service.log(
        db,
        "estimates",
        "create",
        estimate.id,
        new_values={"grand_total": result.grand_total, "source": source},
    )

    # Snapshot reuses the already-created rows — no duplicate object construction
    snapshot = build_estimate_snapshot(estimate, line_item_rows)
    db.add(EstimateVersion(
        estimate_id=estimate.id,
        version_number=1,
        snapshot_json=snapshot,
        change_summary="Initial estimate version",
    ))

    await db.refresh(estimate)
    return estimate
