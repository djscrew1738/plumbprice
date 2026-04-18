"""Blueprint → Estimate converter.

Aggregates detected fixtures from a completed BlueprintJob and persists a draft
Estimate with per-fixture material + labor line items. Pricing reuses
`supplier_service.get_assembly_costs` for materials and `labor_engine` templates
for labor; totals/tax/markup follow the same deterministic rules as
`pricing_engine.calculate_construction_estimate`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blueprints import BlueprintDetection, BlueprintJob, BlueprintPage
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.models.projects import Project
from app.models.users import User
from app.services.audit_service import audit_service
from app.services.estimate_service import build_estimate_snapshot
from app.services.labor_engine import get_template
from app.services.pricing_engine import (
    MARKUP_RULES,
    _DEFAULT_MARKUP_RULES,
    _DEFAULT_TAX_RATES,
)
from app.services.supplier_service import MATERIAL_ASSEMBLIES, supplier_service

logger = structlog.get_logger()


# ─── Fixture-type → Assembly mapping ──────────────────────────────────────────
# Detections from the vision pipeline use loose terms (toilet, lavatory, sink…).
# This table collapses each canonical fixture to an assembly code + labor
# template + human-readable noun. Unknown types are skipped with a log line.
_FIXTURE_MAP: dict[str, tuple[str, str]] = {
    # Toilets / water closets
    "toilet":          ("TOILET_INSTALL_KIT",   "Toilet"),
    "water_closet":    ("TOILET_INSTALL_KIT",   "Water Closet"),
    "wc":              ("TOILET_INSTALL_KIT",   "Water Closet"),
    # Lavatories / bathroom sinks
    "lavatory":        ("LAV_SINK_KIT",         "Lavatory Sink"),
    "lav":             ("LAV_SINK_KIT",         "Lavatory Sink"),
    "bathroom_sink":   ("LAV_SINK_KIT",         "Bathroom Sink"),
    # Kitchen sinks
    "sink":            ("KITCHEN_FAUCET_KIT",   "Kitchen Sink"),
    "kitchen_sink":    ("KITCHEN_FAUCET_KIT",   "Kitchen Sink"),
    # Showers / tubs
    "shower":          ("SHOWER_VALVE_KIT",     "Shower"),
    "tub":             ("TUB_SHOWER_VALVE_KIT", "Tub"),
    "bathtub":         ("TUB_SHOWER_VALVE_KIT", "Bathtub"),
    "tub_shower":      ("TUB_SHOWER_VALVE_KIT", "Tub/Shower"),
    # Water heaters
    "water_heater":    ("WH_50G_GAS_KIT",       "Water Heater"),
    "wh":              ("WH_50G_GAS_KIT",       "Water Heater"),
    # Appliances
    "disposal":        ("DISPOSAL_KIT",         "Garbage Disposal"),
    "garbage_disposal":("DISPOSAL_KIT",         "Garbage Disposal"),
    "dishwasher":      ("DISHWASHER_KIT",       "Dishwasher"),
    # Laundry — treat a washer box as an angle-stop pair for a rough material set
    "laundry":         ("ANGLE_STOP_KIT",       "Laundry Connection"),
    "washing_machine": ("ANGLE_STOP_KIT",       "Washing Machine Box"),
    "washer_box":      ("ANGLE_STOP_KIT",       "Washer Box"),
    # Misc
    "hose_bib":        ("HOSE_BIB_KIT",         "Hose Bib"),
    "prv":             ("PRV_KIT",              "PRV Valve"),
}


def _map_fixture(fixture_type: str) -> Optional[tuple[str, str]]:
    key = (fixture_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    return _FIXTURE_MAP.get(key)


class EmptyTakeoffError(ValueError):
    """Raised when a blueprint has no convertible fixtures."""


async def _load_job(db: AsyncSession, job_id: int) -> Optional[BlueprintJob]:
    result = await db.execute(
        select(BlueprintJob)
        .options(selectinload(BlueprintJob.pages).selectinload(BlueprintPage.detections))
        .where(BlueprintJob.id == job_id)
    )
    return result.scalar_one_or_none()


def _user_owns_job(job: BlueprintJob, user: User) -> bool:
    return job.created_by == user.id or getattr(user, "is_admin", False)


async def create_estimate_from_blueprint(
    db: AsyncSession,
    job_id: int,
    current_user: User,
    project_id: Optional[int] = None,
) -> Estimate:
    """Map detected fixtures to EstimateLineItems and persist as a draft."""
    job = await _load_job(db, job_id)
    if not job or not _user_owns_job(job, current_user):
        raise LookupError("Blueprint job not found")

    # Aggregate detections across pages by canonical fixture type
    totals: dict[str, int] = {}
    for page in job.pages or []:
        for det in page.detections or []:
            totals[det.fixture_type] = totals.get(det.fixture_type, 0) + (det.count or 1)

    if not totals:
        raise EmptyTakeoffError("No fixtures detected for this blueprint")

    # Resolve project for county default + FK
    effective_project_id = project_id if project_id is not None else job.project_id
    county = "Dallas"
    if effective_project_id is not None:
        proj = await db.get(Project, effective_project_id)
        if proj and proj.county:
            county = proj.county

    # Build line items
    line_items: list[dict] = []
    materials_total = 0.0
    labor_total = 0.0
    unmapped: list[str] = []

    for fixture_type, quantity in sorted(totals.items()):
        mapping = _map_fixture(fixture_type)
        if not mapping:
            unmapped.append(fixture_type)
            logger.info("blueprint_to_estimate.unmapped_fixture", fixture_type=fixture_type)
            continue

        assembly_code, display_name = mapping

        # Materials
        items = await supplier_service.get_assembly_costs(assembly_code, db=db)
        assembly_unit_cost = sum(i.total_cost for i in items) if items else 0.0

        if items:
            for i in items:
                extended_qty = i.quantity * quantity
                extended_total = round(i.unit_cost * extended_qty, 2)
                materials_total += extended_total
                line_items.append({
                    "line_type": "material",
                    "description": f"{display_name} — {i.description}",
                    "quantity": extended_qty,
                    "unit": i.unit,
                    "unit_cost": i.unit_cost,
                    "total_cost": extended_total,
                    "supplier": i.supplier,
                    "sku": i.sku,
                    "canonical_item": i.canonical_item,
                })
        else:
            # Fallback: record a zero-cost placeholder so the fixture still shows up
            line_items.append({
                "line_type": "material",
                "description": f"{display_name} — materials (pricing pending)",
                "quantity": float(quantity),
                "unit": "ea",
                "unit_cost": 0.0,
                "total_cost": 0.0,
                "supplier": None,
                "sku": None,
                "canonical_item": assembly_code,
            })

        # Labor — use the assembly's labor template when present
        assembly_def = MATERIAL_ASSEMBLIES.get(assembly_code, {})
        labor_code = assembly_def.get("labor_template")
        template = get_template(labor_code) if labor_code else None
        if template:
            labor_calc = template.calculate_labor_cost()
            unit_labor = float(labor_calc["total_labor_cost"])
            ext = round(unit_labor * quantity, 2)
            labor_total += ext
            line_items.append({
                "line_type": "labor",
                "description": f"{display_name} — install labor ({quantity} ea)",
                "quantity": float(quantity),
                "unit": "fixture",
                "unit_cost": unit_labor,
                "total_cost": ext,
                "supplier": None,
                "sku": None,
                "canonical_item": labor_code,
                "trace_json": labor_calc,
            })

    if not line_items:
        raise EmptyTakeoffError(
            f"No line items could be generated from fixtures: {sorted(totals)}"
        )

    # Totals — mirror pricing_engine.calculate_construction_estimate
    tax_rate = _DEFAULT_TAX_RATES.get(county.lower(), 0.0825)
    rules = MARKUP_RULES.get("construction", _DEFAULT_MARKUP_RULES["construction"])
    materials_markup = round(materials_total * rules["materials_markup_pct"], 2)
    misc_flat = float(rules["misc_flat"])
    tax_amount = round(materials_total * tax_rate, 2)

    if materials_markup > 0:
        line_items.append({
            "line_type": "markup",
            "description": f"Materials Markup ({int(rules['materials_markup_pct'] * 100)}%)",
            "quantity": 1.0, "unit": "lot",
            "unit_cost": materials_markup, "total_cost": materials_markup,
            "supplier": None, "sku": None, "canonical_item": None,
        })
    if misc_flat > 0:
        line_items.append({
            "line_type": "misc",
            "description": "Misc Supplies & Disposal",
            "quantity": 1.0, "unit": "lot",
            "unit_cost": misc_flat, "total_cost": misc_flat,
            "supplier": None, "sku": None, "canonical_item": None,
        })
    if tax_amount > 0:
        line_items.append({
            "line_type": "tax",
            "description": f"Sales Tax — {county} County ({tax_rate*100:.2f}%)",
            "quantity": 1.0, "unit": "lot",
            "unit_cost": tax_amount, "total_cost": tax_amount,
            "supplier": None, "sku": None, "canonical_item": None,
        })

    subtotal = round(labor_total + materials_total + materials_markup + misc_flat, 2)
    grand_total = round(subtotal + tax_amount, 2)

    fixture_count = sum(totals.values())
    assumptions = [
        f"Generated from blueprint #{job.id} ({job.original_filename or job.filename})",
        f"Detected {fixture_count} fixtures across {len(job.pages or [])} page(s)",
        f"County: {county}, Tax rate: {tax_rate*100:.2f}%",
    ]
    if unmapped:
        assumptions.append(
            f"Unmapped fixture types (excluded): {', '.join(sorted(set(unmapped)))}"
        )

    # Persist
    title = f"Blueprint Estimate — {job.original_filename or job.filename}"
    estimate = Estimate(
        title=title,
        job_type="construction",
        status="draft",
        labor_total=round(labor_total, 2),
        materials_total=round(materials_total, 2),
        tax_total=tax_amount,
        markup_total=materials_markup,
        misc_total=misc_flat,
        subtotal=subtotal,
        grand_total=grand_total,
        confidence_score=0.7,
        confidence_label="MEDIUM",
        assumptions=assumptions,
        sources=[f"Blueprint job #{job.id}"],
        county=county,
        tax_rate=tax_rate,
        project_id=effective_project_id,
        blueprint_job_id=job.id,
        created_by=current_user.id,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(estimate)
    await db.flush()

    line_item_rows: list[EstimateLineItem] = []
    for idx, li in enumerate(line_items):
        row = EstimateLineItem(
            estimate_id=estimate.id,
            line_type=li["line_type"],
            description=li["description"],
            quantity=li["quantity"],
            unit=li["unit"],
            unit_cost=li["unit_cost"],
            total_cost=li["total_cost"],
            supplier=li.get("supplier"),
            sku=li.get("sku"),
            canonical_item=li.get("canonical_item"),
            sort_order=idx,
            trace_json=li.get("trace_json"),
        )
        db.add(row)
        line_item_rows.append(row)

    await audit_service.log(
        db,
        "estimates",
        "create",
        estimate.id,
        new_values={"grand_total": grand_total, "source": "blueprint", "blueprint_job_id": job.id},
    )

    snapshot = build_estimate_snapshot(estimate, line_item_rows)
    db.add(EstimateVersion(
        estimate_id=estimate.id,
        version_number=1,
        snapshot_json=snapshot,
        change_summary=f"Initial draft generated from blueprint #{job.id}",
    ))

    if effective_project_id is not None:
        try:
            from app.services import activity_service
            await activity_service.log(
                db,
                project_id=effective_project_id,
                actor_user_id=current_user.id,
                kind="estimate_created",
                payload={
                    "estimate_id": estimate.id,
                    "total": grand_total,
                    "source": "blueprint",
                    "blueprint_job_id": job.id,
                },
            )
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("blueprint_to_estimate.activity_log_failed", error=str(e))

    await db.commit()
    await db.refresh(estimate)

    logger.info(
        "blueprint_to_estimate.created",
        estimate_id=estimate.id,
        job_id=job_id,
        fixture_count=fixture_count,
        line_items=len(line_item_rows),
        grand_total=grand_total,
    )
    return estimate
