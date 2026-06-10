"""Ferguson price feed adapter — wraps the existing FergusonScraper."""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.price_feed_adapter import PriceFeedAdapter, PriceFeedResult, FeedHealth
from app.services.data_sources.suppliers.ferguson import FergusonScraper


class FergusonAdapter(PriceFeedAdapter):
    """Price feed adapter for Ferguson Enterprises.

    Uses the existing FergusonScraper which supports:
    - OAuth2 client credentials flow
    - Legacy bearer token auth
    - Simulation fallback (±2.5% jitter on CANONICAL_MAP)
    """

    def __init__(self):
        self._scraper = FergusonScraper(simulation_mode=True)
        self._last_sync: datetime | None = None
        self._last_count: int = 0
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        return "ferguson"

    async def fetch(self, canonical_items: list[str]) -> list[PriceFeedResult]:
        scraped = await self._scraper.fetch_prices(canonical_items)
        results = []
        for p in scraped:
            results.append(PriceFeedResult(
                canonical_item=p.canonical_item,
                sku=p.sku,
                name=p.name,
                cost=p.cost,
                currency=p.currency,
                source=self.name,
                scraped_at=p.scraped_at,
                confidence=0.95 if not self._scraper.simulation_mode else 0.6,
            ))
        self._last_sync = datetime.now(timezone.utc)
        self._last_count = len(results)
        self._last_error = None
        return results

    async def health(self) -> FeedHealth:
        status = "healthy"
        if self._scraper.simulation_mode:
            status = "degraded"
        return FeedHealth(
            name=self.name,
            status=status,
            last_sync=self._last_sync,
            items_synced=self._last_count,
            error_count=0 if not self._last_error else 1,
            error_message=self._last_error,
        )
