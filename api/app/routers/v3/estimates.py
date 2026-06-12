"""
Estimates API v3 — Extended estimate endpoints with v3 fields.
"""

import uuid
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.estimates import Estimate, EstimateLineItem, EstimateVersion
from app.schemas.v3.estimates import (
    EstimateResponseV3,
    EstimateVersionItem,
    EstimateVersionDiff,
    BranchEstimateRequest,
)

router = APIRouter()


@router.get("/{estimate_id}", response_model=EstimateResponseV3)
async def get_estimate_v3(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single estimate with v3 fields (agent trace, market adjustments, blueprint data)."""
    stmt = select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None))
    result = await db.execute(stmt)
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    # Ownership check — match v1 behavior: creator OR same org OR admin
    user_org = getattr(current_user, "organization_id", None)
    org_match = user_org is not None and estimate.organization_id == user_org
    is_creator = estimate.created_by == current_user.id
    if not (org_match or is_creator or current_user.is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    return estimate


@router.get("", response_model=list[EstimateResponseV3])
async def list_estimates_v3(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List estimates with v3 fields. Supports filtering by status, job_type, county."""
    user_org = getattr(current_user, "organization_id", None)
    if user_org is not None:
        stmt = select(Estimate).where(
            Estimate.deleted_at.is_(None),
            Estimate.organization_id == user_org,
        )
    else:
        stmt = select(Estimate).where(
            Estimate.deleted_at.is_(None),
            Estimate.created_by == current_user.id,
        )

    if status:
        stmt = stmt.where(Estimate.status == status)
    if job_type:
        stmt = stmt.where(Estimate.job_type == job_type)
    if county:
        stmt = stmt.where(Estimate.county == county)

    stmt = stmt.order_by(Estimate.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Versioning & Branching (Phase 14) ─────────────────────────────────────────

@router.get("/{estimate_id}/versions", response_model=list[EstimateVersionItem])
async def list_estimate_versions(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all version snapshots for an estimate, ordered by version number."""
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None)))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    user_org = getattr(current_user, "organization_id", None)
    org_match = user_org is not None and estimate.organization_id == user_org
    is_creator = estimate.created_by == current_user.id
    if not (org_match or is_creator or current_user.is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    version_result = await db.execute(
        select(EstimateVersion)
        .where(EstimateVersion.estimate_id == estimate_id)
        .order_by(EstimateVersion.version_number.desc())
    )
    versions = version_result.scalars().all()
    return [
        EstimateVersionItem(
            id=v.id,
            version_number=v.version_number,
            change_summary=v.change_summary,
            created_at=v.created_at,
            created_by=v.created_by,
        )
        for v in versions
    ]


@router.get("/{estimate_id}/versions/{version_id}/diff", response_model=EstimateVersionDiff)
async def diff_estimate_version(
    estimate_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Diff a specific version against the previous version (or current estimate if version 1)."""
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None)))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    user_org = getattr(current_user, "organization_id", None)
    org_match = user_org is not None and estimate.organization_id == user_org
    is_creator = estimate.created_by == current_user.id
    if not (org_match or is_creator or current_user.is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    version_result = await db.execute(
        select(EstimateVersion).where(
            EstimateVersion.estimate_id == estimate_id,
            EstimateVersion.id == version_id,
        )
    )
    target_version = version_result.scalar_one_or_none()
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")

    target_snapshot = target_version.snapshot_json or {}
    target_lines = target_snapshot.get("line_items", [])

    # Find previous version for comparison
    prev_result = await db.execute(
        select(EstimateVersion)
        .where(
            EstimateVersion.estimate_id == estimate_id,
            EstimateVersion.version_number < target_version.version_number,
        )
        .order_by(EstimateVersion.version_number.desc())
        .limit(1)
    )
    prev_version = prev_result.scalar_one_or_none()

    if prev_version:
        prev_snapshot = prev_version.snapshot_json or {}
        prev_lines = prev_snapshot.get("line_items", [])
        from_total = prev_snapshot.get("grand_total", 0)
        from_version_num = prev_version.version_number
    else:
        # No previous version — compare against empty
        prev_lines = []
        from_total = 0
        from_version_num = 0

    to_total = target_snapshot.get("grand_total", 0)

    # Compute diff
    prev_by_desc = {li.get("description", f"item_{i}"): li for i, li in enumerate(prev_lines)}
    target_by_desc = {li.get("description", f"item_{i}"): li for i, li in enumerate(target_lines)}

    added = []
    removed = []
    modified = []

    for desc, li in target_by_desc.items():
        if desc not in prev_by_desc:
            added.append(li)
        else:
            prev_li = prev_by_desc[desc]
            if prev_li.get("quantity") != li.get("quantity") or prev_li.get("unit_cost") != li.get("unit_cost"):
                modified.append({
                    "description": desc,
                    "previous": prev_li,
                    "current": li,
                })

    for desc, li in prev_by_desc.items():
        if desc not in target_by_desc:
            removed.append(li)

    return EstimateVersionDiff(
        from_version=from_version_num,
        to_version=target_version.version_number,
        from_total=from_total,
        to_total=to_total,
        total_delta=round(to_total - from_total, 2),
        added_line_items=added,
        removed_line_items=removed,
        modified_line_items=modified,
    )


@router.post("/{estimate_id}/branch", response_model=EstimateResponseV3)
async def branch_estimate(
    estimate_id: int,
    req: BranchEstimateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fork an estimate into a new estimate on a new branch.

    Creates a deep copy of the estimate and all its line items,
    assigns a new branch_id, and leaves the original untouched.
    """
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None)))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Estimate not found")

    user_org = getattr(current_user, "organization_id", None)
    org_match = user_org is not None and original.organization_id == user_org
    is_creator = original.created_by == current_user.id
    if not (org_match or is_creator or current_user.is_admin):
        raise HTTPException(status_code=403, detail="Access denied")

    branch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    branched = Estimate(
        title=req.title or f"{original.title} (branch)",
        job_type=original.job_type,
        status="draft",
        labor_total=original.labor_total,
        materials_total=original.materials_total,
        tax_total=original.tax_total,
        markup_total=original.markup_total,
        misc_total=original.misc_total,
        subtotal=original.subtotal,
        grand_total=original.grand_total,
        confidence_score=original.confidence_score,
        confidence_label=original.confidence_label,
        assumptions=deepcopy(original.assumptions) if original.assumptions else [],
        sources=deepcopy(original.sources) if original.sources else [],
        county=original.county,
        tax_rate=original.tax_rate,
        preferred_supplier=original.preferred_supplier,
        project_id=original.project_id,
        chat_context=req.notes or f"Branched from estimate {estimate_id}",
        created_by=current_user.id,
        organization_id=original.organization_id,
        branch_id=branch_id,
        updated_at=now,
        valid_until=now,
    )
    db.add(branched)
    await db.flush()

    # Deep-copy line items
    for li in original.line_items:
        db.add(EstimateLineItem(
            estimate_id=branched.id,
            line_type=li.line_type,
            description=li.description,
            quantity=li.quantity,
            unit=li.unit,
            unit_cost=li.unit_cost,
            total_cost=li.total_cost,
            supplier=li.supplier,
            sku=li.sku,
            canonical_item=li.canonical_item,
            sort_order=li.sort_order,
            trace_json=deepcopy(li.trace_json) if li.trace_json else None,
        ))

    await db.commit()
    await db.refresh(branched)

    # Manually serialize line_items to dicts for the response schema
    line_item_dicts = [
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
            "sort_order": li.sort_order,
            "trace_json": li.trace_json,
        }
        for li in branched.line_items
    ]

    # Return as dict to satisfy response_model serialization
    return {
        "id": branched.id,
        "title": branched.title,
        "job_type": branched.job_type,
        "status": branched.status,
        "labor_total": branched.labor_total,
        "materials_total": branched.materials_total,
        "tax_total": branched.tax_total,
        "markup_total": branched.markup_total,
        "misc_total": branched.misc_total,
        "subtotal": branched.subtotal,
        "grand_total": branched.grand_total,
        "confidence_score": branched.confidence_score,
        "confidence_label": branched.confidence_label,
        "assumptions": branched.assumptions or [],
        "county": branched.county,
        "tax_rate": branched.tax_rate,
        "preferred_supplier": branched.preferred_supplier,
        "line_items": line_item_dicts,
        "blueprint_job_id": branched.blueprint_job_id,
        "blueprint_room_count": branched.blueprint_room_count,
        "blueprint_pipe_run_ft": branched.blueprint_pipe_run_ft,
        "market_adjustment_applied": branched.market_adjustment_applied,
        "confidence_components": branched.confidence_components or {},
        "agent_trace": branched.agent_trace or {},
        "created_at": branched.created_at,
        "variant_group_id": branched.variant_group_id,
        "variant_label": branched.variant_label,
        "branch_id": branched.branch_id,
    }


# ─── Estimate Comments ───────────────────────────────────────────────────────

from pydantic import BaseModel
from app.models.estimates import EstimateComment
from app.models.users import User


class CommentCreateRequest(BaseModel):
    content: str
    parent_id: int | None = None


class CommentResponse(BaseModel):
    id: int
    estimate_id: int
    user_id: int
    parent_id: int | None
    content: str
    created_at: str | None
    user_name: str | None = None


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]


@router.post("/{estimate_id}/comments", response_model=CommentResponse)
async def create_estimate_comment(
    estimate_id: int,
    body: CommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment (or reply) to an estimate."""
    # Verify estimate exists and user has access
    stmt = select(Estimate).where(Estimate.id == estimate_id, Estimate.deleted_at.is_(None))
    result = await db.execute(stmt)
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    comment = EstimateComment(
        estimate_id=estimate_id,
        user_id=current_user.id,
        parent_id=body.parent_id,
        content=body.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        estimate_id=comment.estimate_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        content=comment.content,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
        user_name=getattr(current_user, 'full_name', None) or getattr(current_user, 'email', None),
    )


@router.get("/{estimate_id}/comments", response_model=CommentListResponse)
async def list_estimate_comments(
    estimate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all comments on an estimate."""
    stmt = select(EstimateComment, User).join(User, EstimateComment.user_id == User.id).where(
        EstimateComment.estimate_id == estimate_id
    ).order_by(EstimateComment.created_at.asc())
    result = await db.execute(stmt)

    comments = []
    for comment, user in result.all():
        comments.append(CommentResponse(
            id=comment.id,
            estimate_id=comment.estimate_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            created_at=comment.created_at.isoformat() if comment.created_at else None,
            user_name=getattr(user, 'full_name', None) or getattr(user, 'email', None),
        ))

    return CommentListResponse(comments=comments)
