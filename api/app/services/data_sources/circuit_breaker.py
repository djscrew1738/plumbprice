"""
Async circuit breaker for supplier integrations.

Protects upstream supplier APIs (Ferguson, etc.) so a partial outage
doesn't cascade into estimator latency. Three states:

- CLOSED   — calls flow normally; failures increment a counter.
- OPEN     — calls short-circuit immediately for `cooldown_seconds`.
- HALF_OPEN — first probe call after cooldown; success closes the
              circuit, failure re-opens it for another cooldown.

Designed to be process-local; for multi-worker fleets pair with
last-known-good cache reads (see callers).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the breaker is OPEN."""


@dataclass
class _BreakerStats:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float = 0.0
    last_failure: Optional[str] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CircuitBreaker:
    """
    Per-key (e.g. supplier slug) circuit breaker registry.

    Use one shared instance and call `await breaker.call(key, fn)`.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be > 0")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._stats: Dict[str, _BreakerStats] = {}
        self._registry_lock = asyncio.Lock()

    async def _get(self, key: str) -> _BreakerStats:
        async with self._registry_lock:
            if key not in self._stats:
                self._stats[key] = _BreakerStats()
            return self._stats[key]

    def state(self, key: str) -> CircuitState:
        return self._stats.get(key, _BreakerStats()).state

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for k, s in self._stats.items():
            out[k] = {
                "state": s.state.value,
                "failure_count": s.failure_count,
                "opened_at": s.opened_at,
                "last_failure": s.last_failure,
            }
        return out

    async def _maybe_half_open(self, stats: _BreakerStats) -> None:
        if stats.state != CircuitState.OPEN:
            return
        if time.monotonic() - stats.opened_at >= self.cooldown_seconds:
            stats.state = CircuitState.HALF_OPEN
            logger.info("circuit_breaker.half_open")

    async def _on_success(self, key: str, stats: _BreakerStats) -> None:
        if stats.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("circuit_breaker.closed", key=key)
        stats.state = CircuitState.CLOSED
        stats.failure_count = 0
        stats.opened_at = 0.0
        stats.last_failure = None

    async def _on_failure(self, key: str, stats: _BreakerStats, exc: BaseException) -> None:
        stats.failure_count += 1
        stats.last_failure = f"{type(exc).__name__}: {exc}"
        if (
            stats.state == CircuitState.HALF_OPEN
            or stats.failure_count >= self.failure_threshold
        ):
            stats.state = CircuitState.OPEN
            stats.opened_at = time.monotonic()
            logger.warning(
                "circuit_breaker.opened",
                key=key,
                failures=stats.failure_count,
                last=stats.last_failure,
            )

    async def call(self, key: str, fn: Callable[[], Awaitable[T]]) -> T:
        stats = await self._get(key)
        async with stats.lock:
            await self._maybe_half_open(stats)
            if stats.state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"circuit '{key}' is OPEN (last: {stats.last_failure})"
                )
        try:
            result = await fn()
        except Exception as exc:
            async with stats.lock:
                await self._on_failure(key, stats, exc)
            raise
        async with stats.lock:
            await self._on_success(key, stats)
        return result

    async def reset(self, key: Optional[str] = None) -> None:
        async with self._registry_lock:
            if key is None:
                self._stats.clear()
            else:
                self._stats.pop(key, None)


# Module-level shared instance for supplier integrations.
supplier_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=60.0)
