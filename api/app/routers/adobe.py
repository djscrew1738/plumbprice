"""Adobe Document Cloud integration router.

Endpoints:
  GET  /auth/url          — generate Adobe OAuth URL (requires login)
  GET  /auth/callback     — OAuth callback (redirects to frontend)
  GET  /auth/status       — check if user's Adobe account is connected
  DELETE /auth/disconnect — remove stored Adobe tokens
  GET  /files             — list user's PDF files from Adobe DC
  POST /import            — download a DC file and queue as blueprint job
"""
import io
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.broker import broker_available
from app.core.storage import storage_client
from app.database import get_db
from app.models.adobe_oauth import AdobeOAuthToken
from app.models.blueprints import BlueprintJob
from app.models.users import User
from app.services import adobe_service

logger = structlog.get_logger()
router = APIRouter()

_MAX_IMPORT_BYTES = 100 * 1024 * 1024  # 100 MB


# ── Schemas ───────────────────────────────────────────────────────────────────

class AdobeAuthUrlResponse(BaseModel):
    auth_url: str


class AdobeConnectionStatus(BaseModel):
    connected: bool
    adobe_email: Optional[str] = None
    adobe_display_name: Optional[str] = None
    expires_at: Optional[datetime] = None


class AdobeFileItem(BaseModel):
    asset_id: str
    name: str
    modified: Optional[str] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    thumbnail_url: Optional[str] = None


class AdobeFilesResponse(BaseModel):
    files: list[AdobeFileItem]
    total: int
    offset: int
    limit: int


class AdobeImportRequest(BaseModel):
    asset_id: str
    filename: Optional[str] = None
    project_id: Optional[int] = None


class AdobeImportResponse(BaseModel):
    job_id: int
    filename: str
    status: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/auth/url", response_model=AdobeAuthUrlResponse)
async def get_adobe_auth_url(
    current_user: User = Depends(get_current_user),
):
    """Generate Adobe OAuth URL. Frontend should redirect user to this URL."""
    if not settings.adobe_client_id or not settings.adobe_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Adobe integration is not configured. Set ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET.",
        )
    state = f"{current_user.id}:{secrets.token_urlsafe(16)}"
    auth_url = adobe_service.get_auth_url(state=state)
    return AdobeAuthUrlResponse(auth_url=auth_url)


