"""Tests for the supplier circuit breaker."""

import asyncio
import pytest

from app.services.data_sources.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_closed_breaker_passes_through() -> None:
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=1.0)

    async def ok() -> int:
        return 42

    assert await cb.call("k", ok) == 42
    assert cb.state("k") == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_opens_after_threshold_failures() -> None:
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10.0)

    async def fail() -> None:
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.call("k", fail)

    assert cb.state("k") == CircuitState.OPEN

    # Next call short-circuits with CircuitOpenError, not RuntimeError.
    with pytest.raises(CircuitOpenError):
        await cb.call("k", fail)


@pytest.mark.asyncio
async def test_half_open_then_closes_on_success() -> None:
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.05)

    async def fail() -> None:
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call("k", fail)
    assert cb.state("k") == CircuitState.OPEN

    # Wait for cooldown.
    await asyncio.sleep(0.1)

    async def ok() -> str:
        return "good"

    assert await cb.call("k", ok) == "good"
    assert cb.state("k") == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens() -> None:
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.05)

    async def fail() -> None:
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call("k", fail)

    await asyncio.sleep(0.1)

    # First call after cooldown is the half-open probe — failing reopens.
    with pytest.raises(RuntimeError):
        await cb.call("k", fail)

    assert cb.state("k") == CircuitState.OPEN
    # And immediately short-circuits again.
    with pytest.raises(CircuitOpenError):
        await cb.call("k", fail)


@pytest.mark.asyncio
async def test_isolation_between_keys() -> None:
    cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=10.0)

    async def fail() -> None:
        raise RuntimeError("boom")

    async def ok() -> int:
        return 1

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call("ferguson", fail)

    # Ferguson is open, but moore is unaffected.
    assert cb.state("ferguson") == CircuitState.OPEN
    assert await cb.call("moore", ok) == 1
    assert cb.state("moore") == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_reset_clears_state() -> None:
    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=10.0)

    async def fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cb.call("k", fail)
    assert cb.state("k") == CircuitState.OPEN

    await cb.reset("k")
    assert cb.state("k") == CircuitState.CLOSED


def test_invalid_config() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0)
    with pytest.raises(ValueError):
        CircuitBreaker(cooldown_seconds=0)
