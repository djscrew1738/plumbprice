"""
Blueprints API v3 — Enhanced blueprint analysis with rooms, pipe runs, and bounding boxes.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog
import uuid
import io

from app.core.auth import get_current_user
from app.core.broker import broker_available
from app.database import get_db
from app.models.blueprints import BlueprintJob
from app.models.users import User
from app.core.storage import storage_client
from app.services.blueprint_to_estimate_v3 import (
    _load_job_v3,
    _user_owns_job,
    create_estimate_from_blueprint_v3,
    EmptyTakeoffError,
)
from app.config import settings
from app.core.limiter import limiter  # noqa: F401 — imported for rate-limit registration
from app.services.vision_v3 import vision_service_v3
from app.core.cache import cache_get, cache_set

logger = structlog.get_logger()
router = APIRouter()

_MAX_BLUEPRINT_BYTES = 100 * 1024 * 1024
_MAX_IMAGE_BYTES = 20 * 1024 * 1024


try:
    from worker.tasks.blueprint_analysis import analyze_blueprint as _analyze_blueprint
    _worker_available = True
except ImportError:
    _analyze_blueprint = None
    _worker_available = False


# ── Upload (same as v1, but triggers v3 analysis) ────────────────────────────

@router.post("/upload")
async def upload_blueprint_v3(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a blueprint PDF for v3 analysis (rooms + pipe runs + fixtures with bboxes)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if not _worker_available or not _analyze_blueprint:
        raise HTTPException(status_code=503, detail="Blueprint worker is not deployed")
    if not await broker_available():
        raise HTTPException(status_code=503, detail="Blueprint analysis queue is unavailable")

    content = await file.read()
    if len(content) > _MAX_BLUEPRINT_BYTES:
        raise HTTPException(status_code=413, detail="Blueprint PDF exceeds 100 MB limit")

    unique_filename = f"blueprints/{uuid.uuid4()}.pdf"
    success = storage_client.upload_file(
        settings.minio_bucket_blueprints,
        unique_filename,
        io.BytesIO(content),
        len(content),
        content_type="application/pdf",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

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

    # Enqueue Celery task for v3 analysis
    task = _analyze_blueprint.delay(job.id)
    job.celery_task_id = task.id
    job.status = "queued"
    await db.commit()

    logger.info(
        "blueprint.uploaded_v3",
        job_id=job.id,
        user_id=current_user.id,
        filename=file.filename,
        size_bytes=len(content),
    )
    return {
        "job_id": job.id,
        "status": job.status,
        "celery_task_id": task.id,
        "original_filename": file.filename,
    }


# ── Quick image analyze (for chat attachment) ────────────────────────────────

@router.post("/quick-analyze")
async def quick_analyze_image_v3(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Quick image analysis for chat attachment. Returns fixture/room/pipe summary."""
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = (file.filename or "").lower()
    if not any(ext.endswith(e) for e in allowed_ext):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 20 MB limit")

    cache_key = f"blueprint:quick:{uuid.uuid5(uuid.NAMESPACE_OID, content[:4096])}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        fixtures = await vision_service_v3.detect_fixtures_v2(content)
        rooms = await vision_service_v3.detect_rooms(content)
        pipes = await vision_service_v3.detect_pipe_runs(content)
    except Exception as exc:
        logger.warning("blueprint.quick_analyze_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Vision analysis failed")

    summary_parts = []
    if rooms.get("rooms"):
        room_types = {}
        for r in rooms["rooms"]:
            rt = r.get("room_type", "room")
            room_types[rt] = room_types.get(rt, 0) + 1
        room_str = ", ".join(f"{c} {t}" for t, c in room_types.items())
        summary_parts.append(f"Detected rooms: {room_str}")
    if fixtures.get("fixtures"):
        fixture_types = {}
        for f in fixtures["fixtures"]:
            ft = f.get("fixture_type", "fixture")
            fixture_types[ft] = fixture_types.get(ft, 0) + 1
        fix_str = ", ".join(f"{c} {t}" for t, c in fixture_types.items())
        summary_parts.append(f"Detected fixtures: {fix_str}")
    if pipes.get("pipe_runs"):
        total_ft = sum(p.get("length_ft", 0) for p in pipes["pipe_runs"])
        pipe_types = {}
        for p in pipes["pipe_runs"]:
            pt = p.get("pipe_type", "pipe")
            pipe_types[pt] = pipe_types.get(pt, 0) + 1
        pipe_str = ", ".join(f"{c} {t} run{'s' if c > 1 else ''}" for t, c in pipe_types.items())
        summary_parts.append(f"Estimated pipe: {total_ft:.0f} ft total ({pipe_str})")

    result = {
        "summary": "; ".join(summary_parts) if summary_parts else "No plumbing elements detected.",
        "fixtures": fixtures.get("fixtures", []),
        "rooms": rooms.get("rooms", []),
        "pipe_runs": pipes.get("pipe_runs", []),
    }
    await cache_set(cache_key, result, ttl=3600)
    return result


# ── Status & results ─────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_blueprint_job_v3(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get blueprint job status with v3 data (rooms, pipe runs, detections)."""
    job = await _load_job_v3(db, job_id)
    if not job or not _user_owns_job(job, current_user):
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "status": job.status,
        "original_filename": job.original_filename,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "pages": [
            {
                "id": p.id,
                "page_number": p.page_number,
                "detections": [
                    {
                        "id": d.id,
                        "fixture_type": d.fixture_type,
                        "confidence": d.confidence,
                        "bounding_box": d.bounding_box,
                    }
                    for d in (p.detections or [])
                ],
            }
            for p in (job.pages or [])
        ],
        "rooms": [
            {
                "id": r.id,
                "room_type": r.room_type,
                "room_name": r.room_name,
                "area_sqft": r.area_sqft,
                "fixture_count": r.fixture_count,
                "confidence": r.confidence,
                "bounding_box": r.bounding_box,
            }
            for r in (job.rooms or [])
        ],
        "pipe_runs": [
            {
                "id": p.id,
                "pipe_type": p.pipe_type,
                "length_ft": p.length_ft,
                "confidence": p.confidence,
            }
            for p in (job.pipe_runs or [])
        ],
        "total_room_count": len(job.rooms or []),
        "total_pipe_run_ft": round(sum(p.length_ft for p in (job.pipe_runs or [])), 2),
    }


# ── List jobs ────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_blueprint_jobs_v3(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BlueprintJob).where(BlueprintJob.created_by == current_user.id)
    if project_id is not None:
        stmt = stmt.where(BlueprintJob.project_id == project_id)
    stmt = stmt.order_by(BlueprintJob.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": j.id,
            "status": j.status,
            "original_filename": j.original_filename,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in rows
    ]


# ── Convert to estimate ──────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/to-estimate")
async def blueprint_to_estimate_v3(
    job_id: int,
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert a v3 blueprint job (fixtures + rooms + pipe runs) to a draft estimate."""
    try:
        estimate = await create_estimate_from_blueprint_v3(
            db, job_id, current_user, project_id=project_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Blueprint job not found")
    except EmptyTakeoffError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "estimate_id": estimate.id,
        "status": estimate.status,
        "title": estimate.title,
        "grand_total": estimate.grand_total,
        "blueprint_room_count": estimate.blueprint_room_count,
        "blueprint_pipe_run_ft": estimate.blueprint_pipe_run_ft,
    }
