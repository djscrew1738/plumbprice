"""Retail benchmark price feed adapter — Home Depot / Lowe's via Apify.

Wraps the Apify web-scraping layer to provide retail MSRP benchmarks
for canonical plumbing items.  Retail prices are used as a cross-check
against wholesale supplier feeds (Ferguson, Moore Supply, Apex).

Confidence: 0.65 (below verified supplier API 0.95, above simulation 0.60)
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.price_feed_adapter import PriceFeedAdapter, PriceFeedResult, FeedHealth
from app.services.data_sources import apify_source


class RetailBenchmarkAdapter(PriceFeedAdapter):
    """Price feed adapter for retail benchmarking (Home Depot / Lowe's).

    Uses Apify Platform to scrape live retail prices.  Falls back to
    empty results when Apify token is missing or scraping fails.
    """

    def __init__(self):
        self._last_sync: datetime | None = None
        self._last_count: int = 0
        self._last_error: str | None = None
        self._last_response_time_ms: float | None = None

    @property
    def name(self) -> str:
        return "retail_benchmark"

    async def fetch(self, canonical_items: list[str]) -> list[PriceFeedResult]:
        start = datetime.now(timezone.utc)
        try:
            apify_prices = await apify_source.fetch_prices(
                canonical_ids=canonical_items,
            )
        except Exception as exc:
            self._last_error = str(exc)
            self._last_sync = datetime.now(timezone.utc)
            self._last_response_time_ms = (
                datetime.now(timezone.utc) - start
            ).total_seconds() * 1000
            raise

        results = []
        for p in apify_prices:
            # Retail price is MSRP; estimate wholesale at 60% of retail
            estimated_wholesale = round(p.price * 0.60, 2)
            results.append(
                PriceFeedResult(
                    canonical_item=p.canonical_id,
                    sku=p.sku,
                    name=p.name,
                    cost=estimated_wholesale,
                    msrp=p.price,
                    currency=p.currency,
                    source=f"{self.name}:{p.retailer}",
                    scraped_at=datetime.now(timezone.utc),
                    confidence=0.65,
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
        if self._last_error:
            status = "unhealthy"
        elif not self._last_sync:
            status = "degraded"
        elif (datetime.now(timezone.utc) - self._last_sync).total_seconds() > 86400:
            status = "degraded"
        return FeedHealth(
            name=self.name,
            status=status,
            last_sync=self._last_sync,
            items_synced=self._last_count,
            error_count=0 if not self._last_error else 1,
            error_message=self._last_error,
            response_time_ms=self._last_response_time_ms,
        )
