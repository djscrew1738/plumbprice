from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.database import get_db
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.schemas.estimates import (
    ServiceEstimateRequest, ConstructionEstimateRequest,
    EstimateResponse, EstimateListItem, EstimateVersionItem, EstimateVersionListResponse
)
from app.services.pricing_engine import pricing_engine
from app.services.supplier_service import supplier_service
from app.services.estimate_service import persist_estimate

logger = structlog.get_logger()
router = APIRouter()

VALID_ESTIMATE_STATUSES = {"draft", "sent", "accepted", "rejected"}


class EstimateStatusUpdate(BaseModel):
    status: str


@router.post("/service", response_model=EstimateResponse)
async def create_service_estimate(
    request: ServiceEstimateRequest,
    db: AsyncSession = Depends(get_db),
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
            preferred_supplier=request.preferred_supplier,
        )

        estimate = await persist_estimate(
            db=db,
            result=result,
            title=f"{request.task_code} — {request.county}",
            county=request.county,
            preferred_supplier=request.preferred_supplier,
            project_id=request.project_id,
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
        logger.error("Service estimate error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/construction", response_model=EstimateResponse)
async def create_construction_estimate(
    request: ConstructionEstimateRequest,
    db: AsyncSession = Depends(get_db),
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
        logger.error("Construction estimate error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[EstimateListItem])
async def list_estimates(
    status: str = Query(None),
    job_type: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """List estimates with optional filters."""
    query = select(Estimate).order_by(desc(Estimate.created_at)).limit(limit).offset(offset)
    if status:
        query = query.where(Estimate.status == status)
    if job_type:
        query = query.where(Estimate.job_type == job_type)

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
        )
        for e in estimates
    ]


@router.get("/{estimate_id}")
async def get_estimate(estimate_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single estimate with line items."""
    result = await db.execute(
        select(Estimate).where(Estimate.id == estimate_id)
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    li_result = await db.execute(
        select(EstimateLineItem)
        .where(EstimateLineItem.estimate_id == estimate_id)
        .order_by(EstimateLineItem.sort_order)
    )
    line_items = li_result.scalars().all()

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
        "sources": estimate.sources,
        "county": estimate.county,
        "tax_rate": estimate.tax_rate,
        "preferred_supplier": estimate.preferred_supplier,
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
            }
            for li in line_items
        ],
    }


@router.get("/{estimate_id}/versions", response_model=EstimateVersionListResponse)
async def list_estimate_versions(estimate_id: int, db: AsyncSession = Depends(get_db)):
    estimate_result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = estimate_result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

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


@router.patch("/{estimate_id}/status")
async def update_estimate_status(
    estimate_id: int,
    body: EstimateStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update estimate status (draft → sent → accepted/rejected)."""
    if body.status not in VALID_ESTIMATE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_ESTIMATE_STATUSES))}",
        )
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    estimate.status = body.status
    await db.commit()
    await db.refresh(estimate)
    return {"id": estimate.id, "status": estimate.status}


@router.delete("/{estimate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_estimate(estimate_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an estimate."""
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    await db.delete(estimate)
    await db.commit()
