"""Agent memory service.

Long-term memory for the pricing agent. Backed by pgvector.

Three primary entry points:

  * ``store(...)`` — write an explicit memory (e.g. user preference set in UI,
    or extracted by an LLM pass).
  * ``retrieve(...)`` — semantic search the user's memories for context to
    inject into a chat turn.
  * ``extract_from_session(...)`` — background helper that asks the LLM to
    distill durable facts out of a recent chat exchange and stores any it
    finds.
"""
from __future__ import annotations

import json
from typing import Optional, Sequence

import httpx
import structlog
from sqlalchemy import select, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent_memory import AgentMemory
from app.models.sessions import ChatMessage
from app.services.rag_service import rag_service

logger = structlog.get_logger()


VALID_KINDS = {"preference", "profile", "customer", "job_history", "fact"}

# Soft cap per user. We prune lowest-importance / oldest beyond this.
MAX_MEMORIES_PER_USER = 500

# Cosine similarity floor for retrieval.
RELEVANCE_THRESHOLD = 0.25


class MemoryService:
    """Long-term memory persistence and retrieval."""

    async def store(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        content: str,
        kind: str = "fact",
        organization_id: Optional[int] = None,
        importance: float = 0.5,
        metadata: Optional[dict] = None,
        source_session_id: Optional[int] = None,
        skip_dedupe: bool = False,
    ) -> AgentMemory:
        """Embed and persist a memory.

        Returns the stored row. If a near-duplicate already exists for this
        user, returns the existing row (unless ``skip_dedupe`` is True).
        """
        if kind not in VALID_KINDS:
            kind = "fact"
        content = content.strip()
        if not content:
            raise ValueError("memory content is required")

        embedding = await rag_service.embed(content)
        if not embedding:
            logger.warning("memory.store_embed_failed", user_id=user_id)

        if embedding and not skip_dedupe:
            existing = await self._find_duplicate(db, user_id, embedding)
            if existing is not None:
                # Refresh importance/metadata on the existing row instead of
                # adding noise.
                existing.importance = max(existing.importance, importance)
                if metadata:
                    merged = {**(existing.metadata_json or {}), **metadata}
                    existing.metadata_json = merged
                await db.commit()
                await db.refresh(existing)
                return existing

        row = AgentMemory(
            user_id=user_id,
            organization_id=organization_id,
            kind=kind,
            content=content,
            embedding=embedding or None,
            metadata_json=metadata or None,
            importance=float(max(0.0, min(1.0, importance))),
            source_session_id=source_session_id,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        # Best-effort prune; don't fail the write if pruning fails.
        try:
            await self._prune_if_over_cap(db, user_id)
        except Exception as e:
            logger.warning("memory.prune_failed", user_id=user_id, error=str(e))

        return row

    async def retrieve(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        query: str,
        top_k: int = 5,
        kinds: Optional[Sequence[str]] = None,
    ) -> list[dict]:
        """Semantic search the user's memories.

        Returns a list of dicts with ``content``, ``kind``, ``score``,
        ``importance``, ``id``, ``metadata``. Falls back to most-recent rows
        if the embedding API is unavailable so the agent still has *some*
        context.
        """
        embedding = await rag_service.embed(query)
        if not embedding:
            # Fallback: most recently referenced / created memories.
            stmt = (
                select(AgentMemory)
                .where(AgentMemory.user_id == user_id)
                .order_by(
                    AgentMemory.last_referenced_at.desc().nullslast(),
                    AgentMemory.created_at.desc(),
                )
                .limit(top_k)
            )
            if kinds:
                stmt = stmt.where(AgentMemory.kind.in_(list(kinds)))
            rows = (await db.execute(stmt)).scalars().all()
            return [self._row_to_dict(r, score=None) for r in rows]

        vector_str = json.dumps(embedding)
        params: dict = {"vector": vector_str, "user_id": user_id, "limit": top_k}
        kind_clause = ""
        if kinds:
            kind_clause = " AND kind = ANY(:kinds) "
            params["kinds"] = list(kinds)

        sql = text(
            f"""
            SELECT id, content, kind, importance, metadata_json,
                   (embedding <=> CAST(:vector AS vector)) AS distance
            FROM agent_memories
            WHERE user_id = :user_id
              AND embedding IS NOT NULL
              {kind_clause}
            ORDER BY distance ASC
            LIMIT :limit
            """
        )
        result = await db.execute(sql, params)
        out: list[dict] = []
        ids_to_touch: list[int] = []
        for row in result.fetchall():
            score = 1.0 - float(row[5])
            if score < RELEVANCE_THRESHOLD:
                continue
            out.append({
                "id": row[0],
                "content": row[1],
                "kind": row[2],
                "importance": float(row[3]),
                "metadata": row[4],
                "score": round(score, 4),
            })
            ids_to_touch.append(row[0])

        if ids_to_touch:
            try:
                await db.execute(
                    update(AgentMemory)
                    .where(AgentMemory.id.in_(ids_to_touch))
                    .values(last_referenced_at=text("now()"))
                )
                await db.commit()
            except Exception as e:
                logger.warning("memory.touch_failed", error=str(e))
                await db.rollback()
        return out

    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        kinds: Optional[Sequence[str]] = None,
        limit: int = 200,
    ) -> list[AgentMemory]:
        stmt = select(AgentMemory).where(AgentMemory.user_id == user_id)
        if kinds:
            stmt = stmt.where(AgentMemory.kind.in_(list(kinds)))
        stmt = stmt.order_by(AgentMemory.created_at.desc()).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def delete(self, db: AsyncSession, *, memory_id: int, user_id: int) -> bool:
        result = await db.execute(
            delete(AgentMemory)
            .where(AgentMemory.id == memory_id, AgentMemory.user_id == user_id)
        )
        await db.commit()
        return (result.rowcount or 0) > 0

    async def update_content(
        self,
        db: AsyncSession,
        *,
        memory_id: int,
        user_id: int,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        kind: Optional[str] = None,
    ) -> Optional[AgentMemory]:
        row = (await db.execute(
            select(AgentMemory).where(
                AgentMemory.id == memory_id,
                AgentMemory.user_id == user_id,
            )
        )).scalars().first()
        if row is None:
            return None
        if content is not None:
            new_content = content.strip()
            if new_content and new_content != row.content:
                row.content = new_content
                emb = await rag_service.embed(new_content)
                if emb:
                    row.embedding = emb
        if importance is not None:
            row.importance = float(max(0.0, min(1.0, importance)))
        if kind is not None and kind in VALID_KINDS:
            row.kind = kind
        await db.commit()
        await db.refresh(row)
        return row

    async def extract_from_session(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        session_id: int,
        max_messages: int = 12,
    ) -> int:
        """Ask the LLM to distill durable memories from recent chat messages.

        Returns count of memories stored. Designed to be called from a
        background task after a chat turn so it doesn't slow user response.
        """
        msgs = (await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
        )).scalars().all()
        if not msgs:
            return 0

        # Reverse to chronological order for the LLM.
        msgs = list(reversed(msgs))
        transcript = "\n".join(
            f"{m.role.upper()}: {m.content[:800]}" for m in msgs
        )

        candidates = await self._llm_extract(transcript)
        stored = 0
        for cand in candidates:
            try:
                content = (cand.get("content") or "").strip()
                if not content or len(content) < 8:
                    continue
                kind = cand.get("kind") or "fact"
                importance = float(cand.get("importance", 0.5))
                await self.store(
                    db,
                    user_id=user_id,
                    content=content,
                    kind=kind,
                    importance=importance,
                    source_session_id=session_id,
                    metadata={"extracted": True},
                )
                stored += 1
            except Exception as e:
                logger.warning("memory.extract_store_failed", error=str(e))
        if stored:
            logger.info("memory.extracted", user_id=user_id, session_id=session_id, count=stored)
        return stored

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: AgentMemory, *, score: Optional[float]) -> dict:
        return {
            "id": row.id,
            "content": row.content,
            "kind": row.kind,
            "importance": row.importance,
            "metadata": row.metadata_json,
            "score": score,
        }

    async def _find_duplicate(
        self, db: AsyncSession, user_id: int, embedding: list[float],
        threshold: float = 0.92,
    ) -> Optional[AgentMemory]:
        sql = text(
            """
            SELECT id, (embedding <=> CAST(:vector AS vector)) AS distance
            FROM agent_memories
            WHERE user_id = :user_id AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT 1
            """
        )
        result = await db.execute(
            sql, {"vector": json.dumps(embedding), "user_id": user_id}
        )
        row = result.first()
        if row is None:
            return None
        score = 1.0 - float(row[1])
        if score < threshold:
            return None
        return await db.get(AgentMemory, int(row[0]))

    async def _prune_if_over_cap(self, db: AsyncSession, user_id: int) -> None:
        count = (await db.execute(
            text("SELECT count(*) FROM agent_memories WHERE user_id = :u"),
            {"u": user_id},
        )).scalar() or 0
        if count <= MAX_MEMORIES_PER_USER:
            return
        # Delete lowest-importance / oldest until we're under cap.
        excess = count - MAX_MEMORIES_PER_USER
        await db.execute(
            text(
                """
                DELETE FROM agent_memories
                WHERE id IN (
                    SELECT id FROM agent_memories
                    WHERE user_id = :u
                    ORDER BY importance ASC, created_at ASC
                    LIMIT :n
                )
                """
            ),
            {"u": user_id, "n": int(excess)},
        )
        await db.commit()

    async def _llm_extract(self, transcript: str) -> list[dict]:
        """Call the configured LLM and return a list of {content, kind, importance}."""
        endpoint = settings.hermes_endpoint_url
        model = getattr(settings, "llm_classify_model", None) or "hermes3:8b"
        system = (
            "You extract durable, generally-useful memories from a chat between "
            "a contractor and a pricing assistant. Return a JSON array. Each item "
            "must be {\"content\": str, \"kind\": one of [preference, profile, "
            "customer, job_history, fact], \"importance\": 0.0-1.0}. Only include "
            "facts that will be useful in future conversations. Skip greetings, "
            "transient questions, and things specific only to this single turn. "
            "Return at most 5 items. Return [] if nothing is durable."
        )
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{endpoint}/chat/completions",
                    json={
                        "model": model,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": f"Transcript:\n{transcript}\n\nReturn JSON: {{\"memories\": [...]}}."},
                        ],
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                raw = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
                parsed = json.loads(raw) if raw else {}
                memories = parsed.get("memories") if isinstance(parsed, dict) else parsed
                if isinstance(memories, list):
                    return [m for m in memories if isinstance(m, dict)]
        except Exception as e:
            logger.warning("memory.llm_extract_failed", error=str(e))
        return []


memory_service = MemoryService()
