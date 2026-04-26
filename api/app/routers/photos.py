"""
Phase 3 + 3.5 — On-site photo quick-quote + persistence.

Workflow:
    1. Field tech POSTs a photo (multipart) to `/api/v1/photos/quick-quote`
    2. We send the bytes through `vision_service.describe_photo` (Ollama vision)
    3. We map vision items → labor templates → priced draft via `photo_quote.build_quick_quote`
    4. The response is a JSON draft the UI can display under 30 seconds.

Phase 3.5: when the request includes `persist=true` (and optionally a
`project_id`), we additionally upload the photo to MinIO and create a
`photos` row so the project gets a permanent record. The persisted photo
can later be turned into a draft estimate via `/api/v1/photos/{id}/attach`.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.limiter import limiter
from app.core.storage import storage_client
from app.database import get_db
from app.models.estimates import Estimate, EstimateLineItem
from app.models.photos import Photo
from app.models.projects import Project
from app.models.users import User
from app.services.photo_quote import build_quick_quote, load_db_overrides
from app.services.vision_service import vision_service

logger = structlog.get_logger()
router = APIRouter()

# Hard cap: a phone photo is ~5–10MB; reject anything obviously huge.
_MAX_BYTES = 12 * 1024 * 1024


async def _user_owns_project(db: AsyncSession, project_id: int, user: User) -> Optional[Project]:
    q = await db.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))
    project = q.scalar_one_or_none()
    if project is None:
        return None
    if user.organization_id and project.organization_id == user.organization_id:
        return project
    if project.created_by == user.id:
        return project
    return None


@router.post("/quick-quote")
@limiter.limit("20/minute")
async def quick_quote(
    request: Request,
    file: UploadFile = File(...),
    note: Optional[str] = Form(None),
    county: str = Form("Dallas"),
    city: Optional[str] = Form(None),
    urgency: str = Form("standard"),
    access: str = Form("first_floor"),
    persist: bool = Form(False),
    project_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Snap → priced draft.

    Form fields:
        file:       image/jpeg or image/png (required)
        note:       optional context (e.g. "second-floor master bath, leaking under sink")
        county:     defaults to Dallas (drives tax + permit math)
        city:       optional city premium driver
        urgency:    standard | same_day | after_hours | emergency
        access:     first_floor | second_floor | crawlspace | attic | basement
        persist:    when true, upload the photo to MinIO + create a `photos` row
        project_id: optional project to attach this photo to (requires persist=true)
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload must be an image (jpeg/png)")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(image_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Photo too large (max 12 MB)")

    # If a project_id is given, verify ownership before doing the expensive vision call.
    project: Optional[Project] = None
    if project_id is not None:
        project = await _user_owns_project(db, project_id, current_user)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

    logger.info("photo.quick_quote.start",
                user_id=current_user.id, bytes=len(image_bytes),
                county=county, urgency=urgency, access=access,
                persist=persist, project_id=project_id)

    vision = await vision_service.describe_photo(image_bytes, hint=note)
    if vision.get("status") == "error":
        return {
            "status": "vision_error",
            "error": vision.get("error"),
            "scene": "unknown",
            "summary": "",
            "lines": [],
            "totals": {"low": 0.0, "high": 0.0, "expected": 0.0},
            "unmapped": [],
        }

    overrides = await load_db_overrides(db)
    quote = build_quick_quote(
        vision,
        county=county,
        city=city,
        urgency=urgency,
        access=access,
        overrides=overrides,
    )
    quote["status"] = "ok"
    quote["raw_vision"] = vision
    quote["user_note"] = note

    if persist:
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() if (file.filename and "." in (file.filename or "")) else "jpg"
        if ext not in {"jpg", "jpeg", "png", "webp", "heic"}:
            ext = "jpg"
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        object_name = f"{date_prefix}/u{current_user.id}/{uuid.uuid4().hex}.{ext}"
        bucket = settings.minio_bucket_photos
        try:
            storage_client.ensure_buckets()
            ok = storage_client.upload_file(
                bucket, object_name, io.BytesIO(image_bytes), len(image_bytes),
                content_type=file.content_type or "image/jpeg",
            )
            if not ok:
                raise RuntimeError("upload returned False")
        except Exception as e:
            logger.error("photo.persist_failed", error=str(e))
            quote["persisted"] = False
            quote["persist_error"] = str(e)
            return quote

        photo = Photo(
            project_id=project.id if project else None,
            estimate_id=None,
            uploaded_by=current_user.id,
            organization_id=current_user.organization_id,
            storage_bucket=bucket,
            storage_path=object_name,
            content_type=file.content_type or "image/jpeg",
            size_bytes=len(image_bytes),
            note=note,
            county=county,
            urgency=urgency,
            access=access,
            vision=vision,
            quote={
                "lines": quote.get("lines", []),
                "totals": quote.get("totals", {}),
                "unmapped": quote.get("unmapped", []),
                "scene": vision.get("scene"),
            },
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        quote["persisted"] = True
        quote["photo_id"] = photo.id

    logger.info("photo.quick_quote.done",
                user_id=current_user.id,
                lines=len(quote["lines"]),
                unmapped=len(quote["unmapped"]),
                expected=quote["totals"]["expected"],
                photo_id=quote.get("photo_id"))
    return quote


@router.get("")
async def list_photos(
    project_id: Optional[int] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List photos visible to the current user, optionally filtered by project."""
    q = select(Photo).order_by(Photo.created_at.desc()).limit(min(limit, 200))
    if project_id is not None:
        q = q.where(Photo.project_id == project_id)
    if current_user.organization_id:
        q = q.where(Photo.organization_id == current_user.organization_id)
    else:
        q = q.where(Photo.uploaded_by == current_user.id)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": p.id,
            "project_id": p.project_id,
            "estimate_id": p.estimate_id,
            "note": p.note,
            "county": p.county,
            "urgency": p.urgency,
            "access": p.access,
            "size_bytes": p.size_bytes,
            "content_type": p.content_type,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "totals": (p.quote or {}).get("totals"),
            "scene": (p.quote or {}).get("scene") or (p.vision or {}).get("scene"),
        }
        for p in rows
    ]


