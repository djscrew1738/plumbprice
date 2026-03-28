"""Celery task: Process uploaded documents for RAG ingestion (Phase 3)."""

from worker import app
import structlog

logger = structlog.get_logger()


@app.task(bind=True, max_retries=3)
def process_document(self, document_id: int, storage_path: str, doc_type: str):
    """
    Process an uploaded document for RAG ingestion.
    Phase 3: Extract text, chunk, embed, store in pgvector.
    """
    logger.info("Processing document", document_id=document_id, doc_type=doc_type)

    try:
        # TODO Phase 3: implement document processing pipeline
        # 1. Download from MinIO
        # 2. Extract text (PDF -> text)
        # 3. Chunk text (512 tokens, 50 overlap)
        # 4. Embed chunks (OpenAI text-embedding-3-small)
        # 5. Store in document_chunks table with vectors
        raise NotImplementedError("Document processing pipeline is not yet implemented.")
        logger.info("Document processing complete (Phase 3 stub)", document_id=document_id)
        return {"document_id": document_id, "status": "complete", "chunks": 0}

    except Exception as exc:
        logger.error("Document processing failed", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)
