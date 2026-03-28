from collections import Counter

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.projects import Project
from app.schemas.projects import ProjectCreateRequest, ProjectListItem, ProjectListResponse

router = APIRouter()
PIPELINE_STATUSES = ["lead", "estimate_sent", "won", "lost", "in_progress", "complete"]


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
    query = (
        select(Project)
        .options(selectinload(Project.estimates))
        .order_by(desc(Project.created_at))
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Project.status == status)

    result = await db.execute(query)
    projects = result.scalars().all()

    summary = {pipeline_status: 0 for pipeline_status in PIPELINE_STATUSES}
    summary.update(Counter(project.status or "lead" for project in projects))

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
                estimate_count=len(project.estimates),
                latest_estimate_total=project.estimates[-1].grand_total if project.estimates else None,
                created_at=project.created_at,
            )
            for project in projects
        ],
        summary=dict(summary),
    )
