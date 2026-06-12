"""One-shot script to seed chat_embeddings for all canonical items.

Usage:
    cd api
    source .venv/bin/activate
    python -m scripts.seed_chat_embeddings

Requires: Ollama running with the embedding model (default: mxbai-embed-large).
"""
from __future__ import annotations

import asyncio
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import structlog

from app.database import AsyncSessionLocal
from app.services.task_code_embeddings import task_code_embedding_service

logger = structlog.get_logger()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        stats = await task_code_embedding_service.seed_all(db)
    logger.info(
        "seed_chat_embeddings.complete",
        created=stats["created"],
        skipped=stats["skipped"],
        errors=stats["errors"],
        total=len(CANONICAL_MAP),
    )
    print(f"Created: {stats['created']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}")


if __name__ == "__main__":
    asyncio.run(main())
