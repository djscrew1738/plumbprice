from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
import os
import io
from typing import Optional

from app.core.auth import get_current_user
from app.core.broker import broker_available
from app.database import get_db
from app.schemas.blueprints import BlueprintJobResponse
from app.services.blueprint_service import blueprint_service
from app.services.blueprint_to_estimate import (
    EmptyTakeoffError,
    create_estimate_from_blueprint,
)
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
    from datetime import datetime, timezone, timedelta
    retention_until = datetime.now(timezone.utc) + timedelta(days=settings.data_retention_days)
    job = BlueprintJob(
        filename=unique_filename,
        original_filename=file.filename,
        storage_path=unique_filename,
        status="uploaded",
        project_id=project_id,
        created_by=current_user.id,
        retention_until=retention_until,
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
    if not job or not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
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
    if not job or not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Blueprint job not found")

    return await blueprint_service.generate_takeoff(db, job_id)


class BlueprintToEstimateRequest(BaseModel):
    project_id: Optional[int] = None


class BlueprintToEstimateResponse(BaseModel):
    estimate_id: int


@router.post("/{job_id}/to-estimate", response_model=BlueprintToEstimateResponse)
async def blueprint_to_estimate(
    job_id: int,
    body: Optional[BlueprintToEstimateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert a completed blueprint takeoff into a draft Estimate."""
    try:
        estimate = await create_estimate_from_blueprint(
            db=db,
            job_id=job_id,
            current_user=current_user,
            project_id=body.project_id if body else None,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Blueprint job not found")
    except EmptyTakeoffError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return BlueprintToEstimateResponse(estimate_id=estimate.id)


@router.delete("/{job_id}", status_code=204)
async def delete_blueprint(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    User-initiated deletion of an uploaded blueprint.

    Removes the source PDF from object storage immediately and marks the DB
    record as soft-deleted. The record itself is hard-deleted after the
    soft-delete grace window by `purge_expired_uploads`.
    """
    from sqlalchemy import select as _select
    from datetime import datetime, timezone

    result = await db.execute(_select(BlueprintJob).where(BlueprintJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job or not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Blueprint job not found")

    # Best-effort blob deletion now (DB row purged later).
    if job.storage_path:
        storage_client.delete_file(settings.minio_bucket_blueprints, job.storage_path)

    job.deleted_at = datetime.now(timezone.utc)
    job.status = "deleted"
    await db.commit()

    logger.info("blueprint.deleted", job_id=job.id, user_id=current_user.id)
    return None


# ── Detection feedback (Phase 2: review loop) ────────────────────────────────

class DetectionFeedbackRequest(BaseModel):
    verdict: str  # "correct" | "wrong" | "edited"
    corrected_fixture_type: Optional[str] = None
    corrected_count: Optional[int] = None
    note: Optional[str] = None


@router.post("/detections/{detection_id}/feedback", status_code=201)
async def submit_detection_feedback(
    detection_id: int,
    body: DetectionFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist user feedback on a vision detection.

    The submitted record drives the side-by-side review UI and is the data
    substrate for future classifier tuning. Submitting "correct" or "edited"
    also clears the detection's `needs_review` flag so the takeoff stops
    reporting it.
    """
    from sqlalchemy import select as _select
    from app.models.blueprints import BlueprintDetection, BlueprintDetectionFeedback, BlueprintPage

    if body.verdict not in {"correct", "wrong", "edited"}:
        raise HTTPException(status_code=400, detail="verdict must be one of: correct, wrong, edited")

    det_q = await db.execute(
        _select(BlueprintDetection, BlueprintJob)
        .join(BlueprintPage, BlueprintDetection.page_id == BlueprintPage.id)
        .join(BlueprintJob, BlueprintPage.job_id == BlueprintJob.id)
        .where(BlueprintDetection.id == detection_id)
    )
    row = det_q.first()
    if not row:
        raise HTTPException(status_code=404, detail="Detection not found")
    detection, job = row
    if not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Detection not found")

    feedback = BlueprintDetectionFeedback(
        detection_id=detection.id,
        verdict=body.verdict,
        corrected_fixture_type=(body.corrected_fixture_type or "").strip().lower() or None,
        corrected_count=body.corrected_count,
        note=(body.note or None),
        submitted_by=current_user.id,
    )
    db.add(feedback)

    # Apply correction in place (so downstream takeoff/estimate uses the corrected values)
    if body.verdict == "edited":
        if body.corrected_fixture_type:
            detection.fixture_type = body.corrected_fixture_type.strip().lower()
        if body.corrected_count is not None and body.corrected_count > 0:
            detection.count = body.corrected_count
        detection.needs_review = False
    elif body.verdict == "correct":
        detection.needs_review = False
    elif body.verdict == "wrong":
        # Mark as zero-count rather than deleting — preserves the audit trail.
        detection.count = 0
        detection.needs_review = False

    await db.commit()
    logger.info("blueprint.detection_feedback",
                detection_id=detection.id, verdict=body.verdict, user_id=current_user.id)

    return {
        "id": feedback.id,
        "detection_id": detection.id,
        "verdict": body.verdict,
        "applied": True,
    }


# ─── Phase 2.5 — Drawing-scale calibration ────────────────────────────────────


class CalibrationManualRequest(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    real_feet: float
    note: Optional[str] = None


@router.post("/pages/{page_id}/calibrate")
async def calibrate_page_scale(
    page_id: int,
    body: CalibrationManualRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Two-point manual scale calibration. Computes px/ft from the pixel
    distance between the clicked points and the user-entered real-world feet.
    Stores it on the page so takeoff/estimate can use it."""
    from sqlalchemy import select as _select
    from app.models.blueprints import BlueprintPage
    from app.services.scale_calibration import px_per_ft_from_points

    if body.real_feet <= 0:
        raise HTTPException(status_code=400, detail="real_feet must be > 0")

    row = (
        await db.execute(
            _select(BlueprintPage, BlueprintJob)
            .join(BlueprintJob, BlueprintPage.job_id == BlueprintJob.id)
            .where(BlueprintPage.id == page_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    page, job = row
    if not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Page not found")

    px_per_ft = px_per_ft_from_points(body.x1, body.y1, body.x2, body.y2, body.real_feet)
    if px_per_ft is None:
        raise HTTPException(status_code=400, detail="Invalid calibration points")

    page.px_per_ft = px_per_ft
    page.scale_calibrated = True
    page.scale_source = "manual"
    await db.commit()
    logger.info("blueprint.calibrate_manual",
                page_id=page.id, px_per_ft=px_per_ft, user_id=current_user.id)

    return {
        "page_id": page.id,
        "px_per_ft": px_per_ft,
        "scale_source": "manual",
        "scale_calibrated": True,
    }


@router.post("/pages/{page_id}/calibrate/auto")
async def calibrate_page_scale_from_text(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Try to derive px/ft from the page's existing `scale_text` + render DPI.
    Returns 422 if the text is missing/unparseable so the UI can fall back to
    the manual two-point flow."""
    from sqlalchemy import select as _select
    from app.models.blueprints import BlueprintPage
    from app.services.scale_calibration import px_per_ft_from_text

    row = (
        await db.execute(
            _select(BlueprintPage, BlueprintJob)
            .join(BlueprintJob, BlueprintPage.job_id == BlueprintJob.id)
            .where(BlueprintPage.id == page_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    page, job = row
    if not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Page not found")

    if not page.scale_text:
        raise HTTPException(status_code=422, detail="No scale text on this page")

    px_per_ft = px_per_ft_from_text(page.scale_text)
    if px_per_ft is None:
        raise HTTPException(status_code=422, detail=f"Could not parse scale: {page.scale_text!r}")

    page.px_per_ft = px_per_ft
    page.scale_calibrated = True
    page.scale_source = "text"
    await db.commit()
    logger.info("blueprint.calibrate_text",
                page_id=page.id, px_per_ft=px_per_ft, scale_text=page.scale_text)

    return {
        "page_id": page.id,
        "px_per_ft": px_per_ft,
        "scale_source": "text",
        "scale_text": page.scale_text,
        "scale_calibrated": True,
    }


@router.get("/pages/{page_id}/scale")
async def get_page_scale(
    page_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _select
    from app.models.blueprints import BlueprintPage

    row = (
        await db.execute(
            _select(BlueprintPage, BlueprintJob)
            .join(BlueprintJob, BlueprintPage.job_id == BlueprintJob.id)
            .where(BlueprintPage.id == page_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    page, job = row
    if not _user_owns_blueprint(job, current_user) or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {
        "page_id": page.id,
        "scale_text": page.scale_text,
        "px_per_ft": page.px_per_ft,
        "scale_source": page.scale_source,
        "scale_calibrated": page.scale_calibrated,
    }
