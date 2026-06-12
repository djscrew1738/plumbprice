"""Task Code Embeddings — semantic retrieval for pricing chat classification.

Generates and queries pgvector embeddings for all labor template task codes
so the LLM classifier sees the most relevant task codes in-context instead
of a static shortlist.
"""
from __future__ import annotations

import json

import httpx
import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.labor_engine import LABOR_TEMPLATES, LaborTemplateData

logger = structlog.get_logger()

# Module-level singleton — reuses connection pool
_http_client: httpx.AsyncClient | None = None

# Static list of common task codes that are always included in the classify
# prompt (high-frequency items that must never be hidden from the LLM).
_COMMON_TASK_CODES: set[str] = {
    "ANGLE_STOP_REPLACE",
    "ANGLE_STOP_REPLACE_PAIR",
    "BACKFLOW_PREVENTER_INSTALL",
    "BATHTUB_DRAIN_REPAIR",
    "CAMERA_INSPECTION",
    "CLEAN_OUT_INSTALL",
    "DISHWASHER_HOOKUP",
    "DRAIN_CLEAN_BATHTUB",
    "DRAIN_CLEAN_KITCHEN",
    "DRAIN_CLEAN_SHOWER",
    "DRAIN_CLEAN_STANDARD",
    "EXPANSION_TANK_INSTALL",
    "FAUCET_CARTRIDGE_REPAIR",
    "GARBAGE_DISPOSAL_INSTALL",
    "GARBAGE_DISPOSAL_REPAIR",
    "GAS_LINE_NEW_RUN",
    "GAS_LINE_REPAIR_MINOR",
    "GAS_SHUTOFF_REPLACE",
    "HOSE_BIB_ADD_NEW",
    "HOSE_BIB_REPLACE",
    "ICE_MAKER_LINE_INSTALL",
    "IRRIGATION_BACKFLOW_REPAIR",
    "KITCHEN_FAUCET_REPLACE",
    "LAV_FAUCET_REPLACE",
    "LAV_SINK_REPLACE",
    "LEAK_DETECTION",
    "MAIN_LINE_CLEAN",
    "MAIN_SHUTOFF_REPLACE",
    "MIXING_VALVE_REPLACE",
    "PRV_INSTALL_NEW",
    "PRV_REPLACE",
    "PTRAP_REPLACE",
    "RECIRCULATION_PUMP_INSTALL",
    "SEWER_SPOT_REPAIR",
    "SHOWER_HEAD_REPLACE",
    "SHOWER_VALVE_REPLACE",
    "SLAB_LEAK_REPAIR",
    "SUPPLY_LINE_REPLACE",
    "TOILET_COMFORT_HEIGHT",
    "TOILET_FILL_VALVE_REPLACE",
    "TOILET_FLANGE_REPAIR",
    "TOILET_FLAPPER_REPLACE",
    "TOILET_INSTALL_NEW",
    "TOILET_REPLACE_STANDARD",
    "TUB_SPOUT_REPLACE",
    "TUB_SHOWER_COMBO_REPLACE",
    "UNDER_SINK_FILTER_INSTALL",
    "URINAL_REPLACE",
    "WATER_HEATER_FLUSH",
    "WATER_SOFTENER_INSTALL",
    "WH_40G_GAS_STANDARD",
    "WH_50G_GAS_STANDARD",
    "WH_50G_GAS_ATTIC",
    "WH_40G_ELEC_STANDARD",
    "WH_50G_ELEC_STANDARD",
    "WH_ANODE_REPLACE",
    "WH_ELEMENT_REPLACE",
    "WH_REPAIR_GAS",
    "WH_TANKLESS_GAS",
    "WH_TANKLESS_ELEC",
    "WHOLE_HOUSE_FILTER_INSTALL",
    "WHOLE_HOUSE_REPIPING",
}


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


class TaskCodeEmbeddingService:
    """Manages embeddings for labor template task codes."""

    def __init__(self) -> None:
        self.endpoint = settings.hermes_endpoint_url.replace("/v1", "/api/embeddings")
        self.model = settings.llm_embedding_model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text via Ollama embeddings API."""
        try:
            client = _get_http_client()
            resp = await client.post(
                self.endpoint,
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as exc:
            logger.error("task_code_embed.error", error=str(exc), model=self.model)
            return []

    async def search_similar(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 20,
        min_similarity: float = 0.25,
    ) -> list[str]:
        """Return the top-k task codes most similar to the query.

        Falls back to the common code list if embedding generation fails
        or the DB query returns no results.
        """
        query_embedding = await self.embed(query)
        if not query_embedding:
            logger.warning("task_code_embed.empty_embedding", query=query[:50])
            return sorted(_COMMON_TASK_CODES)

        vector_str = json.dumps(query_embedding)

        sql = text("""
            SELECT task_code,
                   1.0 - (embedding <=> CAST(:vector AS vector)) AS similarity
            FROM chat_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vector AS vector)
            LIMIT :limit
        """)

        try:
            result = await db.execute(sql, {"vector": vector_str, "limit": top_k})
            rows = result.fetchall()
        except Exception as exc:
            logger.error("task_code_embed.db_error", error=str(exc))
            return sorted(_COMMON_TASK_CODES)

        codes = []
        for row in rows:
            if row[1] >= min_similarity:
                codes.append(row[0])

        # Always include common codes so high-frequency items are never lost
        merged = set(codes) | _COMMON_TASK_CODES
        return sorted(merged)

    def build_description(self, template: LaborTemplateData) -> str:
        """Build a rich natural-language description for embedding.

        Combines the task code, human-readable name, category, and tags.
        """
        parts = [template.code.replace("_", " "), template.name]
        if template.category:
            parts.append(f"category: {template.category}")
        if template.notes:
            parts.append(template.notes)
        if template.tags:
            parts.append(f"tags: {', '.join(template.tags)}")
        return " · ".join(parts)

    async def seed_all(
        self,
        db: AsyncSession,
    ) -> dict[str, int]:
        """Generate embeddings for all labor templates and insert into DB.

        Returns {"created": N, "skipped": N, "errors": N}.
        """
        from app.models.sessions import ChatEmbedding

        created = 0
        skipped = 0
        errors = 0

        for code, template in LABOR_TEMPLATES.items():
            # Skip if already exists
            existing = await db.execute(
                select(ChatEmbedding).where(ChatEmbedding.task_code == code)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            description = self.build_description(template)
            embedding = await self.embed(description)

            if not embedding:
                logger.warning("task_code_embed.seed_failed", item=code)
                errors += 1
                continue

            db.add(
                ChatEmbedding(
                    task_code=code,
                    description=description,
                    embedding=embedding,
                    model_name=self.model,
                )
            )
            created += 1

        await db.commit()
        logger.info(
            "task_code_embed.seed_complete",
            created=created,
            skipped=skipped,
            errors=errors,
        )
        return {"created": created, "skipped": skipped, "errors": errors}


# Global singleton
task_code_embedding_service = TaskCodeEmbeddingService()
