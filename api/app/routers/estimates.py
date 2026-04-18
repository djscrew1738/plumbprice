from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.models.users import User
from app.schemas.estimates import (
    ServiceEstimateRequest, ConstructionEstimateRequest,
    EstimateResponse, EstimateListItem, EstimateVersionItem, EstimateVersionListResponse,
    EstimateUpdateRequest,
)
from app.services.pricing_engine import pricing_engine
from app.services.supplier_service import supplier_service
from app.services.estimate_service import persist_estimate, update_draft_estimate

logger = structlog.get_logger()
router = APIRouter()

VALID_ESTIMATE_STATUSES = {"draft", "sent", "accepted", "rejected"}


async def _get_owned_estimate(estimate_id: int, db: AsyncSession, current_user: User) -> Estimate:
    """Fetch an estimate and verify the current user has access to it."""
    result = await db.execute(
        select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None))
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    # Admin can access any estimate; otherwise must be creator OR same org (with non-null org)
    if not current_user.is_admin:
        user_org = getattr(current_user, "organization_id", None)
        org_match = user_org is not None and estimate.organization_id == user_org
        is_creator = estimate.created_by is not None and estimate.created_by == current_user.id
        if not (org_match or is_creator):
            raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


def _is_expired(estimate: Estimate) -> bool:
    if not estimate.valid_until:
        return False
    # Naive datetimes (e.g. SQLite) are treated as UTC for comparison purposes.
    valid_until = estimate.valid_until
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    return valid_until < datetime.now(timezone.utc)


class EstimateStatusUpdate(BaseModel):
    status: str


@router.post("/service", response_model=EstimateResponse)
async def create_service_estimate(
    request: ServiceEstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a deterministic service estimate from a labor template."""
    try:
        materials = []
        if request.assembly_code:
            materials = await supplier_service.get_assembly_costs(
                request.assembly_code,
                preferred_supplier=request.preferred_supplier,
                db=db,
            )

        result = pricing_engine.calculate_service_estimate(
            task_code=request.task_code,
            materials=materials,
            assembly_code=request.assembly_code,
            access=request.access_type,
            urgency=request.urgency,
            county=request.county,
            city=request.city,
            include_trip_charge=request.include_trip_charge,
            preferred_supplier=request.preferred_supplier,
        )

        estimate = await persist_estimate(
            db=db,
            result=result,
            title=f"{request.task_code} — {request.city or request.county}",
            county=request.county,
            preferred_supplier=request.preferred_supplier,
            project_id=request.project_id,
            created_by=current_user.id,
            organization_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
        )

        return EstimateResponse(
            id=estimate.id,
            title=estimate.title,
            job_type=estimate.job_type,
            status=estimate.status,
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
            county=request.county,
            tax_rate=result.tax_rate,
            preferred_supplier=request.preferred_supplier,
            line_items=[
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                    "supplier": li.supplier,
                }
                for li in result.line_items
            ],
            created_at=estimate.created_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Service estimate error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating the estimate")


@router.post("/construction", response_model=EstimateResponse)
async def create_construction_estimate(
    request: ConstructionEstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new construction estimate."""
    try:
        result = pricing_engine.calculate_construction_estimate(
            bath_groups=request.bath_groups,
            fixture_count=request.fixture_count,
            underground_lf=request.underground_lf,
            county=request.county,
            preferred_supplier=request.preferred_supplier,
        )

        estimate = await persist_estimate(
            db=db,
            result=result,
            title=f"New Construction — {request.bath_groups} Bath Groups — {request.county}",
            county=request.county,
            preferred_supplier=request.preferred_supplier,
            project_id=request.project_id,
            created_by=current_user.id,
            organization_id=current_user.organization_id if hasattr(current_user, "organization_id") else None,
            source="construction",
        )

        return EstimateResponse(
            id=estimate.id,
            title=estimate.title,
            job_type="construction",
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
            county=request.county,
            tax_rate=result.tax_rate,
            preferred_supplier=request.preferred_supplier,
            line_items=[
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                }
                for li in result.line_items
            ],
            created_at=estimate.created_at,
        )

    except Exception as e:
        logger.error("Construction estimate error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating the estimate")