async def _load_photo(db: AsyncSession, photo_id: int, user: User) -> Photo:
    p = (await db.execute(select(Photo).where(Photo.id == photo_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Photo not found")
    visible = (
        (user.organization_id and p.organization_id == user.organization_id)
        or p.uploaded_by == user.id
    )
    if not visible:
        raise HTTPException(status_code=404, detail="Photo not found")
    return p


@router.get("/{photo_id}")
async def get_photo_meta(
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _load_photo(db, photo_id, current_user)
    return {
        "id": p.id,
        "project_id": p.project_id,
        "estimate_id": p.estimate_id,
        "note": p.note,
        "county": p.county,
        "urgency": p.urgency,
        "access": p.access,
        "size_bytes": p.size_bytes,
        "content_type": p.content_type,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "vision": p.vision,
        "quote": p.quote,
    }


@router.get("/{photo_id}/file")
async def get_photo_file(
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p = await _load_photo(db, photo_id, current_user)
    data = storage_client.download_file(p.storage_bucket, p.storage_path)
    if data is None:
        raise HTTPException(status_code=404, detail="Photo file missing in storage")
    return StreamingResponse(data, media_type=p.content_type or "image/jpeg")


@router.post("/{photo_id}/attach")
async def attach_photo_to_project(
    photo_id: int,
    project_id: int = Form(...),
    create_estimate: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Move/attach a persisted photo to a project. Optionally creates a draft
    Estimate seeded from the photo's stored quote (one EstimateLineItem per
    quote line, totals copied through).
    """
    p = await _load_photo(db, photo_id, current_user)
    project = await _user_owns_project(db, project_id, current_user)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    p.project_id = project.id
    estimate_id: Optional[int] = None

    if create_estimate and p.quote:
        lines = (p.quote or {}).get("lines") or []
        totals = (p.quote or {}).get("totals") or {}
        labor_total = float(sum(float(li.get("labor_total", 0) or 0) for li in lines))
        materials_total = float(sum(float(li.get("materials_total", 0) or 0) for li in lines))
        grand_total = float(totals.get("expected") or sum(float(li.get("grand_total", 0) or 0) for li in lines))

        est = Estimate(
            project_id=project.id,
            title=(p.note or "Photo quick-quote")[:255],
            job_type="service",
            status="draft",
            grand_total=grand_total,
            labor_total=labor_total,
            materials_total=materials_total,
            tax_total=0.0,
            confidence_label="MEDIUM",
            county=p.county or project.county or "Dallas",
            chat_context=f"Photo quick-quote (photo_id={p.id})",
            created_by=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(est)
        await db.flush()
        estimate_id = est.id
        for li in lines:
            db.add(EstimateLineItem(
                estimate_id=est.id,
                line_type=li.get("line_type") or "labor",
                description=li.get("description") or li.get("task_code") or "Photo line",
                quantity=float(li.get("quantity") or 1),
                unit=li.get("unit") or "ea",
                unit_cost=float(li.get("unit_cost") or 0),
                total_cost=float(li.get("total_cost") or li.get("grand_total") or 0),
            ))
        p.estimate_id = est.id

    await db.commit()
    return {
        "photo_id": p.id,
        "project_id": project.id,
        "estimate_id": estimate_id,
        "attached": True,
    }

