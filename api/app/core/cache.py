"""Simple async Redis cache helper.

Usage:
    from app.core.cache import cache_get, cache_set, cache_invalidate

    cached = await cache_get("suppliers:list")
    if cached is None:
        data = compute_data()
        await cache_set("suppliers:list", data, ttl=300)
    else:
        data = cached
"""
import json
import os
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


def _is_test_env() -> bool:
    """Tests must never hit a real Redis — it leaks state across runs and
    breaks deterministic assertions (e.g. an empty-state test that gets
    served stale `analytics:revenue:*` data from a prior pytest session).
    """
    return os.getenv("ENVIRONMENT", "").lower() == "test"


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def cache_get(key: str) -> Any | None:
    if _is_test_env():
        return None
    try:
        raw = await _get_redis().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get_error", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    if _is_test_env():
        return
    try:
        await _get_redis().set(key, json.dumps(value), ex=ttl)
    except Exception as exc:
        logger.warning("cache_set_error", key=key, error=str(exc))


async def cache_invalidate(*keys: str) -> None:
    if not keys:
        return
    if _is_test_env():
        return
    try:
        await _get_redis().delete(*keys)
    except Exception as exc:
        logger.warning("cache_invalidate_error", keys=keys, error=str(exc))
