"""Celery / Redis broker availability helpers.

Used by upload endpoints to fail fast (503) when the task broker is down,
so we don't silently black-hole files that were uploaded to object storage.
"""

from __future__ import annotations

import time
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger()

# Simple TTL cache so we don't ping Redis on every request.
_CACHE_TTL_SECONDS = 5.0
_last_check_at: float = 0.0
_last_result: bool = False


async def broker_available(force: bool = False) -> bool:
    """Return True if the Celery broker (Redis) is reachable.

    Result is cached for _CACHE_TTL_SECONDS so a burst of uploads doesn't
    hammer Redis with pings. Pass force=True to bypass the cache.
    """
    global _last_check_at, _last_result

    now = time.monotonic()
    if not force and (now - _last_check_at) < _CACHE_TTL_SECONDS:
        return _last_result

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.celery_broker_url, socket_connect_timeout=2, socket_timeout=2
        )
        try:
            pong = await client.ping()
        finally:
            await client.aclose()
        _last_result = bool(pong)
    except Exception as exc:
        logger.warning("broker.ping_failed", error=str(exc))
        _last_result = False

    _last_check_at = now
    return _last_result
