from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid
import os
from typing import Optional

from app.database import get_db
from app.core.storage import storage_client
from app.models.documents import UploadedDocument
from app.config import settings
from worker.tasks.document_processing import process_document

logger = structlog.get_logger()
router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...), # price_sheet, spec, code, manual
    supplier_id: Optional[int] = Form(None),
    organization_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document for RAG processing (Phase 3)."""
    # 1. Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # 2. Upload to MinIO
    content = await file.read()
    success = storage_client.upload_file(
        settings.minio_bucket_documents,
        unique_filename,
        io.BytesIO(content),
        len(content),
        content_type=file.content_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # 3. Save to DB
    doc = UploadedDocument(
        filename=unique_filename,
        original_filename=file.filename,
        doc_type=doc_type,
        file_size=len(content),
        mime_type=file.content_type,
        storage_path=unique_filename,
        status="pending",
        supplier_id=supplier_id,
        organization_id=organization_id
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 4. Trigger background processing
    process_document.delay(doc.id, doc.storage_path, doc.doc_type)

    return {
        "id": doc.id,
        "filename": doc.original_filename,
        "status": doc.status,
        "created_at": doc.created_at
    }

import io # Needed for io.BytesIO
