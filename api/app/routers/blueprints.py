from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
import os
import io

from app.core.auth import get_current_user
from app.database import get_db
from app.schemas.blueprints import BlueprintJobResponse
from app.services.blueprint_service import blueprint_service
from app.models.blueprints import BlueprintJob
from app.models.users import User
from app.core.storage import storage_client
from app.config import settings

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
async def upload_blueprint(
    file: UploadFile = File(...),
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a blueprint PDF for analysis (Phase 4)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

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
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 4. Trigger background analysis (requires Celery worker)
    if _worker_available and _analyze_blueprint:
        _analyze_blueprint.delay(job.id, job.storage_path)
    else:
        logger.warning("blueprint.worker_unavailable", job_id=job.id)

    logger.info("blueprint.uploaded", job_id=job.id, user_id=current_user.id)
    return BlueprintJobResponse(
        id=job.id,
        filename=job.original_filename,
        status=job.status,
        page_count=None,
        created_at=job.created_at,
    )


@router.get("/{job_id}/status", response_model=BlueprintJobResponse)
async def get_blueprint_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get blueprint processing status."""
    status_data = await blueprint_service.get_job_status(db, job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Blueprint job not found")
        
    return BlueprintJobResponse(
        id=status_data["id"],
        filename="", # Not needed for status
        status=status_data["status"],
        page_count=status_data["page_count"],
        created_at=None, # Mocking for response model compatibility
    )


@router.get("/{job_id}/takeoff")
async def get_takeoff(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get takeoff results (Phase 4)."""
    result = await blueprint_service.generate_takeoff(db, job_id)
    return result
