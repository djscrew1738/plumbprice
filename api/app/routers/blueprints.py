from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
import os
import io

from app.core.auth import get_current_user
from app.core.broker import broker_available
from app.database import get_db
from app.schemas.blueprints import BlueprintJobResponse
from app.services.blueprint_service import blueprint_service
from app.models.blueprints import BlueprintJob
from app.models.users import User
from app.core.storage import storage_client
from app.config import settings
from app.core.limiter import limiter

try:
    from worker.tasks.blueprint_analysis import analyze_blueprint as _analyze_blueprint
    _worker_available = True
except ImportError:
    _analyze_blueprint = None
    _worker_available = False

logger = structlog.get_logger()
router = APIRouter()

_MAX_BLUEPRINT_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post("/upload", response_model=BlueprintJobResponse)
@limiter.limit("10/minute")
async def upload_blueprint(
    request: Request,
    file: UploadFile = File(...),
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a blueprint PDF for analysis (Phase 4)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Fail fast if the background worker broker is down — otherwise the PDF
    # would land in MinIO and never be processed.
    if not _worker_available or not _analyze_blueprint:
        raise HTTPException(status_code=503, detail="Blueprint worker is not deployed")
    if not await broker_available():
        raise HTTPException(
            status_code=503,
            detail="Blueprint analysis queue is unavailable; please retry shortly",
        )

    # 1. Generate unique filename
    unique_filename = f"blueprints/{uuid.uuid4()}.pdf"

    # 2. Upload to MinIO (enforce size limit)
    content = await file.read()
    if len(content) > _MAX_BLUEPRINT_BYTES:
        raise HTTPException(status_code=413, detail="Blueprint PDF exceeds 100 MB limit")
    success = storage_client.upload_file(
        settings.minio_bucket_blueprints,
        unique_filename,
        io.BytesIO(content),
        len(content),
        content_type="application/pdf"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # 3. Create Job in DB
    job = BlueprintJob(
        filename=unique_filename,
        original_filename=file.filename,
        storage_path=unique_filename,
        status="uploaded",
        project_id=project_id,
        created_by=current_user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 4. Trigger background analysis — broker checked above, so enqueue directly.
    _analyze_blueprint.delay(job.id, job.storage_path)

    logger.info("blueprint.uploaded", job_id=job.id, user_id=current_user.id)
    return BlueprintJobResponse(
        id=job.id,
        filename=job.original_filename,
        status=job.status,
        page_count=None,
        created_at=job.created_at,
    )


def _user_owns_blueprint(job: BlueprintJob, user: User) -> bool:
    """Blueprint jobs don't yet carry org_id, so scope by uploader or admin."""
    return (
        job.created_by == user.id
        or getattr(user, "is_admin", False)
    )


@router.get("/{job_id}/status", response_model=BlueprintJobResponse)
async def get_blueprint_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get blueprint processing status."""
    from sqlalchemy import select as _select

    result = await db.execute(_select(BlueprintJob).where(BlueprintJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job or not _user_owns_blueprint(job, current_user):
        raise HTTPException(status_code=404, detail="Blueprint job not found")

    return BlueprintJobResponse(
        id=job.id,
        filename=job.original_filename or job.filename,
        status=job.status,
        page_count=job.page_count,
        created_at=job.created_at,
    )


@router.get("/{job_id}/takeoff")
async def get_takeoff(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get takeoff results (Phase 4)."""
    from sqlalchemy import select as _select

    result = await db.execute(_select(BlueprintJob).where(BlueprintJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job or not _user_owns_blueprint(job, current_user):
        raise HTTPException(status_code=404, detail="Blueprint job not found")

    return await blueprint_service.generate_takeoff(db, job_id)