@router.get("", response_model=list[EstimateListItem])
async def list_estimates(
    status: Optional[Literal["draft", "sent", "accepted", "rejected"]] = Query(None),
    job_type: Optional[Literal["service", "construction", "rough_in", "remodel", "commercial"]] = Query(None),
    exclude_expired: bool = Query(False, description="Hide estimates whose valid_until is in the past"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List estimates with optional filters (scoped to current user's organization)."""
    query = select(Estimate).where(Estimate.deleted_at.is_(None)).order_by(desc(Estimate.created_at)).limit(limit).offset(offset)
    user_org = getattr(current_user, "organization_id", None)
    if not current_user.is_admin:
        if user_org is not None:
            query = query.where(Estimate.organization_id == user_org)
        else:
            query = query.where(Estimate.created_by == current_user.id)
    if status:
        query = query.where(Estimate.status == status)
    if job_type:
        query = query.where(Estimate.job_type == job_type)
    if exclude_expired:
        now = datetime.now(timezone.utc)
        query = query.where((Estimate.valid_until.is_(None)) | (Estimate.valid_until >= now))

    result = await db.execute(query)
    estimates = result.scalars().all()

    return [
        EstimateListItem(
            id=e.id,
            title=e.title,
            job_type=e.job_type,
            status=e.status,
            grand_total=e.grand_total,
            confidence_label=e.confidence_label or "HIGH",
            county=e.county or "Dallas",
            created_at=e.created_at,
            valid_until=e.valid_until,
            is_expired=_is_expired(e),
        )
        for e in estimates
    ]


@router.get("/{estimate_id}")
async def get_estimate(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single estimate with line items (eager-loaded via selectin)."""
    estimate = await _get_owned_estimate(estimate_id, db, current_user)

    # line_items are eager-loaded via lazy="selectin" — no second query needed
    line_items = sorted(estimate.line_items, key=lambda li: li.sort_order or 0)

    return {
        "id": estimate.id,
        "title": estimate.title,
        "job_type": estimate.job_type,
        "status": estimate.status,
        "project_id": estimate.project_id,
        "labor_total": estimate.labor_total,
        "materials_total": estimate.materials_total,
        "tax_total": estimate.tax_total,
        "markup_total": estimate.markup_total,
        "misc_total": estimate.misc_total,
        "subtotal": estimate.subtotal,
        "grand_total": estimate.grand_total,
        "confidence_score": estimate.confidence_score,
        "confidence_label": estimate.confidence_label,
        "assumptions": estimate.assumptions,
        "sources": estimate.sources,
        "county": estimate.county,
        "tax_rate": estimate.tax_rate,
        "preferred_supplier": estimate.preferred_supplier,
        "blueprint_job_id": estimate.blueprint_job_id,
        "valid_until": estimate.valid_until,
        "is_expired": _is_expired(estimate),
        "created_at": estimate.created_at,
        "line_items": [
            {
                "id": li.id,
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
            for li in line_items
        ],
    }


@router.get("/{estimate_id}/versions", response_model=EstimateVersionListResponse)
async def list_estimate_versions(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    estimate = await _get_owned_estimate(estimate_id, db, current_user)

    versions_result = await db.execute(
        select(EstimateVersion)
        .where(EstimateVersion.estimate_id == estimate_id)
        .order_by(desc(EstimateVersion.version_number))
    )
    versions = versions_result.scalars().all()

    return EstimateVersionListResponse(
        estimate_id=estimate_id,
        versions=[
            EstimateVersionItem(
                id=version.id,
                version_number=version.version_number,
                snapshot=version.snapshot_json,
                change_summary=version.change_summary,
                created_at=version.created_at,
            )
            for version in versions
        ],
    )


@router.get("/{estimate_id}/cost-breakdown")
async def get_cost_breakdown(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a percentage breakdown of costs for an estimate."""
    estimate = await _get_owned_estimate(estimate_id, db, current_user)

    grand_total = estimate.grand_total or 0.0
    category_amounts = {
        "labor": estimate.labor_total or 0.0,
        "materials": estimate.materials_total or 0.0,
        "tax": estimate.tax_total or 0.0,
        "markup": estimate.markup_total or 0.0,
        "misc": estimate.misc_total or 0.0,
    }

    # Add trip and permit from line items (not stored as top-level model fields)
    trip_total = sum(
        li.total_cost for li in estimate.line_items if li.line_type == "trip"
    )
    permit_total = sum(
        li.total_cost for li in estimate.line_items if li.line_type == "permit"
    )
    if trip_total > 0:
        category_amounts["trip"] = trip_total
    if permit_total > 0:
        category_amounts["permit"] = permit_total

    breakdown = {
        category: {
            "amount": amount,
            "pct": round(amount / grand_total * 100, 2) if grand_total else 0.0,
        }
        for category, amount in category_amounts.items()
    }

    return {
        "estimate_id": estimate.id,
        "grand_total": grand_total,
        "breakdown": breakdown,
        "confidence_score": estimate.confidence_score,
        "confidence_label": estimate.confidence_label,
    }


@router.patch("/{estimate_id}")
async def patch_estimate(
    estimate_id: int,
    body: EstimateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a draft estimate's line items and recompute totals. Creates a version snapshot first."""
    estimate = await _get_owned_estimate(estimate_id, db, current_user)
    if estimate.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft estimates can be edited")
    try:
        estimate = await update_draft_estimate(db, estimate, body, current_user)
    except ValueError:
        raise HTTPException(status_code=409, detail="Only draft estimates can be edited")

    line_items = sorted(estimate.line_items, key=lambda li: li.sort_order or 0)
    return {
        "id": estimate.id,
        "title": estimate.title,
        "job_type": estimate.job_type,
        "status": estimate.status,
        "labor_total": estimate.labor_total,
        "materials_total": estimate.materials_total,
        "tax_total": estimate.tax_total,
        "markup_total": estimate.markup_total,
        "misc_total": estimate.misc_total,
        "subtotal": estimate.subtotal,
        "grand_total": estimate.grand_total,
        "confidence_score": estimate.confidence_score,
        "confidence_label": estimate.confidence_label,
        "assumptions": estimate.assumptions,
        "county": estimate.county,
        "tax_rate": estimate.tax_rate,
        "line_items": [
            {
                "id": li.id,
                "line_type": li.line_type,
                "description": li.description,
                "quantity": li.quantity,
                "unit": li.unit,
                "unit_cost": li.unit_cost,
                "total_cost": li.total_cost,
                "supplier": li.supplier,
                "sku": li.sku,
                "trace_json": li.trace_json,
            }
            for li in line_items
        ],
    }


@router.patch("/{estimate_id}/status")
async def update_estimate_status(    estimate_id: int,
    body: EstimateStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update estimate status (draft → sent → accepted/rejected)."""
    if body.status not in VALID_ESTIMATE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_ESTIMATE_STATUSES))}",
        )
    estimate = await _get_owned_estimate(estimate_id, db, current_user)
    estimate.status = body.status
    await db.commit()
    await db.refresh(estimate)
    return {"id": estimate.id, "status": estimate.status}


@router.post("/{estimate_id}/duplicate", response_model=EstimateResponse, status_code=http_status.HTTP_201_CREATED)
async def duplicate_estimate(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Duplicate an estimate: creates a copy with status=draft, title appended ' (copy)', and all line items copied."""
    original_estimate = await _get_owned_estimate(estimate_id, db, current_user)

    # line_items eager-loaded via selectin — no extra query
    original_line_items = sorted(original_estimate.line_items, key=lambda li: li.sort_order or 0)

    new_estimate = Estimate(
        project_id=original_estimate.project_id,
        title=f"{original_estimate.title} (copy)",
        job_type=original_estimate.job_type,
        status="draft",
        labor_total=original_estimate.labor_total,
        materials_total=original_estimate.materials_total,
        tax_total=original_estimate.tax_total,
        markup_total=original_estimate.markup_total,
        misc_total=original_estimate.misc_total,
        subtotal=original_estimate.subtotal,
        grand_total=original_estimate.grand_total,
        confidence_score=original_estimate.confidence_score,
        confidence_label=original_estimate.confidence_label,
        assumptions=original_estimate.assumptions,
        sources=original_estimate.sources,
        chat_context=original_estimate.chat_context,
        county=original_estimate.county,
        tax_rate=original_estimate.tax_rate,
        preferred_supplier=original_estimate.preferred_supplier,
        created_by=current_user.id,
        organization_id=original_estimate.organization_id,
        valid_until=original_estimate.valid_until,
    )
    db.add(new_estimate)
    await db.flush()

    copied_items = []
    for original_li in original_line_items:
        new_li = EstimateLineItem(
            estimate_id=new_estimate.id,
            line_type=original_li.line_type,
            description=original_li.description,
            quantity=original_li.quantity,
            unit=original_li.unit,
            unit_cost=original_li.unit_cost,
            total_cost=original_li.total_cost,
            supplier=original_li.supplier,
            sku=original_li.sku,
            canonical_item=original_li.canonical_item,
            sort_order=original_li.sort_order,
            trace_json=original_li.trace_json,
        )
        db.add(new_li)
        copied_items.append(new_li)

    await db.commit()
    await db.refresh(new_estimate)

    return EstimateResponse(
        id=new_estimate.id,
        title=new_estimate.title,
        job_type=new_estimate.job_type,
        status=new_estimate.status,
        labor_total=new_estimate.labor_total,
        materials_total=new_estimate.materials_total,
        tax_total=new_estimate.tax_total,
        markup_total=new_estimate.markup_total,
        misc_total=new_estimate.misc_total,
        subtotal=new_estimate.subtotal,
        grand_total=new_estimate.grand_total,
        confidence_score=new_estimate.confidence_score,
        confidence_label=new_estimate.confidence_label,
        assumptions=new_estimate.assumptions,
        county=new_estimate.county,
        tax_rate=new_estimate.tax_rate,
        preferred_supplier=new_estimate.preferred_supplier,
        line_items=[
            {
                "line_type": li.line_type,
                "description": li.description,
                "quantity": li.quantity,
                "unit": li.unit,
                "unit_cost": li.unit_cost,
                "total_cost": li.total_cost,
                "supplier": li.supplier,
            }
            for li in copied_items
        ],
        created_at=new_estimate.created_at,
    )


@router.delete("/{estimate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_estimate(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an estimate."""
    estimate = await _get_owned_estimate(estimate_id, db, current_user)
    await db.delete(estimate)
    await db.commit()
