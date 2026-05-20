"""Blueprint → Estimate converter — v3 with rooms + pipe runs.

Extends the v1 converter by adding:
  * Pipe run line items (materials per linear foot + labor per linear foot)
  * Room context in assumptions and v3 estimate fields
  * v3 columns: blueprint_room_count, blueprint_pipe_run_ft, confidence_components
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.blueprints import BlueprintJob, BlueprintPage
from app.models.blueprint_rooms import BlueprintRoom
from app.models.blueprint_pipe_runs import BlueprintPipeRun
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.models.projects import Project
from app.models.users import User
from app.services.audit_service import audit_service
from app.services.estimate_service import build_estimate_snapshot
from app.services.labor_engine import get_template
from app.services.pricing_config_service import pricing_config_service
from app.services.supplier_service import MATERIAL_ASSEMBLIES, supplier_service
from app.services.blueprint_to_estimate import (
    _FIXTURE_MAP,
    _map_fixture,
    EmptyTakeoffError,
)

logger = structlog.get_logger()


# ─── Pipe-type → per-foot pricing ─────────────────────────────────────────────
# Approximate material + labor cost per linear foot. These are MVP defaults;
# they should be overridden by supplier pricing data when available.
_PIPE_COST_PER_FT: dict[str, tuple[float, float]] = {
    # (material_cost_per_ft, labor_cost_per_ft)
    "copper_3_4": (3.50, 2.00),
    "copper_1_2": (2.80, 1.80),
    "copper_1":   (4.20, 2.40),
    "pvc_3":      (1.80, 1.20),
    "pvc_4":      (2.20, 1.40),
    "pex_1_2":    (0.80, 0.90),
    "pex_3_4":    (1.10, 1.00),
    "pex_1":      (1.50, 1.20),
    "galvanized_3_4": (2.50, 1.80),
    "cast_iron_4":    (3.00, 2.50),
}

# Fallback for unknown pipe types
_DEFAULT_PIPE_COST = (2.00, 1.50)


# ─── Room-type → rough-in assembly mapping ────────────────────────────────────
# When a room is detected but no fixtures are mapped for it, we can add a
# rough-in placeholder so the estimator knows to review.
_ROOM_ROUGHIN_MAP: dict[str, tuple[str, str]] = {
    "bathroom": ("LAV_SINK_KIT", "Bathroom rough-in (review fixtures)"),
    "kitchen":  ("KITCHEN_FAUCET_KIT", "Kitchen rough-in (review fixtures)"),
    "utility":  ("ANGLE_STOP_KIT", "Utility/Laundry rough-in"),
}


async def _load_job_v3(db: AsyncSession, job_id: int) -> Optional[BlueprintJob]:
    result = await db.execute(
        select(BlueprintJob)
        .options(
            selectinload(BlueprintJob.pages).selectinload(BlueprintPage.detections),
            selectinload(BlueprintJob.rooms),
            selectinload(BlueprintJob.pipe_runs),
        )
        .where(BlueprintJob.id == job_id)
    )
    return result.scalar_one_or_none()


def _user_owns_job(job: BlueprintJob, user: User) -> bool:
    return job.created_by == user.id or getattr(user, "is_admin", False)


async def create_estimate_from_blueprint_v3(
    db: AsyncSession,
    job_id: int,
    current_user: User,
    project_id: Optional[int] = None,
) -> Estimate:
    """Map detected fixtures, rooms, and pipe runs to EstimateLineItems and persist as a draft."""
    job = await _load_job_v3(db, job_id)
    if not job or not _user_owns_job(job, current_user):
        raise LookupError("Blueprint job not found")

    # ── Aggregate fixtures ───────────────────────────────────────────────────
    totals: dict[str, int] = {}
    for page in job.pages or []:
        for det in page.detections or []:
            totals[det.fixture_type] = totals.get(det.fixture_type, 0) + (det.count or 1)

    # ── Aggregate rooms ──────────────────────────────────────────────────────
    rooms = list(job.rooms or [])
    room_counts: dict[str, int] = {}
    for r in rooms:
        room_counts[r.room_type] = room_counts.get(r.room_type, 0) + 1

    # ── Aggregate pipe runs ──────────────────────────────────────────────────
    pipe_runs = list(job.pipe_runs or [])
    pipe_totals: dict[str, float] = {}
    for p in pipe_runs:
        pipe_totals[p.pipe_type] = pipe_totals.get(p.pipe_type, 0.0) + p.length_ft

    if not totals and not pipe_totals:
        raise EmptyTakeoffError("No fixtures or pipe runs detected for this blueprint")

    # ── Resolve project/county ───────────────────────────────────────────────
    effective_project_id = project_id if project_id is not None else job.project_id
    county = "Dallas"
    if effective_project_id is not None:
        proj = await db.get(Project, effective_project_id)
        if proj and proj.county:
            county = proj.county

    # ── Build line items ─────────────────────────────────────────────────────
    line_items: list[dict] = []
    materials_total = 0.0
    labor_total = 0.0
    unmapped: list[str] = []

    # Fixtures
    for fixture_type, quantity in sorted(totals.items()):
        mapping = _map_fixture(fixture_type)
        if not mapping:
            unmapped.append(fixture_type)
            logger.info("blueprint_to_estimate_v3.unmapped_fixture", fixture_type=fixture_type)
            continue

        assembly_code, display_name = mapping
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

    # Pipe runs
    for pipe_type, length_ft in sorted(pipe_totals.items()):
        mat_cost_per_ft, labor_cost_per_ft = _PIPE_COST_PER_FT.get(pipe_type, _DEFAULT_PIPE_COST)
        mat_total = round(mat_cost_per_ft * length_ft, 2)
        labor_ext = round(labor_cost_per_ft * length_ft, 2)
        materials_total += mat_total
        labor_total += labor_ext

        display_pipe = pipe_type.replace("_", " ").title()
        line_items.append({
            "line_type": "material",
            "description": f"{display_pipe} — pipe & fittings ({length_ft:.0f} ft)",
            "quantity": round(length_ft, 2),
            "unit": "ft",
            "unit_cost": mat_cost_per_ft,
            "total_cost": mat_total,
            "supplier": None,
            "sku": None,
            "canonical_item": f"pipe.{pipe_type}",
        })
        line_items.append({
            "line_type": "labor",
            "description": f"{display_pipe} — install labor ({length_ft:.0f} ft)",
            "quantity": round(length_ft, 2),
            "unit": "ft",
            "unit_cost": labor_cost_per_ft,
            "total_cost": labor_ext,
            "supplier": None,
            "sku": None,
            "canonical_item": f"labor.pipe_{pipe_type}",
        })

    # Room rough-in placeholders (only if no fixtures were mapped for that room type)
    for room_type, count in sorted(room_counts.items()):
        if room_type not in totals and room_type in _ROOM_ROUGHIN_MAP:
            assembly_code, desc = _ROOM_ROUGHIN_MAP[room_type]
            line_items.append({
                "line_type": "labor",
                "description": f"{desc} ({count} room{'s' if count > 1 else ''}) — review required",
                "quantity": float(count),
                "unit": "room",
                "unit_cost": 0.0,
                "total_cost": 0.0,
                "supplier": None,
                "sku": None,
                "canonical_item": assembly_code,
            })

    if not line_items:
        raise EmptyTakeoffError(
            f"No line items could be generated from blueprint #{job.id}"
        )

    # ── Totals ───────────────────────────────────────────────────────────────
    tax_rate = pricing_config_service.get_tax_rate(county)
    rules = pricing_config_service.get_markup_rule("construction")
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
    total_pipe_ft = round(sum(pipe_totals.values()), 2)
    total_rooms = len(rooms)

    assumptions = [
        f"Generated from blueprint #{job.id} ({job.original_filename or job.filename})",
        f"Detected {fixture_count} fixtures across {len(job.pages or [])} page(s)",
        f"Detected {total_rooms} room(s) and {total_pipe_ft:.0f} ft of pipe runs",
        f"County: {county}, Tax rate: {tax_rate*100:.2f}%",
    ]
    if unmapped:
        assumptions.append(
            f"Unmapped fixture types (excluded): {', '.join(sorted(set(unmapped)))}"
        )

    # ── Persist ──────────────────────────────────────────────────────────────
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
        confidence_score=0.75,
        confidence_label="MEDIUM",
        confidence_components={
            "fixture_detection": 0.8,
            "pipe_run_detection": 0.7 if pipe_runs else 1.0,
            "room_detection": 0.75 if rooms else 1.0,
        },
        assumptions=assumptions,
        sources=[f"Blueprint job #{job.id}"],
        county=county,
        tax_rate=tax_rate,
        project_id=effective_project_id,
        blueprint_job_id=job.id,
        created_by=current_user.id,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        # v3 fields
        blueprint_room_count=total_rooms or None,
        blueprint_pipe_run_ft=total_pipe_ft or None,
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
        new_values={
            "grand_total": grand_total,
            "source": "blueprint_v3",
            "blueprint_job_id": job.id,
            "rooms": total_rooms,
            "pipe_ft": total_pipe_ft,
        },
    )

    snapshot = build_estimate_snapshot(estimate, line_item_rows)
    db.add(EstimateVersion(
        estimate_id=estimate.id,
        version_number=1,
        snapshot_json=snapshot,
        change_summary=f"Initial draft generated from blueprint #{job.id} (v3)",
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
                    "source": "blueprint_v3",
                    "blueprint_job_id": job.id,
                },
            )
        except Exception as e:
            logger.warning("blueprint_to_estimate_v3.activity_log_failed", error=str(e))

    await db.commit()
    await db.refresh(estimate)

    logger.info(
        "blueprint_to_estimate_v3.created",
        estimate_id=estimate.id,
        job_id=job_id,
        fixture_count=fixture_count,
        rooms=total_rooms,
        pipe_ft=total_pipe_ft,
        line_items=len(line_item_rows),
        grand_total=grand_total,
    )
    return estimate
