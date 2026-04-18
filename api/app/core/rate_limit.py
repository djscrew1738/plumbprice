"""Redis-backed brute-force / rate-limit counter.

Falls back to an in-process counter when Redis is unavailable so dev/test
environments still work; production deployments must have Redis reachable.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger()

# In-process fallback used only when Redis is unreachable.
_local_counts: dict[str, list[float]] = defaultdict(list)


def _redis_client():
    try:
        import redis.asyncio as aioredis

        return aioredis.from_url(
            settings.celery_broker_url, socket_connect_timeout=1, socket_timeout=1
        )
    except Exception:  # pragma: no cover — import failure is unexpected
        return None


async def record_failure(key: str, window_seconds: int) -> int:
    """Record a failed attempt for `key` and return the count within `window_seconds`."""
    client = _redis_client()
    if client is None:
        return _local_record(key, window_seconds)

    redis_key = f"bf:{key}"
    try:
        # INCR + EXPIRE atomic via pipeline
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds)
            count, _ = await pipe.execute()
        return int(count)
    except Exception as exc:
        logger.warning("rate_limit.record_failed", key=key, error=str(exc))
        return _local_record(key, window_seconds)
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


async def get_count(key: str, window_seconds: int) -> int:
    """Return current failure count for `key` within `window_seconds`."""
    client = _redis_client()
    if client is None:
        return _local_count(key, window_seconds)
    redis_key = f"bf:{key}"
    try:
        val = await client.get(redis_key)
        return int(val) if val else 0
    except Exception as exc:
        logger.warning("rate_limit.get_failed", key=key, error=str(exc))
        return _local_count(key, window_seconds)
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


async def clear(key: str) -> None:
    """Clear failure counter for `key` (e.g. after successful login)."""
    _local_counts.pop(key, None)
    client = _redis_client()
    if client is None:
        return
    try:
        await client.delete(f"bf:{key}")
    except Exception as exc:
        logger.warning("rate_limit.clear_failed", key=key, error=str(exc))
    finally:
        try:
            await client.aclose()
        except Exception:
            pass


def _local_record(key: str, window_seconds: int) -> int:
    now = time.time()
    cutoff = now - window_seconds
    _local_counts[key] = [t for t in _local_counts[key] if t > cutoff]
    _local_counts[key].append(now)
    return len(_local_counts[key])


def _local_count(key: str, window_seconds: int) -> int:
    now = time.time()
    cutoff = now - window_seconds
    _local_counts[key] = [t for t in _local_counts[key] if t > cutoff]
    return len(_local_counts[key])
