from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.schemas.blueprints import BlueprintJobResponse, TakeoffResult
from app.services.blueprint_service import blueprint_service
from app.models.blueprints import BlueprintJob

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload", response_model=BlueprintJobResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload a blueprint PDF for analysis (Phase 4)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    job = BlueprintJob(
        filename=file.filename,
        original_filename=file.filename,
        status="uploaded",
        project_id=project_id,
    )
    db.add(job)
    await db.flush()

    return BlueprintJobResponse(
        id=job.id,
        filename=job.filename,
        status=job.status,
        page_count=None,
        created_at=job.created_at,
    )


@router.get("/{job_id}/status", response_model=BlueprintJobResponse)
async def get_blueprint_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get blueprint processing status."""
    from sqlalchemy import select
    result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Blueprint job not found")
    return BlueprintJobResponse(
        id=job.id,
        filename=job.filename,
        status=job.status,
        page_count=job.page_count,
        created_at=job.created_at,
    )


@router.get("/{job_id}/takeoff")
async def get_takeoff(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get takeoff results (Phase 4)."""
    result = await blueprint_service.generate_takeoff(str(job_id))
    return result
