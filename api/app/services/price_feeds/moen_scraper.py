"""Moen MSRP scraper.

Scrapes moen.com product pages for MSRP pricing.
Uses cached prices as fallback when scraping fails.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

import structlog

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

from app.services.price_feed_adapter import PriceFeedAdapter, PriceFeedResult, FeedHealth

logger = structlog.get_logger()

_MOEN_PRODUCT_URLS: dict[str, str] = {
    "faucet.kitchen.pull_down": "https://www.moen.com/kitchen-faucets",
    "faucet.bathroom.single": "https://www.moen.com/bathroom-faucets",
    "shower.valve_pressure_balance": "https://www.moen.com/showering/shower-valves",
    "shower.head_rain": "https://www.moen.com/showering/showerheads",
    "smart.faucet.voice_control": "https://www.moen.com/smart-water-network",
    "smart.shower.digital": "https://www.moen.com/smart-water-network",
    "tub.spout_diverter": "https://www.moen.com/bathroom-faucets/tub-spouts",
}


class MoenScraper(PriceFeedAdapter):
    """Scrapes Moen MSRP from product pages."""

    def __init__(self):
        self._last_sync: datetime | None = None
        self._last_count: int = 0
        self._last_error: str | None = None
        self._cache: dict[str, PriceFeedResult] = {}

    @property
    def name(self) -> str:
        return "moen"

    async def fetch(self, canonical_items: list[str]) -> list[PriceFeedResult]:
        if not _HTTPX_AVAILABLE or not _BS4_AVAILABLE:
            self._last_error = "Missing httpx or beautifulsoup4"
            return list(self._cache.values())

        results: list[PriceFeedResult] = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for item_id in canonical_items:
                url = _MOEN_PRODUCT_URLS.get(item_id)
                if not url:
                    continue
                try:
                    result = await self._scrape_product(client, item_id, url)
                    if result:
                        results.append(result)
                        self._cache[item_id] = result
                except Exception as exc:
                    logger.warning("moen.scrape_error", item=item_id, error=str(exc))
                    if item_id in self._cache:
                        results.append(self._cache[item_id])
                await asyncio.sleep(0.5)

        self._last_sync = datetime.now(timezone.utc)
        self._last_count = len(results)
        self._last_error = None
        return results

    async def _scrape_product(
        self,
        client: httpx.AsyncClient,
        canonical_item: str,
        url: str,
    ) -> Optional[PriceFeedResult]:
        resp = await client.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
            },
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        price = self._extract_price(soup)
        if not price:
            return None

        name_elem = soup.find("h1") or soup.find("meta", property="og:title")
        name = ""
        if name_elem:
            name = name_elem.get_text(strip=True) if hasattr(name_elem, "get_text") else name_elem.get("content", "")

        return PriceFeedResult(
            canonical_item=canonical_item,
            sku=None,
            name=name or canonical_item,
            cost=price * 0.6,
            msrp=price,
            manufacturer="Moen",
            source=self.name,
            scraped_at=datetime.now(timezone.utc),
            confidence=0.7,
        )

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        selectors = [
            '[data-testid="product-price"]',
            '.product-price',
            '.price-current',
            'meta[itemprop="price"]',
            '.sr-only',
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True) if hasattr(elem, "get_text") else elem.get("content", "")
                match = re.search(r"\$?([0-9,]+\.\d{2})", text)
                if match:
                    return float(match.group(1).replace(",", ""))
        return None

    async def health(self) -> FeedHealth:
        status = "healthy"
        if self._last_error:
            status = "unhealthy"
        elif not self._last_sync or (datetime.now(timezone.utc) - self._last_sync).days > 1:
            status = "degraded"
        return FeedHealth(
            name=self.name,
            status=status,
            last_sync=self._last_sync,
            items_synced=self._last_count,
            error_count=0 if not self._last_error else 1,
            error_message=self._last_error,
        )
