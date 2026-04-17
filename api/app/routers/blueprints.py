from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
import os
import io

from app.database import get_db
from app.schemas.blueprints import BlueprintJobResponse
from app.services.blueprint_service import blueprint_service
from app.models.blueprints import BlueprintJob
from app.core.storage import storage_client
from app.config import settings
from worker.tasks.blueprint_analysis import analyze_blueprint

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

    # 1. Generate unique filename
    unique_filename = f"blueprints/{uuid.uuid4()}.pdf"
    
    # 2. Upload to MinIO
    content = await file.read()
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

    # 4. Trigger background analysis
    analyze_blueprint.delay(job.id, job.storage_path)

    return BlueprintJobResponse(
        id=job.id,
        filename=job.original_filename,
        status=job.status,
        page_count=None,
        created_at=job.created_at,
    )


@router.get("/{job_id}/status", response_model=BlueprintJobResponse)
async def get_blueprint_status(job_id: int, db: AsyncSession = Depends(get_db)):
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
async def get_takeoff(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get takeoff results (Phase 4)."""
    result = await blueprint_service.generate_takeoff(db, job_id)
    return result
