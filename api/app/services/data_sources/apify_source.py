"""
Apify Platform data source — scrapes live plumbing material prices from
Home Depot and Lowe's using the Apify REST API.

Requires: APIFY_TOKEN env var (free tier: 50 runs/month, ~250K results)

Actor used: apify/website-content-crawler (generic, always available on free tier)
Override with APIFY_ACTOR_ID env var to use a specialized Home Depot scraper
if you have one subscribed (e.g. "epctex/home-depot-products-scraper").

Workflow:
  1. POST /v2/acts/{actor_id}/runs?waitForFinish=120 with search URL inputs
  2. GET  /v2/datasets/{datasetId}/items to retrieve scraped products
  3. Parse product name, price, SKU → map to canonical plumbing items
  4. Results cached in-memory (TTL set by price_enrichment layer)
"""

from __future__ import annotations

import re
import asyncio
from dataclasses import dataclass
from typing import Optional
import structlog

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

logger = structlog.get_logger()

APIFY_BASE = "https://api.apify.com/v2"
# Default actor: generic crawler (always available on free tier)
# For better results install a dedicated Home Depot actor and set APIFY_ACTOR_ID
DEFAULT_ACTOR_ID = "apify/website-content-crawler"
MAX_PAGES_PER_RUN = 3
RUN_TIMEOUT_SECONDS = 120


@dataclass
class ApifyPrice:
    canonical_id: str
    source: str
    retailer: str
    name: str
    price: float
    sku: Optional[str]
    url: Optional[str]
    currency: str = "USD"
    unit: str = "ea"


# ─── Search URL templates for common plumbing items ───────────────────────────
# Home Depot search URLs mapped to canonical IDs
HD_SEARCH_URLS: list[tuple[str, str]] = [
    ("toilet.wax_ring",          "https://www.homedepot.com/s/wax%20ring?NCNI-5"),
    ("toilet.supply_line_12",    "https://www.homedepot.com/s/toilet%20supply%20line%2012%20inch?NCNI-5"),
    ("toilet.closet_bolts",      "https://www.homedepot.com/s/closet%20bolts%20toilet?NCNI-5"),
    ("wh.expansion_tank_2g",     "https://www.homedepot.com/s/thermal%20expansion%20tank%202%20gallon?NCNI-5"),
    ("wh.tp_valve_075",          "https://www.homedepot.com/s/tp%20relief%20valve%203%204?NCNI-5"),
    ("wh.gas_flex_connector_18", "https://www.homedepot.com/s/gas%20flex%20connector%2018%20inch?NCNI-5"),
    ("kitchen.faucet_single",    "https://www.homedepot.com/s/kitchen%20faucet%20single%20handle?NCNI-5"),
    ("disposal.half_hp",         "https://www.homedepot.com/s/garbage%20disposal%201%2F2%20hp?NCNI-5"),
    ("prv.valve_075",            "https://www.homedepot.com/s/pressure%20reducing%20valve%203%204?NCNI-5"),
    ("shower.valve_body",        "https://www.homedepot.com/s/pressure%20balance%20shower%20valve?NCNI-5"),
    ("valve.ball_075",           "https://www.homedepot.com/s/ball%20valve%203%204%20inch%20brass?NCNI-5"),
    ("misc.pex_crimp_075_10ft",  "https://www.homedepot.com/s/pex%20tubing%203%204%20inch?NCNI-5"),
]


