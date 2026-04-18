"""
Shared estimate persistence logic used by all estimate-creating endpoints.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import func, select
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
    created_by: Optional[int] = None,
    organization_id: Optional[int] = None,
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
        created_by=created_by,
        organization_id=organization_id,
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

    if project_id is not None:
        from app.services import activity_service

        await activity_service.log(
            db,
            project_id=project_id,
            actor_user_id=created_by,
            kind="estimate_created",
            payload={"estimate_id": estimate.id, "total": result.grand_total},
        )

    await db.refresh(estimate)
    return estimate


def _recompute_totals(line_item_inputs) -> dict:
    """Recompute aggregated totals from a list of line item inputs."""
    labor = sum(
        (i.resolved_total_cost() if hasattr(i, "resolved_total_cost") else i.total_cost or 0)
        for i in line_item_inputs if i.line_type == "labor"
    )
    materials = sum(
        (i.resolved_total_cost() if hasattr(i, "resolved_total_cost") else i.total_cost or 0)
        for i in line_item_inputs if i.line_type == "material"
    )
    markup = sum(
        (i.resolved_total_cost() if hasattr(i, "resolved_total_cost") else i.total_cost or 0)
        for i in line_item_inputs if i.line_type == "markup"
    )
    tax = sum(
        (i.resolved_total_cost() if hasattr(i, "resolved_total_cost") else i.total_cost or 0)
        for i in line_item_inputs if i.line_type == "tax"
    )
    misc = sum(
        (i.resolved_total_cost() if hasattr(i, "resolved_total_cost") else i.total_cost or 0)
        for i in line_item_inputs
        if i.line_type not in ("labor", "material", "markup", "tax")
    )
    subtotal = round(labor + materials + markup + misc, 2)
    grand_total = round(subtotal + tax, 2)
    return {
        "labor_total": round(labor, 2),
        "materials_total": round(materials, 2),
        "markup_total": round(markup, 2),
        "tax_total": round(tax, 2),
        "misc_total": round(misc, 2),
        "subtotal": subtotal,
        "grand_total": grand_total,
    }


async def update_draft_estimate(
    db: AsyncSession,
    estimate: Estimate,
    update_data,
    current_user,
) -> Estimate:
    """
    Apply edits to a draft estimate:
      1. Snapshot current state as a new EstimateVersion (version_number = max + 1).
      2. Delete existing line items and replace with the new ones.
      3. Recompute aggregated totals.
    Raises ValueError if estimate is not draft.
    """
    if estimate.status != "draft":
        raise ValueError("not_draft")

    # Eager-load current line items (selectin means they're already loaded)
    current_items = sorted(estimate.line_items, key=lambda li: li.sort_order or 0)

    # Get next version number
    version_result = await db.execute(
        select(func.max(EstimateVersion.version_number)).where(
            EstimateVersion.estimate_id == estimate.id
        )
    )
    max_version = version_result.scalar() or 0

    snapshot = build_estimate_snapshot(estimate, current_items)
    db.add(EstimateVersion(
        estimate_id=estimate.id,
        version_number=max_version + 1,
        snapshot_json=snapshot,
        change_summary="Pre-edit snapshot",
        created_by=current_user.id if current_user else None,
    ))

    # Replace line items atomically
    for li in list(estimate.line_items):
        await db.delete(li)
    await db.flush()

    totals = _recompute_totals(update_data.line_items)
    for i, item in enumerate(update_data.line_items):
        tc = item.resolved_total_cost()
        db.add(EstimateLineItem(
            estimate_id=estimate.id,
            line_type=item.line_type,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit or "ea",
            unit_cost=item.unit_cost,
            total_cost=tc,
            supplier=item.supplier,
            sku=item.sku,
            canonical_item=item.canonical_item,
            sort_order=i,
        ))

    estimate.labor_total = totals["labor_total"]
    estimate.materials_total = totals["materials_total"]
    estimate.markup_total = totals["markup_total"]
    estimate.tax_total = totals["tax_total"]
    estimate.misc_total = totals["misc_total"]
    estimate.subtotal = totals["subtotal"]
    estimate.grand_total = totals["grand_total"]
    estimate.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(estimate)
    return estimate
