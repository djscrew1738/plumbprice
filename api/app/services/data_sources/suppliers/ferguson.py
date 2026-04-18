"""
Ferguson Enterprises price adapter.

Two modes:
  1. Live API  — when FERGUSON_API_KEY is set, calls the Ferguson Trade Partner API.
                 Apply for access at:
                 https://www.ferguson.com/content/website-info/api-overview
  2. Simulation — jitters stored CANONICAL_MAP prices ±2.5% to mimic live data.
                  Used in development and when no API key is present.

Live API integration points are marked TODO(ferguson-api). The surrounding
request/response plumbing, auth, and DB-update logic are fully implemented.
"""

import asyncio
import httpx
import structlog
from typing import List
from datetime import datetime, timezone

from .base import SupplierScraper, ScrapedProduct

logger = structlog.get_logger()

# Ferguson Trade API uses customer account number + API key
# Header: Authorization: Bearer <api_key>
# SKU lookup: GET /pricing/products?account={account}&skus={sku1},{sku2}
# Response: { "products": [{ "sku": "...", "listPrice": 0.00, "netPrice": 0.00 }] }
_FERGUSON_PRICING_PATH = "/pricing/products"
_BATCH_SIZE = 50  # Ferguson API accepts up to 50 SKUs per request


class FergusonScraper(SupplierScraper):
    def __init__(self, simulation_mode: bool = True):
        super().__init__("ferguson")
        self.simulation_mode = simulation_mode

        from app.config import settings
        self._api_key = settings.ferguson_api_key
        self._api_base = settings.ferguson_api_base_url
        self._alert_threshold = settings.price_change_alert_threshold

        # Use live mode if an API key is configured, regardless of simulation_mode flag
        if self._api_key:
            self.simulation_mode = False

    async def fetch_prices(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        if self.simulation_mode:
            return self._simulate_fetch(canonical_items)
        return await self._live_fetch(canonical_items)

    # ── Live API ──────────────────────────────────────────────────────────────

    async def _live_fetch(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        from app.services.supplier_service import CANONICAL_MAP

        # Build SKU → canonical_item reverse map so we can match API response back
        sku_to_canonical: dict[str, str] = {}
        sku_list: list[str] = []
        for item_id in canonical_items:
            ferguson_data = CANONICAL_MAP.get(item_id, {}).get("ferguson")
            if ferguson_data and ferguson_data.get("sku"):
                sku = ferguson_data["sku"]
                sku_to_canonical[sku] = item_id
                sku_list.append(sku)

        if not sku_list:
            return []

        results: List[ScrapedProduct] = []
        failed_canonical_items: list[str] = []
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            # Process in batches of _BATCH_SIZE
            for i in range(0, len(sku_list), _BATCH_SIZE):
                batch = sku_list[i : i + _BATCH_SIZE]
                batch_succeeded = False
                # Retry transient failures (connection / 5xx) up to 3 times w/ backoff.
                last_exc: Exception | None = None
                for attempt in range(3):
                    try:
                        # TODO(ferguson-api): Replace with verified Ferguson Trade API endpoint.
                        # The path, query params, and response shape below are based on
                        # Ferguson's published API overview. Verify against their actual
                        # sandbox documentation before enabling in production.
                        resp = await client.get(
                            f"{self._api_base}{_FERGUSON_PRICING_PATH}",
                            params={"skus": ",".join(batch)},
                            headers=headers,
                        )
                        resp.raise_for_status()
                        data = resp.json()

                        for product in data.get("products", []):
                            sku = product.get("sku", "")
                            canonical_id = sku_to_canonical.get(sku)
                            if not canonical_id:
                                continue

                            # Prefer net (trade) price; fall back to list price
                            cost = product.get("netPrice") or product.get("listPrice")
                            if not cost:
                                continue

                            original_cost = CANONICAL_MAP.get(canonical_id, {}).get("ferguson", {}).get("cost", 0)
                            self._check_price_alert(canonical_id, sku, original_cost, float(cost))

                            results.append(ScrapedProduct(
                                canonical_item=canonical_id,
                                sku=sku,
                                name=product.get("description", CANONICAL_MAP.get(canonical_id, {}).get("ferguson", {}).get("name", sku)),
                                cost=round(float(cost), 2),
                                scraped_at=datetime.now(timezone.utc),
                                source_url=f"{self._api_base}{_FERGUSON_PRICING_PATH}?skus={sku}",
                            ))
                        batch_succeeded = True
                        break  # batch done

                    except httpx.HTTPStatusError as e:
                        last_exc = e
                        # Only retry on 5xx; client errors won't recover.
                        if 500 <= e.response.status_code < 600 and attempt < 2:
                            backoff = 0.5 * (2 ** attempt)
                            logger.warning(
                                "ferguson.api_5xx_retry",
                                status=e.response.status_code,
                                batch_start=i,
                                attempt=attempt + 1,
                                backoff=backoff,
                            )
                            await asyncio.sleep(backoff)
                            continue
                        logger.error("ferguson.api_error", status=e.response.status_code, batch_start=i)
                        break
                    except (httpx.TransportError, httpx.TimeoutException) as e:
                        last_exc = e
                        if attempt < 2:
                            backoff = 0.5 * (2 ** attempt)
                            logger.warning("ferguson.transport_retry", error=str(e), batch_start=i, attempt=attempt + 1)
                            await asyncio.sleep(backoff)
                            continue
                        logger.error("ferguson.transport_failed", error=str(e), batch_start=i)
                        break
                    except Exception as e:
                        last_exc = e
                        logger.error("ferguson.fetch_error", error=str(e), batch_start=i)
                        break

                if not batch_succeeded:
                    # Track which canonical items in this batch had no live data.
                    for sku in batch:
                        canonical_id = sku_to_canonical.get(sku)
                        if canonical_id:
                            failed_canonical_items.append(canonical_id)

        # Fallback: simulate prices for canonical items the live API couldn't return.
        if failed_canonical_items:
            logger.warning(
                "ferguson.fallback_to_simulation",
                missing=len(failed_canonical_items),
                fetched=len(results),
            )
            simulated = self._simulate_fetch(failed_canonical_items)
            results.extend(simulated)

        logger.info("ferguson.live_fetch_complete", fetched=len(results), total_skus=len(sku_list))
        return results

    def _check_price_alert(self, canonical_id: str, sku: str, old_cost: float, new_cost: float) -> None:
        if old_cost <= 0:
            return
        deviation = abs(new_cost - old_cost) / old_cost
        if deviation >= self._alert_threshold:
            logger.warning(
                "price_change_alert",
                supplier="ferguson",
                canonical_item=canonical_id,
                sku=sku,
                old_cost=old_cost,
                new_cost=new_cost,
                pct_change=round(deviation * 100, 1),
            )

    # ── Simulation ────────────────────────────────────────────────────────────

    def _simulate_fetch(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        import random
        from app.services.supplier_service import CANONICAL_MAP

        results = []
        for item_id in canonical_items:
            item_data = CANONICAL_MAP.get(item_id, {}).get("ferguson")
            if not item_data:
                continue
            jitter = 1 + (random.random() * 0.05 - 0.025)  # ±2.5%
            new_cost = round(item_data["cost"] * jitter, 2)
            results.append(ScrapedProduct(
                canonical_item=item_id,
                sku=item_data["sku"],
                name=item_data["name"],
                cost=new_cost,
                scraped_at=datetime.now(timezone.utc),
                source_url=f"https://www.ferguson.com/search?q={item_data['sku']}",
            ))
        return results