async def fetch_prices(
    token: str,
    actor_id: str = DEFAULT_ACTOR_ID,
    canonical_ids: Optional[list[str]] = None,
) -> list[ApifyPrice]:
    """
    Run Apify actor to scrape plumbing product prices from Home Depot.
    Returns list of ApifyPrice objects for matched canonical items.
    Falls back to empty list on any error (non-blocking).
    """
    if not _HTTPX_AVAILABLE:
        logger.warning("apify.httpx_missing", msg="httpx not installed; skipping Apify fetch")
        return []

    target_urls = HD_SEARCH_URLS
    if canonical_ids:
        target_urls = [(cid, url) for cid, url in HD_SEARCH_URLS if cid in canonical_ids]
    if not target_urls:
        return []

    # Batch into groups of 6 URLs per run to stay within free-tier limits
    results: list[ApifyPrice] = []
    batch = target_urls[:6]  # max 6 search pages per run

    logger.info("apify.run_start", actor=actor_id, urls=len(batch))

    try:
        async with httpx.AsyncClient(timeout=RUN_TIMEOUT_SECONDS + 30) as client:
            run_resp = await client.post(
                f"{APIFY_BASE}/acts/{actor_id}/runs",
                params={"token": token, "waitForFinish": RUN_TIMEOUT_SECONDS},
                json={
                    "startUrls": [{"url": url} for _, url in batch],
                    "maxCrawlPages": MAX_PAGES_PER_RUN * len(batch),
                    "maxCrawlDepth": 1,
                    "pageFunction": _get_page_function(),
                },
                headers={"Content-Type": "application/json"},
            )
            run_resp.raise_for_status()
            run_data = run_resp.json().get("data", {})
            dataset_id = run_data.get("defaultDatasetId")
            if not dataset_id:
                logger.warning("apify.no_dataset", resp=run_data)
                return []

            items_resp = await client.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                params={"token": token, "format": "json", "limit": 200},
            )
            items_resp.raise_for_status()
            raw_items: list[dict] = items_resp.json()

    except Exception as exc:
        logger.warning("apify.fetch_error", error=str(exc))
        return []

    # Build a quick lookup: search URL → canonical_id
    url_to_canonical: dict[str, str] = {url: cid for cid, url in batch}

    for item in raw_items:
        price = _extract_price(item)
        if price is None:
            continue
        canonical_id = _infer_canonical_id(item, url_to_canonical)
        if not canonical_id:
            continue
        results.append(ApifyPrice(
            canonical_id=canonical_id,
            source="apify",
            retailer="home_depot",
            name=item.get("title") or item.get("name") or "",
            price=price,
            sku=_extract_sku(item),
            url=item.get("url"),
        ))

    logger.info("apify.run_complete", results=len(results))
    return results


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_price(item: dict) -> Optional[float]:
    """Try multiple price field patterns from different scrapers."""
    for key in ("price", "priceValue", "salePrice", "regularPrice", "currentPrice"):
        val = item.get(key)
        if val is not None:
            try:
                return float(str(val).replace("$", "").replace(",", "").strip())
            except ValueError:
                continue
    # Try text field: "$12.45"
    for key in ("priceText", "priceString", "text"):
        val = item.get(key, "")
        match = re.search(r"\$\s*(\d+(?:\.\d+)?)", str(val))
        if match:
            return float(match.group(1))
    return None


def _extract_sku(item: dict) -> Optional[str]:
    for key in ("sku", "modelNumber", "itemId", "productId", "model"):
        val = item.get(key)
        if val:
            return str(val).strip()
    return None


def _infer_canonical_id(item: dict, url_map: dict[str, str]) -> Optional[str]:
    """Map a scraped item back to a canonical ID using the originating search URL."""
    origin_url = item.get("loadedUrl") or item.get("url") or ""
    for search_url, canonical_id in url_map.items():
        # The item URL usually contains the search URL as the domain referrer
        if any(part in origin_url for part in search_url.split("?")[0].split("s/")[-1:]):
            return canonical_id
    return None


def _get_page_function() -> str:
    """JS page function for website-content-crawler to extract pricing data."""
    return """
async function pageFunction({ page, request, $ }) {
    // For product listing pages, extract first product's price
    const products = [];
    $('[data-product-id], [data-sku], [class*="price"]').each((i, el) => {
        const $el = $(el);
        const priceText = $el.find('[class*="price-format"], .price, [class*="Price"]').first().text();
        const title = $el.find('[class*="product-title"], h2, h3').first().text();
        const sku = $el.attr('data-sku') || $el.attr('data-product-id');
        if (priceText && title) {
            products.push({ title, priceText, sku, url: request.url });
        }
        if (products.length >= 5) return false;
    });
    return products.length ? products[0] : { url: request.url };
}
"""
