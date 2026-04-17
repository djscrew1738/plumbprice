"""RAG Service — Phase 3 implementation using pgvector."""

import json
from typing import Optional, List
import structlog
import httpx
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.documents import UploadedDocument, DocumentChunk

logger = structlog.get_logger()


class RAGService:
    """Phase 3: RAG retrieval using pgvector embeddings via Ollama."""

    def __init__(self):
        self.endpoint = settings.hermes_endpoint_url.replace("/v1", "/api/embeddings")
        self.model = settings.llm_embedding_model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama's embeddings API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.endpoint,
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error("rag.embed_error", error=str(e), model=self.model)
            return []

    async def ingest_document(self, db: AsyncSession, doc_id: int, chunks: List[str]) -> dict:
        """Process and embed chunks for a document."""
        logger.info("rag.ingest_start", document_id=doc_id, chunks=len(chunks))
        
        try:
            for i, chunk_text in enumerate(chunks):
                embedding = await self.embed(chunk_text)
                if not embedding:
                    continue
                
                chunk = DocumentChunk(
                    document_id=doc_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=embedding,
                    token_count=len(chunk_text.split()) # Rough estimate
                )
                db.add(chunk)
            
            await db.commit()
            logger.info("rag.ingest_complete", document_id=doc_id)
            return {"status": "success", "chunks_processed": len(chunks)}
        except Exception as e:
            await db.rollback()
            logger.error("rag.ingest_failed", document_id=doc_id, error=str(e))
            return {"status": "error", "error": str(e)}

    _SQL_ALL = text("""
        SELECT dc.content, dc.metadata_json, ud.original_filename, ud.doc_type,
               (dc.embedding <=> CAST(:vector AS vector)) AS distance
        FROM document_chunks dc
        JOIN uploaded_documents ud ON dc.document_id = ud.id
        WHERE ud.status = 'complete'
        ORDER BY distance ASC
        LIMIT :limit
    """)

    _SQL_BY_SUPPLIER = text("""
        SELECT dc.content, dc.metadata_json, ud.original_filename, ud.doc_type,
               (dc.embedding <=> CAST(:vector AS vector)) AS distance
        FROM document_chunks dc
        JOIN uploaded_documents ud ON dc.document_id = ud.id
        WHERE ud.status = 'complete'
          AND ud.supplier_id = :supplier_id
        ORDER BY distance ASC
        LIMIT :limit
    """)

    _RELEVANCE_THRESHOLD = 0.30  # minimum similarity score (1 - cosine distance)

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        supplier_id: Optional[int] = None,
    ) -> List[dict]:
        """Retrieve relevant chunks using cosine similarity via pgvector."""
        query_embedding = await self.embed(query)
        if not query_embedding:
            return []

        # pgvector expects '[0.1,0.2,...]' — use json.dumps for reliable serialisation
        import json as _json
        vector_str = _json.dumps(query_embedding)

        if supplier_id is not None:
            sql = self._SQL_BY_SUPPLIER
            params: dict = {"vector": vector_str, "limit": top_k, "supplier_id": supplier_id}
        else:
            sql = self._SQL_ALL
            params = {"vector": vector_str, "limit": top_k}

        result = await db.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            score = 1.0 - float(row[4])  # convert cosine distance → similarity
            if score < self._RELEVANCE_THRESHOLD:
                continue
            results.append({
                "content": row[0],
                "metadata": row[1],
                "source": row[2],
                "doc_type": row[3],
                "score": round(score, 4),
            })

        return results


rag_service = RAGService()
