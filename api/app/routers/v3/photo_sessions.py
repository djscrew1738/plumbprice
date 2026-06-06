"""v4.1 Photo Sessions API — multi-photo estimate sessions (E4.1).

POST   /api/v3/photos/sessions           — create session
GET    /api/v3/photos/sessions/{id}      — get session status
POST   /api/v3/photos/sessions/{id}/add  — add a photo to the session
POST   /api/v3/photos/sessions/{id}/finalize — run detection + generate estimate
"""
from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import get_db
from app.core.auth import get_current_user
from app.core.storage import storage_client
from app.models.users import User
from app.models.photo_sessions import PhotoSession
from app.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/photos", tags=["photos"])


class CreateSessionRequest(BaseModel):
    county: Optional[str] = None
    address: Optional[str] = None
    job_notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SessionResponse(BaseModel):
    id: int
    status: str
    photo_count: int
    county: Optional[str]
    address: Optional[str]
    estimate_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new multi-photo estimate session."""
    # Auto-detect county from GPS if not provided
    county = body.county
    if not county and body.latitude is not None and body.longitude is not None:
        from app.services.geo_service import county_from_coordinates
        county = county_from_coordinates(body.latitude, body.longitude)

    session = PhotoSession(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        county=county,
        address=body.address,
        job_notes=body.job_notes,
        latitude=body.latitude,
        longitude=body.longitude,
        status="open",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("photo_session.created", session_id=session.id, user_id=current_user.id)
    return session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a photo session by ID."""
    session = await _get_session_or_404(db, session_id, current_user)
    return session


@router.post("/sessions/{session_id}/add")
async def add_photo(
    session_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a photo to an existing session. Triggers background detection."""
    session = await _get_session_or_404(db, session_id, current_user)

    if session.status not in ("open", "processing"):
        raise HTTPException(
            status_code=409,
            detail=f"Session is in '{session.status}' status — cannot add photos",
        )

    # Validate file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="File must be an image")

    # Upload to MinIO
    data = await file.read()
    storage_path = f"sessions/{session_id}/photo_{session.photo_count + 1}.jpg"
    storage_client.upload_file(
        settings.minio_bucket_photos,
        storage_path,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )

    # Increment photo count
    session.photo_count = (session.photo_count or 0) + 1
    await db.commit()

    logger.info(
        "photo_session.photo_added",
        session_id=session_id,
        photo_count=session.photo_count,
    )
    return {"status": "added", "photo_count": session.photo_count, "storage_path": storage_path}


@router.post("/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize a photo session — run multi-photo detection and generate an estimate.

    This is an async operation. Poll the session status until it becomes
    'complete' or 'failed'.
    """
    session = await _get_session_or_404(db, session_id, current_user)

    if session.status == "complete":
        return {"status": "already_complete", "estimate_id": session.estimate_id}

    if session.photo_count == 0:
        raise HTTPException(status_code=422, detail="No photos in session")

    # Mark as processing and enqueue worker task
    session.status = "processing"
    await db.commit()

    # Enqueue to Celery worker (photo session finalization)
    try:
        from worker.tasks.blueprint_analysis import analyze_photo_session
        analyze_photo_session.delay(session_id)
    except Exception:
        # Worker unavailable — still return processing status; can be retried
        logger.warning("photo_session.worker_unavailable", session_id=session_id)

    logger.info("photo_session.finalizing", session_id=session_id)
    return {"status": "processing", "session_id": session_id}


async def _get_session_or_404(
    db: AsyncSession, session_id: int, current_user: User
) -> PhotoSession:
    session = (
        await db.execute(
            select(PhotoSession).where(
                PhotoSession.id == session_id,
                PhotoSession.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Photo session not found")
    return session
