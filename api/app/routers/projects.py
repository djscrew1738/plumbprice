from typing import Literal, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.database import get_db
from app.models.estimates import Estimate
from app.models.projects import Project, ProjectActivity
from app.models.users import User
from app.schemas.projects import ProjectCreateRequest, ProjectListItem, ProjectListResponse
from app.services import activity_service
from app.services.notifications_service import notify

router = APIRouter()
logger = structlog.get_logger()
PIPELINE_STATUSES = ["lead", "estimate_sent", "won", "lost", "in_progress", "complete"]

VALID_STATUSES = set(PIPELINE_STATUSES)


async def _get_owned_project(project_id: int, db: AsyncSession, current_user: User) -> Project:
    """Fetch a project and verify the current user has access to it."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_admin:
        user_org = getattr(current_user, "organization_id", None)
        org_match = user_org is not None and project.organization_id == user_org
        is_creator = project.created_by is not None and project.created_by == current_user.id
        if not (org_match or is_creator):
            raise HTTPException(status_code=404, detail="Project not found")
    return project


class ProjectUpdateRequest(BaseModel):
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    notes: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    assigned_to: Optional[int] = None


class ActivityNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


class ActivityActor(BaseModel):
    id: int
    email: Optional[str] = None
    full_name: Optional[str] = None


class ActivityItem(BaseModel):
    id: int
    kind: str
    payload: dict
    actor: Optional[ActivityActor] = None
    created_at: datetime


@router.post("", response_model=ProjectListItem, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        created_by=current_user.id,
        organization_id=getattr(current_user, "organization_id", None),
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
    status: Optional[Literal["lead", "estimate_sent", "won", "lost", "in_progress", "complete"]] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        .where(Project.deleted_at.is_(None))
        .order_by(desc(Project.created_at))
        .limit(limit)
        .offset(offset)
    )
    # Scope to user's org (or own projects if no org assigned)
    user_org = getattr(current_user, "organization_id", None)
    if current_user.is_admin:
        pass  # admin sees all
    elif user_org is not None:
        query = query.where(Project.organization_id == user_org)
    else:
        query = query.where(Project.created_by == current_user.id)

    if status:
        query = query.where(Project.status == status)

    result = await db.execute(query)
    rows = result.all()

    # Count all projects by status scoped to same org/user
    counts_query = select(Project.status, func.count(Project.id)).where(Project.deleted_at.is_(None)).group_by(Project.status)
    if not current_user.is_admin:
        if user_org is not None:
            counts_query = counts_query.where(Project.organization_id == user_org)
        else:
            counts_query = counts_query.where(Project.created_by == current_user.id)
    counts_result = await db.execute(counts_query)
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
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, db, current_user)

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
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, db, current_user)

    prev_status = project.status
    prev_assigned = project.assigned_to

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
    if request.assigned_to is not None:
        project.assigned_to = request.assigned_to

    if request.status is not None and prev_status != project.status:
        await activity_service.log(
            db,
            project_id=project.id,
            actor_user_id=current_user.id,
            kind="stage_changed",
            payload={"from": prev_status, "to": project.status},
        )
    if request.assigned_to is not None and prev_assigned != project.assigned_to:
        await activity_service.log(
            db,
            project_id=project.id,
            actor_user_id=current_user.id,
            kind="assigned",
            payload={"assigned_to": project.assigned_to},
        )
        if project.assigned_to is not None and project.assigned_to != current_user.id:
            await notify(
                db=db,
                user_id=project.assigned_to,
                kind="project_assigned",
                title=f"You were assigned: {project.name}",
                body=f"{current_user.full_name or current_user.email} assigned you to this project.",
                link=f"/projects/{project.id}",
            )

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
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, db, current_user)
    proj_id = project.id
    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("soft_delete", model="project", id=proj_id, actor=current_user.id)


@router.get("/{project_id}/activity", response_model=list[ActivityItem])
async def list_project_activity(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    before: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, db, current_user)

    query = (
        select(ProjectActivity, User)
        .join(User, User.id == ProjectActivity.actor_user_id, isouter=True)
        .where(ProjectActivity.project_id == project.id)
        .order_by(desc(ProjectActivity.created_at), desc(ProjectActivity.id))
        .limit(limit)
    )
    if before is not None:
        query = query.where(ProjectActivity.created_at < before)

    result = await db.execute(query)
    rows = result.all()

    items: list[ActivityItem] = []
    for activity, actor in rows:
        items.append(
            ActivityItem(
                id=activity.id,
                kind=activity.kind,
                payload=activity.payload or {},
                actor=ActivityActor(
                    id=actor.id,
                    email=actor.email,
                    full_name=actor.full_name,
                ) if actor is not None else None,
                created_at=activity.created_at,
            )
        )
    return items


@router.post(
    "/{project_id}/activity",
    response_model=ActivityItem,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_activity_note(
    project_id: int,
    request: ActivityNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, db, current_user)

    activity = ProjectActivity(
        project_id=project.id,
        actor_user_id=current_user.id,
        kind="note_added",
        payload={"note": request.note},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    return ActivityItem(
        id=activity.id,
        kind=activity.kind,
        payload=activity.payload or {},
        actor=ActivityActor(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
        ),
        created_at=activity.created_at,
    )
