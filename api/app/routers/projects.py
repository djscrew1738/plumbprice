from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.estimates import Estimate
from app.models.projects import Project
from app.schemas.projects import ProjectCreateRequest, ProjectListItem, ProjectListResponse

router = APIRouter()
PIPELINE_STATUSES = ["lead", "estimate_sent", "won", "lost", "in_progress", "complete"]

VALID_STATUSES = set(PIPELINE_STATUSES)


class ProjectUpdateRequest(BaseModel):
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    notes: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None


@router.post("", response_model=ProjectListItem, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        name=request.name,
        job_type=request.job_type,
        status=request.status or "lead",
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        customer_email=request.customer_email,
        address=request.address,
        city=request.city,
        county=request.county,
        state=request.state,
        zip_code=request.zip_code,
        notes=request.notes,
    )
    db.add(project)
    await db.flush()
    await db.commit()
    await db.refresh(project)

    return ProjectListItem(
        id=project.id,
        name=project.name,
        job_type=project.job_type,
        status=project.status,
        customer_name=project.customer_name,
        county=project.county,
        city=project.city,
        estimate_count=0,
        latest_estimate_total=None,
        created_at=project.created_at,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    # Correlated subqueries avoid loading all estimates into memory
    estimate_count_sq = (
        select(func.count(Estimate.id))
        .where(Estimate.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
        .label("estimate_count")
    )
    latest_total_sq = (
        select(Estimate.grand_total)
        .where(Estimate.project_id == Project.id)
        .order_by(desc(Estimate.created_at))
        .limit(1)
        .correlate(Project)
        .scalar_subquery()
        .label("latest_estimate_total")
    )

    query = (
        select(Project, estimate_count_sq, latest_total_sq)
        .order_by(desc(Project.created_at))
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Project.status == status)

    result = await db.execute(query)
    rows = result.all()

    # Count all projects by status (not just the current page)
    counts_result = await db.execute(
        select(Project.status, func.count(Project.id)).group_by(Project.status)
    )
    summary = {pipeline_status: 0 for pipeline_status in PIPELINE_STATUSES}
    for row_status, count in counts_result.all():
        key = row_status or "lead"
        if key in summary:
            summary[key] = count

    return ProjectListResponse(
        projects=[
            ProjectListItem(
                id=project.id,
                name=project.name,
                job_type=project.job_type,
                status=project.status,
                customer_name=project.customer_name,
                county=project.county,
                city=project.city,
                estimate_count=estimate_count or 0,
                latest_estimate_total=latest_total,
                created_at=project.created_at,
            )
            for project, estimate_count, latest_total in rows
        ],
        summary=dict(summary),
    )


@router.get("/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    estimates_result = await db.execute(
        select(Estimate)
        .where(Estimate.project_id == project_id)
        .order_by(desc(Estimate.created_at))
    )
    estimates = estimates_result.scalars().all()

    return {
        "id": project.id,
        "name": project.name,
        "job_type": project.job_type,
        "status": project.status,
        "customer_name": project.customer_name,
        "customer_phone": project.customer_phone,
        "customer_email": project.customer_email,
        "address": project.address,
        "city": project.city,
        "county": project.county,
        "state": project.state,
        "zip_code": project.zip_code,
        "notes": project.notes,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "estimate_count": len(estimates),
        "estimates": [
            {
                "id": e.id,
                "title": e.title,
                "job_type": e.job_type,
                "status": e.status,
                "grand_total": e.grand_total,
                "confidence_label": e.confidence_label or "HIGH",
                "county": e.county or "Dallas",
                "created_at": e.created_at,
            }
            for e in estimates
        ],
    }


@router.patch("/{project_id}", response_model=ProjectListItem)
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.status is not None:
        if request.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(PIPELINE_STATUSES)}")
        project.status = request.status

    if request.customer_name is not None:
        project.customer_name = request.customer_name
    if request.customer_phone is not None:
        project.customer_phone = request.customer_phone
    if request.customer_email is not None:
        project.customer_email = request.customer_email
    if request.notes is not None:
        project.notes = request.notes
    if request.city is not None:
        project.city = request.city
    if request.county is not None:
        project.county = request.county

    await db.commit()
    await db.refresh(project)

    # Use SQL aggregation rather than loading all estimates
    count_row = await db.execute(
        select(func.count(Estimate.id)).where(Estimate.project_id == project.id)
    )
    estimate_count = count_row.scalar() or 0

    latest_total_row = await db.execute(
        select(Estimate.grand_total)
        .where(Estimate.project_id == project.id)
        .order_by(desc(Estimate.created_at))
        .limit(1)
    )
    latest_total = latest_total_row.scalar()

    return ProjectListItem(
        id=project.id,
        name=project.name,
        job_type=project.job_type,
        status=project.status,
        customer_name=project.customer_name,
        county=project.county,
        city=project.city,
        estimate_count=estimate_count or 0,
        latest_estimate_total=latest_total,
        created_at=project.created_at,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
