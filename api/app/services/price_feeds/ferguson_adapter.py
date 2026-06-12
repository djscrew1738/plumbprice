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

    Simulation mode is auto-detected from env credentials and
    FERGUSON_API_VERIFY_MODE (off / lenient / strict).
    """

    def __init__(self):
        # Let FergusonScraper auto-detect simulation vs live from env
        self._scraper = FergusonScraper()
        self._last_sync: datetime | None = None
        self._last_count: int = 0
        self._last_error: str | None = None
        self._last_response_time_ms: float | None = None

    @property
    def name(self) -> str:
        return "ferguson"

    async def fetch(self, canonical_items: list[str]) -> list[PriceFeedResult]:
        start = datetime.now(timezone.utc)
        try:
            scraped = await self._scraper.fetch_prices(canonical_items)
        except Exception as exc:
            self._last_error = str(exc)
            self._last_sync = datetime.now(timezone.utc)
            self._last_response_time_ms = (
                datetime.now(timezone.utc) - start
            ).total_seconds() * 1000
            raise

        results = []
        for p in scraped:
            results.append(
                PriceFeedResult(
                    canonical_item=p.canonical_item,
                    sku=p.sku,
                    name=p.name,
                    cost=p.cost,
                    currency=p.currency,
                    source=self.name,
                    scraped_at=p.scraped_at,
                    confidence=0.95 if not self._scraper.simulation_mode else 0.60,
                )
            )
        self._last_sync = datetime.now(timezone.utc)
        self._last_count = len(results)
        self._last_error = None
        self._last_response_time_ms = (
            datetime.now(timezone.utc) - start
        ).total_seconds() * 1000
        return results

    async def health(self) -> FeedHealth:
        status = "healthy"
        if self._scraper.simulation_mode:
            status = "degraded"
        if self._last_error:
            status = "unhealthy"
        return FeedHealth(
            name=self.name,
            status=status,
            last_sync=self._last_sync,
            items_synced=self._last_count,
            error_count=0 if not self._last_error else 1,
            error_message=self._last_error,
            response_time_ms=self._last_response_time_ms,
        )
