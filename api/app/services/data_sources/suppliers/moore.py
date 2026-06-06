"""
Moore Supply Co. price scraper.

Two modes:
  1. Live scrape  — when MOORE_SUPPLY_ENABLED=true, uses httpx to fetch product
                    pages with BeautifulSoup4 HTML parsing. Rate-limited to
                    1 request per 3 seconds to respect server etiquette.
  2. Simulation   — jitters stored CANONICAL_MAP prices ±2% (default / test mode).
"""

import asyncio
import structlog
from typing import List
from datetime import datetime, timezone

import httpx

from .base import SupplierScraper, ScrapedProduct

logger = structlog.get_logger()

_RATE_LIMIT_SECS = 3.0   # minimum seconds between requests
_REQUEST_TIMEOUT = 15.0  # seconds per request
_MAX_RETRIES = 2


class MooreScraper(SupplierScraper):
    def __init__(self, simulation_mode: bool = True):
        super().__init__("moore_supply")
        self.base_url = "https://mooresupply.com"
        self._last_request_at: float = 0.0

        from app.config import settings
        # Allow env-var override to enable live scraping
        live_enabled = getattr(settings, "moore_supply_enabled", False)
        self.simulation_mode = not live_enabled if not simulation_mode else simulation_mode

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def _throttle(self) -> None:
        """Enforce minimum gap between requests."""
        import time
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _RATE_LIMIT_SECS:
            await asyncio.sleep(_RATE_LIMIT_SECS - elapsed)

    async def _fetch_sku_price(self, client: httpx.AsyncClient, sku: str) -> float | None:
        """Fetch the price for a single SKU from mooresupply.com search."""
        await self._throttle()
        import time
        self._last_request_at = time.monotonic()

        url = f"{self.base_url}/search/{sku}"
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.get(url, headers=self.headers, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()
                return self._parse_price_html(resp.text, sku)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    backoff = _RATE_LIMIT_SECS * (attempt + 2)
                    logger.warning("moore_supply.rate_limited", sku=sku, backoff=backoff)
                    await asyncio.sleep(backoff)
                elif exc.response.status_code >= 500 and attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RATE_LIMIT_SECS)
                else:
                    logger.error("moore_supply.http_error", sku=sku, status=exc.response.status_code)
                    return None
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning("moore_supply.request_failed", sku=sku, error=str(exc), attempt=attempt)
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RATE_LIMIT_SECS * (attempt + 1))
                else:
                    return None
        return None

    def _parse_price_html(self, html: str, sku: str) -> float | None:
        """Parse price from search results HTML using BeautifulSoup4."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("moore_supply.bs4_not_installed")
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
            # Moore Supply typically renders prices in elements with data-price or
            # class names containing "price". Try multiple selector strategies.
            for selector in [
                "[data-price]",
                ".product-price",
                ".price-value",
                "[itemprop='price']",
            ]:
                el = soup.select_one(selector)
                if el:
                    raw = el.get("data-price") or el.get_text(strip=True)
                    if raw:
                        cleaned = str(raw).replace("$", "").replace(",", "").strip()
                        try:
                            return float(cleaned)
                        except ValueError:
                            continue
        except Exception as exc:
            logger.warning("moore_supply.parse_error", sku=sku, error=str(exc))
        return None

    async def fetch_prices(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        if self.simulation_mode:
            return self._simulate_fetch(canonical_items)
        return await self._live_fetch(canonical_items)

    async def _live_fetch(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        from app.services.supplier_service import CANONICAL_MAP
        results: List[ScrapedProduct] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for item_id in canonical_items:
                item_data = CANONICAL_MAP.get(item_id, {}).get("moore_supply")
                if not item_data:
                    continue
                sku = item_data["sku"]
                price = await self._fetch_sku_price(client, sku)
                if price is None:
                    logger.info("moore_supply.price_unavailable", canonical_item=item_id, sku=sku)
                    continue
                results.append(ScrapedProduct(
                    canonical_item=item_id,
                    sku=sku,
                    name=item_data["name"],
                    cost=price,
                    scraped_at=datetime.now(timezone.utc),
                    source_url=f"{self.base_url}/search/{sku}",
                ))

        logger.info("moore_supply.live_fetch_complete", items_fetched=len(results))
        return results

    def _simulate_fetch(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        import random
        from app.services.supplier_service import CANONICAL_MAP
        results = []
        for item_id in canonical_items:
            item_data = CANONICAL_MAP.get(item_id, {}).get("moore_supply")
            if item_data:
                jitter = 1 + (random.random() * 0.04 - 0.02)
                results.append(ScrapedProduct(
                    canonical_item=item_id,
                    sku=item_data["sku"],
                    name=item_data["name"],
                    cost=round(item_data["cost"] * jitter, 2),
                    scraped_at=datetime.now(timezone.utc),
                    source_url=f"{self.base_url}/search?q={item_data['sku']}",
                ))
        return results

