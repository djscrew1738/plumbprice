import io
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.auth import get_current_user
from app.core.broker import broker_available
from app.database import get_db
from app.models.documents import UploadedDocument
from app.models.users import User
from app.core.storage import storage_client
from app.config import settings
from app.core.limiter import limiter

try:
    from worker.tasks.document_processing import process_document as _process_document
    _worker_available = True
except ImportError:
    _process_document = None
    _worker_available = False

logger = structlog.get_logger()
router = APIRouter()

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(...),  # price_sheet, spec, code, manual
    supplier_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for RAG processing."""
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    if not _worker_available or not _process_document:
        raise HTTPException(status_code=503, detail="Document processing worker is not deployed")
    if not await broker_available():
        raise HTTPException(
            status_code=503,
            detail="Document processing queue is unavailable; please retry shortly",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    ext = os.path.splitext(file.filename or "file")[1]
    unique_filename = f"{uuid.uuid4()}{ext}"

    success = storage_client.upload_file(
        settings.minio_bucket_documents,
        unique_filename,
        io.BytesIO(content),
        len(content),
        content_type=file.content_type,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    doc = UploadedDocument(
        filename=unique_filename,
        original_filename=file.filename,
        doc_type=doc_type,
        file_size=len(content),
        mime_type=file.content_type,
        storage_path=unique_filename,
        status="pending",
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Broker was checked before upload — enqueue directly.
    _process_document.delay(doc.id, doc.storage_path, doc.doc_type)

    logger.info("document.uploaded", doc_id=doc.id, user_id=current_user.id, doc_type=doc_type)
    return {
        "id": doc.id,
        "filename": doc.original_filename,
        "status": doc.status,
        "created_at": doc.created_at,
    }


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a document from storage. Organisation-scoped."""
    result = await db.execute(
        select(UploadedDocument).where(
            UploadedDocument.id == doc_id,
            UploadedDocument.organization_id == current_user.organization_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.storage_path:
        raise HTTPException(status_code=404, detail="File not available")

    data = storage_client.download_file(settings.minio_bucket_documents, doc.storage_path)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found in storage")

    filename = doc.original_filename or doc.filename
    safe_name = filename.replace('"', "'")
    return StreamingResponse(
        data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/")
async def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents belonging to the current user's organization."""
    q = (
        select(UploadedDocument)
        .where(UploadedDocument.organization_id == current_user.organization_id)
        .order_by(UploadedDocument.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.original_filename,
            "doc_type": d.doc_type,
            "status": d.status,
            "file_size": d.file_size,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a document (organization-scoped)."""
    result = await db.execute(
        select(UploadedDocument).where(
            UploadedDocument.id == doc_id,
            UploadedDocument.organization_id == current_user.organization_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_client.delete_file(settings.minio_bucket_documents, doc.storage_path)
    await db.delete(doc)
    await db.commit()
    logger.info("document.deleted", doc_id=doc_id, user_id=current_user.id)
    return {"deleted": doc_id}
