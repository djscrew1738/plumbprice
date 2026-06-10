"""Generic price feed adapter framework.

Provides a uniform interface for all external price sources:
- Verified supplier APIs (Ferguson OAuth2)
- Manufacturer MSRP scrapers (Kohler, Moen, Delta, AO Smith)
- Professional cost databases (RSMeans, Bluebook) — deferred
- Retail benchmark scrapers (Apify/Home Depot)

Usage:
    from app.services.price_feed_adapter import registry, FeedHealth
    adapter = registry.get("kohler")
    results = await adapter.fetch(["toilet.standard.round"])
    health = await adapter.health()
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class PriceFeedResult:
    canonical_item: str
    sku: str | None
    name: str
    cost: float
    msrp: float | None = None
    currency: str = "USD"
    in_stock: bool | None = None
    lead_time: str | None = None
    manufacturer: str | None = None
    source: str = ""
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0  # 0.0-1.0, decays when stale


@dataclass
class FeedHealth:
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_sync: datetime | None = None
    items_synced: int = 0
    error_count: int = 0
    error_message: str | None = None
    response_time_ms: float | None = None


class PriceFeedAdapter(ABC):
    """Abstract base class for all price feed adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique adapter name (e.g. 'ferguson', 'kohler')."""
        ...

    @abstractmethod
    async def fetch(self, canonical_items: list[str]) -> list[PriceFeedResult]:
        """Fetch prices for the given canonical items.

        Returns a list of PriceFeedResult. Items that could not be fetched
        are silently omitted — the caller decides how to handle gaps.
        """
        ...

    @abstractmethod
    async def health(self) -> FeedHealth:
        """Return the current health status of this feed."""
        ...


class PriceFeedRegistry:
    """Central registry for all price feed adapters."""

    def __init__(self):
        self._adapters: dict[str, PriceFeedAdapter] = {}

    def register(self, adapter: PriceFeedAdapter) -> None:
        if adapter.name in self._adapters:
            logger.warning("price_feed.registry_override", name=adapter.name)
        self._adapters[adapter.name] = adapter
        logger.info("price_feed.registered", name=adapter.name)

    def get(self, name: str) -> PriceFeedAdapter | None:
        return self._adapters.get(name)

    def list_adapters(self) -> list[str]:
        return sorted(self._adapters.keys())

    async def run_all(
        self,
        canonical_items: list[str],
    ) -> dict[str, list[PriceFeedResult]]:
        """Run all registered adapters and collect results.

        Returns a mapping of adapter_name -> list[PriceFeedResult].
        Errors in individual adapters are logged but don't fail the batch.
        """
        results: dict[str, list[PriceFeedResult]] = {}
        for name, adapter in self._adapters.items():
            try:
                adapter_results = await adapter.fetch(canonical_items)
                results[name] = adapter_results
                logger.info(
                    "price_feed.batch_complete",
                    adapter=name,
                    fetched=len(adapter_results),
                    requested=len(canonical_items),
                )
            except Exception as exc:
                logger.error("price_feed.batch_error", adapter=name, error=str(exc))
                results[name] = []
        return results

    async def health_all(self) -> dict[str, FeedHealth]:
        """Return health status for all registered adapters."""
        health_map: dict[str, FeedHealth] = {}
        for name, adapter in self._adapters.items():
            try:
                health_map[name] = await adapter.health()
            except Exception as exc:
                health_map[name] = FeedHealth(
                    name=name,
                    status="unhealthy",
                    error_message=str(exc),
                )
        return health_map


# Global registry instance
registry = PriceFeedRegistry()
