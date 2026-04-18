"""Celery task: Process uploaded documents for RAG ingestion (Phase 3)."""

import asyncio
import io
import random
import fitz  # PyMuPDF
import structlog
from worker.worker import app
from app.core.storage import storage_client
from app.services.rag_service import rag_service
from app.database import AsyncSessionLocal
from app.models.documents import UploadedDocument
from app.config import settings
from sqlalchemy import select

logger = structlog.get_logger()


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """Simple character-based chunking with overlap."""
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
        
    return chunks


async def _async_process_document(document_id: int, storage_path: str, doc_type: str):
    """Internal async implementation of document processing."""
    async with AsyncSessionLocal() as db:
        try:
            # 1. Update status to processing
            result = await db.execute(select(UploadedDocument).where(UploadedDocument.id == document_id))
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error("rag.doc_not_found", document_id=document_id)
                return
            
            doc.status = "processing"
            await db.commit()

            # 2. Download from MinIO
            bucket = settings.minio_bucket_documents
            file_data = storage_client.download_file(bucket, storage_path)
            if not file_data:
                raise ValueError(f"Failed to download file from {bucket}/{storage_path}")

            # 3. Extract text (PDF -> text)
            text_content = ""
            if storage_path.lower().endswith(".pdf"):
                doc_pdf = fitz.open(stream=file_data, filetype="pdf")
                for page in doc_pdf:
                    text_content += page.get_text()
                doc_pdf.close()
            else:
                # Assume plain text for other types for now
                text_content = file_data.getvalue().decode("utf-8", errors="ignore")

            if not text_content.strip():
                raise ValueError("No text extracted from document")

            # 4. Chunk text
            chunks = chunk_text(text_content)
            
            # 5. Ingest into RAG service (embeds and stores chunks)
            ingest_result = await rag_service.ingest_document(db, document_id, chunks)
            
            if ingest_result["status"] == "success":
                doc.status = "complete"
                logger.info("rag.process_complete", document_id=document_id, chunks=len(chunks))
            else:
                doc.status = "error"
                doc.processing_error = ingest_result.get("error", "Unknown ingestion error")
            
            await db.commit()
            return {"document_id": document_id, "status": doc.status, "chunks": len(chunks)}

        except Exception as e:
            await db.rollback()
            # Try to update status to error if possible
            try:
                result = await db.execute(select(UploadedDocument).where(UploadedDocument.id == document_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "error"
                    doc.processing_error = str(e)
                    await db.commit()
            except Exception as rollback_exc:
                logger.warning("Failed to update document status to error", document_id=document_id, error=str(rollback_exc))
            raise e


@app.task(bind=True, max_retries=3)
def process_document(self, document_id: int, storage_path: str, doc_type: str):
    """
    Process an uploaded document for RAG ingestion.
    Phase 3: Extract text, chunk, embed, store in pgvector.
    """
    logger.info("Starting document processing", document_id=document_id, doc_type=doc_type)

    try:
        result = asyncio.run(_async_process_document(document_id, storage_path, doc_type))
        return result

    except Exception as exc:
        logger.error("Document processing failed", document_id=document_id, error=str(exc), exc_info=True)
        backoff = min(60 * (2 ** self.request.retries) + random.uniform(0, 30), 600)
        try:
            raise self.retry(exc=exc, countdown=backoff)
        except self.MaxRetriesExceededError:
            try:
                asyncio.run(_notify_document_failure(document_id, str(exc)))
            except Exception as notify_exc:  # pragma: no cover
                logger.warning("rag.notify_failed", document_id=document_id, error=str(notify_exc))
            raise


async def _notify_document_failure(document_id: int, error: str) -> None:
    """Best-effort notification to the document uploader on terminal failure."""
    from app.services.notifications_service import notify as _notify

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UploadedDocument).where(UploadedDocument.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc or doc.uploaded_by is None:
            return
        await _notify(
            db=db,
            user_id=doc.uploaded_by,
            kind="job_failed",
            title="Document processing failed",
            body=(error or "Unknown error")[:500],
            link=f"/documents/{document_id}",
        )
        await db.commit()
