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

    async def retrieve(self, db: AsyncSession, query: str, top_k: int = 5, supplier_id: Optional[int] = None) -> List[dict]:
        """
        Retrieve relevant chunks using cosine similarity via pgvector.
        """
        query_embedding = await self.embed(query)
        if not query_embedding:
            return []

        # Convert list to pgvector compatible string format: '[0.1, 0.2, ...]'
        vector_str = str(query_embedding)

        # Standard cosine similarity query for pgvector: <=> is cosine distance
        # We want (1 - distance) for similarity if needed, but distance is fine for ordering.
        sql = text(f"""
            SELECT dc.content, dc.metadata_json, ud.original_filename, ud.doc_type,
                   (dc.embedding <=> :vector) as distance
            FROM document_chunks dc
            JOIN uploaded_documents ud ON dc.document_id = ud.id
            WHERE ud.status = 'complete'
            {"AND ud.supplier_id = :supplier_id" if supplier_id else ""}
            ORDER BY distance ASC
            LIMIT :limit
        """)

        params = {"vector": vector_str, "limit": top_k}
        if supplier_id:
            params["supplier_id"] = supplier_id

        result = await db.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            results.append({
                "content": row[0],
                "metadata": row[1],
                "source": row[2],
                "doc_type": row[3],
                "score": 1 - row[4] # Convert distance to similarity score
            })

        return results


rag_service = RAGService()