@router.get("/auth/callback")
async def adobe_auth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Adobe OAuth callback. Exchanges code for tokens, then redirects to frontend."""
    frontend_base = settings.frontend_url.rstrip("/")

    if error:
        logger.warning("adobe.oauth.error", error=error, desc=error_description)
        return RedirectResponse(
            url=f"{frontend_base}/blueprints?adobe_error={error}",
            status_code=302,
        )

    if not code:
        return RedirectResponse(
            url=f"{frontend_base}/blueprints?adobe_error=no_code",
            status_code=302,
        )

    # Extract user_id from state (format: "{user_id}:{nonce}")
    try:
        user_id = int((state or "").split(":")[0])
    except (ValueError, IndexError):
        return RedirectResponse(
            url=f"{frontend_base}/blueprints?adobe_error=invalid_state",
            status_code=302,
        )

    try:
        token_data = await adobe_service.exchange_code(code)
        access_token = token_data.get("access_token", "")

        # Fetch user profile to store email/name
        adobe_email = None
        adobe_display_name = None
        try:
            profile = await adobe_service.get_adobe_profile(access_token)
            adobe_email = profile.get("email") or profile.get("userId")
            adobe_display_name = profile.get("name") or profile.get("displayName")
        except Exception:
            pass  # Non-fatal — tokens still get stored

        await adobe_service.save_tokens(
            db=db,
            user_id=user_id,
            token_data=token_data,
            adobe_email=adobe_email,
            adobe_display_name=adobe_display_name,
        )
        logger.info("adobe.oauth.connected", user_id=user_id, email=adobe_email)
        return RedirectResponse(
            url=f"{frontend_base}/blueprints?adobe_connected=1",
            status_code=302,
        )
    except Exception as exc:
        logger.exception("adobe.oauth.callback_failed", error=str(exc))
        return RedirectResponse(
            url=f"{frontend_base}/blueprints?adobe_error=token_exchange_failed",
            status_code=302,
        )


@router.get("/auth/status", response_model=AdobeConnectionStatus)
async def get_adobe_connection_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether the user has a connected Adobe account."""
    result = await db.execute(
        select(AdobeOAuthToken).where(AdobeOAuthToken.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return AdobeConnectionStatus(connected=False)
    return AdobeConnectionStatus(
        connected=True,
        adobe_email=record.adobe_email,
        adobe_display_name=record.adobe_display_name,
        expires_at=record.expires_at,
    )


@router.delete("/auth/disconnect", status_code=204)
async def disconnect_adobe(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove stored Adobe OAuth tokens for the current user."""
    await db.execute(
        delete(AdobeOAuthToken).where(AdobeOAuthToken.user_id == current_user.id)
    )
    await db.commit()
    logger.info("adobe.disconnected", user_id=current_user.id)


@router.get("/files", response_model=AdobeFilesResponse)
async def list_adobe_files(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List PDF files from the user's Adobe Document Cloud storage."""
    try:
        access_token = await adobe_service.get_valid_access_token(db, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    try:
        raw = await adobe_service.list_files(
            access_token=access_token,
            limit=limit,
            offset=offset,
            search=search,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("adobe.files.list_failed", user_id=current_user.id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to list Adobe Document Cloud files")

    # Normalise the response — Adobe DC API returns items in different shapes
    items_raw = (
        raw.get("assets")
        or raw.get("items")
        or raw.get("files")
        or raw.get("data")
        or []
    )
    files: list[AdobeFileItem] = []
    for item in items_raw:
        # Only return PDF files
        mime = (
            item.get("mimeType")
            or item.get("mime_type")
            or item.get("type", "")
        )
        name = item.get("name") or item.get("filename") or item.get("title") or ""
        if not (mime == "application/pdf" or name.lower().endswith(".pdf")):
            continue
        files.append(AdobeFileItem(
            asset_id=(
                item.get("assetID")
                or item.get("asset_id")
                or item.get("id")
                or item.get("uid", "")
            ),
            name=name,
            modified=(
                item.get("modifyDate")
                or item.get("modified_date")
                or item.get("updatedAt")
                or item.get("modified")
            ),
            size_bytes=item.get("size") or item.get("sizeBytes"),
            mime_type=mime or "application/pdf",
            thumbnail_url=item.get("thumbnailUrl") or item.get("thumbnail"),
        ))

    total = raw.get("total") or raw.get("count") or len(files)
    return AdobeFilesResponse(
        files=files,
        total=int(total),
        offset=offset,
        limit=limit,
    )


@router.post("/import", response_model=AdobeImportResponse)
async def import_adobe_file(
    body: AdobeImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file from Adobe Document Cloud and queue it as a blueprint job."""
    # Check worker availability
    try:
        from worker.tasks.blueprint_analysis import analyze_blueprint as _analyze
        _worker_available = True
    except ImportError:
        _analyze = None
        _worker_available = False

    if not _worker_available or not _analyze:
        raise HTTPException(status_code=503, detail="Blueprint worker is not deployed")
    if not await broker_available():
        raise HTTPException(
            status_code=503,
            detail="Blueprint analysis queue is unavailable; please retry shortly",
        )

    try:
        access_token = await adobe_service.get_valid_access_token(db, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    try:
        pdf_bytes, detected_filename = await adobe_service.download_asset(
            access_token=access_token,
            asset_id=body.asset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("adobe.import.download_failed", asset_id=body.asset_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to download file from Adobe Document Cloud")

    if len(pdf_bytes) > _MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")

    filename = body.filename or detected_filename or "adobe_floorplan.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    # Store in MinIO and create blueprint job (same pipeline as manual upload)
    storage_path = f"blueprints/{uuid.uuid4()}.pdf"
    success = storage_client.upload_file(
        settings.minio_bucket_blueprints,
        storage_path,
        io.BytesIO(pdf_bytes),
        len(pdf_bytes),
        content_type="application/pdf",
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store imported file")

    from datetime import timedelta
    retention_until = datetime.now(timezone.utc) + timedelta(days=settings.data_retention_days)
    job = BlueprintJob(
        filename=storage_path,
        original_filename=filename,
        storage_path=storage_path,
        status="uploaded",
        project_id=body.project_id,
        created_by=current_user.id,
        retention_until=retention_until,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    _analyze.delay(job.id, job.storage_path)

    logger.info(
        "adobe.import.queued",
        job_id=job.id,
        asset_id=body.asset_id,
        user_id=current_user.id,
    )
    return AdobeImportResponse(
        job_id=job.id,
        filename=filename,
        status="uploaded",
    )
