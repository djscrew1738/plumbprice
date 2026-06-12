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
from dataclasses import dataclass
from typing import Optional
import structlog

from app.config import settings

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

logger = structlog.get_logger()

APIFY_BASE = "https://api.apify.com/v2"
DEFAULT_ACTOR_ID = "apify/website-content-crawler"
MAX_PAGES_PER_RUN = 3
RUN_TIMEOUT_SECONDS = 120
URLS_PER_RUN = 6  # Max search pages per Apify run (free tier friendly)


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


# ─── Search URL templates ────────────────────────────────────────────────────
# Each tuple: (canonical_id, retailer, search_url)
# Coverage: ~50 top plumbing items across Home Depot and Lowe's

_RETAIL_SEARCH_URLS: list[tuple[str, str, str]] = [
    # ── Toilet ────────────────────────────────────────────────────────────────
    ("toilet.wax_ring", "home_depot", "https://www.homedepot.com/s/wax%20ring?NCNI-5"),
    ("toilet.wax_ring", "lowes", "https://www.lowes.com/search?searchTerm=wax+ring"),
    ("toilet.supply_line_12", "home_depot", "https://www.homedepot.com/s/toilet%20supply%20line%2012%20inch?NCNI-5"),
    ("toilet.supply_line_12", "lowes", "https://www.lowes.com/search?searchTerm=toilet+supply+line+12+inch"),
    ("toilet.closet_bolts", "home_depot", "https://www.homedepot.com/s/closet%20bolts%20toilet?NCNI-5"),
    ("toilet.closet_bolts", "lowes", "https://www.lowes.com/search?searchTerm=closet+bolts"),
    ("toilet.comfort_height_unit", "home_depot", "https://www.homedepot.com/s/comfort%20height%20toilet?NCNI-5"),
    ("toilet.comfort_height_unit", "lowes", "https://www.lowes.com/search?searchTerm=comfort+height+toilet"),
    ("toilet.seat_elongated_white", "home_depot", "https://www.homedepot.com/s/elongated%20toilet%20seat?NCNI-5"),
    ("toilet.seat_elongated_white", "lowes", "https://www.lowes.com/search?searchTerm=elongated+toilet+seat"),
    ("toilet.fill_valve_400a", "home_depot", "https://www.homedepot.com/s/fluidmaster%20400a?NCNI-5"),
    ("toilet.fill_valve_400a", "lowes", "https://www.lowes.com/search?searchTerm=fluidmaster+400a"),
    ("toilet.flapper_fluidmaster", "home_depot", "https://www.homedepot.com/s/toilet%20flapper?NCNI-5"),
    ("toilet.flapper_fluidmaster", "lowes", "https://www.lowes.com/search?searchTerm=toilet+flapper"),
    # ── Water Heater ──────────────────────────────────────────────────────────
    ("wh.50g_gas_unit", "home_depot", "https://www.homedepot.com/s/50%20gallon%20gas%20water%20heater?NCNI-5"),
    ("wh.50g_gas_unit", "lowes", "https://www.lowes.com/search?searchTerm=50+gallon+gas+water+heater"),
    ("wh.40g_gas_unit", "home_depot", "https://www.homedepot.com/s/40%20gallon%20gas%20water%20heater?NCNI-5"),
    ("wh.40g_gas_unit", "lowes", "https://www.lowes.com/search?searchTerm=40+gallon+gas+water+heater"),
    ("wh.50g_electric_unit", "home_depot", "https://www.homedepot.com/s/50%20gallon%20electric%20water%20heater?NCNI-5"),
    ("wh.50g_electric_unit", "lowes", "https://www.lowes.com/search?searchTerm=50+gallon+electric+water+heater"),
    ("wh.gas_flex_connector_18", "home_depot", "https://www.homedepot.com/s/gas%20flex%20connector%2018%20inch?NCNI-5"),
    ("wh.gas_flex_connector_18", "lowes", "https://www.lowes.com/search?searchTerm=gas+flex+connector+18+inch"),
    ("wh.expansion_tank_2g", "home_depot", "https://www.homedepot.com/s/thermal%20expansion%20tank%202%20gallon?NCNI-5"),
    ("wh.expansion_tank_2g", "lowes", "https://www.lowes.com/search?searchTerm=thermal+expansion+tank+2+gallon"),
    ("wh.tp_valve_075", "home_depot", "https://www.homedepot.com/s/tp%20relief%20valve%203%204?NCNI-5"),
    ("wh.tp_valve_075", "lowes", "https://www.lowes.com/search?searchTerm=tp+relief+valve+3/4"),
    ("wh.drain_pan_26", "home_depot", "https://www.homedepot.com/s/water%20heater%20drain%20pan%2026?NCNI-5"),
    ("wh.drain_pan_26", "lowes", "https://www.lowes.com/search?searchTerm=water+heater+drain+pan"),
    ("wh.tankless_navien_180k", "home_depot", "https://www.homedepot.com/s/tankless%20water%20heater?NCNI-5"),
    ("wh.tankless_navien_180k", "lowes", "https://www.lowes.com/search?searchTerm=tankless+water+heater"),
    ("wh.anode_rod_magnesium", "home_depot", "https://www.homedepot.com/s/anode%20rod%20water%20heater?NCNI-5"),
    ("wh.anode_rod_magnesium", "lowes", "https://www.lowes.com/search?searchTerm=anode+rod"),
    # ── Faucets ───────────────────────────────────────────────────────────────
    ("faucet.kitchen.pull_down", "home_depot", "https://www.homedepot.com/s/kitchen%20faucet%20pull%20down?NCNI-5"),
    ("faucet.kitchen.pull_down", "lowes", "https://www.lowes.com/search?searchTerm=kitchen+faucet+pull+down"),
    ("faucet.bathroom.single", "home_depot", "https://www.homedepot.com/s/bathroom%20faucet%20single%20handle?NCNI-5"),
    ("faucet.bathroom.single", "lowes", "https://www.lowes.com/search?searchTerm=bathroom+faucet+single+handle"),
    ("faucet.pot_filler_chrome", "home_depot", "https://www.homedepot.com/s/pot%20filler%20faucet?NCNI-5"),
    ("faucet.pot_filler_chrome", "lowes", "https://www.lowes.com/search?searchTerm=pot+filler+faucet"),
    ("faucet.touchless_kitchen", "home_depot", "https://www.homedepot.com/s/touchless%20kitchen%20faucet?NCNI-5"),
    ("faucet.touchless_kitchen", "lowes", "https://www.lowes.com/search?searchTerm=touchless+kitchen+faucet"),
    # ── Shower ────────────────────────────────────────────────────────────────
    ("shower.valve_pressure_balance", "home_depot", "https://www.homedepot.com/s/pressure%20balance%20shower%20valve?NCNI-5"),
    ("shower.valve_pressure_balance", "lowes", "https://www.lowes.com/search?searchTerm=pressure+balance+shower+valve"),
    ("shower.head_standard_chrome", "home_depot", "https://www.homedepot.com/s/shower%20head?NCNI-5"),
    ("shower.head_standard_chrome", "lowes", "https://www.lowes.com/search?searchTerm=shower+head"),
    ("shower.rain_head_12in", "home_depot", "https://www.homedepot.com/s/rain%20shower%20head?NCNI-5"),
    ("shower.rain_head_12in", "lowes", "https://www.lowes.com/search?searchTerm=rain+shower+head"),
    ("shower.trim_kit_brushed_nickel", "home_depot", "https://www.homedepot.com/s/shower%20trim%20kit%20brushed%20nickel?NCNI-5"),
    ("shower.trim_kit_brushed_nickel", "lowes", "https://www.lowes.com/search?searchTerm=shower+trim+kit+brushed+nickel"),
    # ── Disposal ──────────────────────────────────────────────────────────────
    ("disposal.drain_elbow_90", "home_depot", "https://www.homedepot.com/s/garbage%20disposal%20drain%20elbow?NCNI-5"),
    ("appliance.disposal_3_4hp", "home_depot", "https://www.homedepot.com/s/garbage%20disposal%203%2F4%20hp?NCNI-5"),
    ("appliance.disposal_3_4hp", "lowes", "https://www.lowes.com/search?searchTerm=garbage+disposal+3/4+hp"),
    ("disposal.mounting_ring_kit", "home_depot", "https://www.homedepot.com/s/garbage%20disposal%20mounting%20ring?NCNI-5"),
    # ── Sinks ─────────────────────────────────────────────────────────────────
    ("sink.undermount_ss_single", "home_depot", "https://www.homedepot.com/s/undermount%20stainless%20steel%20sink?NCNI-5"),
    ("sink.undermount_ss_single", "lowes", "https://www.lowes.com/search?searchTerm=undermount+stainless+steel+sink"),
    ("sink.pedestal_unit_white", "home_depot", "https://www.homedepot.com/s/pedestal%20sink?NCNI-5"),
    ("sink.pedestal_unit_white", "lowes", "https://www.lowes.com/search?searchTerm=pedestal+sink"),
    ("sink.bar_sink_ss_15", "home_depot", "https://www.homedepot.com/s/bar%20sink?NCNI-5"),
    ("sink.utility_tub_24", "home_depot", "https://www.homedepot.com/s/utility%20sink?NCNI-5"),
    ("sink.utility_tub_24", "lowes", "https://www.lowes.com/search?searchTerm=utility+sink"),
    # ── Tub / Tub-Spout ───────────────────────────────────────────────────────
    ("tub.drain_assembly_chrome", "home_depot", "https://www.homedepot.com/s/tub%20drain%20assembly?NCNI-5"),
    ("tub.drain_assembly_chrome", "lowes", "https://www.lowes.com/search?searchTerm=tub+drain+assembly"),
    ("tub_spout.diverter_chrome", "home_depot", "https://www.homedepot.com/s/tub%20spout%20diverter?NCNI-5"),
    ("tub_spout.diverter_chrome", "lowes", "https://www.lowes.com/search?searchTerm=tub+spout+diverter"),
    # ── Angle Stop / Supply ───────────────────────────────────────────────────
    ("angle_stop.quarter_turn_3_8", "home_depot", "https://www.homedepot.com/s/quarter%20turn%20angle%20stop?NCNI-5"),
    ("angle_stop.quarter_turn_3_8", "lowes", "https://www.lowes.com/search?searchTerm=quarter+turn+angle+stop"),
    ("plumbing.angle_stop_quarter_inch", "home_depot", "https://www.homedepot.com/s/angle%20stop%20valve?NCNI-5"),
    ("plumbing.angle_stop_quarter_inch", "lowes", "https://www.lowes.com/search?searchTerm=angle+stop+valve"),
    # ── PEX / Pipe ────────────────────────────────────────────────────────────
    ("pipe.pex_1in_per_ft", "home_depot", "https://www.homedepot.com/s/pex%20pipe%201%20inch?NCNI-5"),
    ("pipe.pex_1in_per_ft", "lowes", "https://www.lowes.com/search?searchTerm=pex+pipe+1+inch"),
    ("pipe.cpvc_3_4_per_ft", "home_depot", "https://www.homedepot.com/s/cpvc%20pipe%203%2F4?NCNI-5"),
    ("pipe.cpvc_3_4_per_ft", "lowes", "https://www.lowes.com/search?searchTerm=cpvc+pipe+3/4"),
    ("pipe.copper_coupling_propress_34", "home_depot", "https://www.homedepot.com/s/propress%20coupling%203%2F4?NCNI-5"),
    # ── PRV / Valves ──────────────────────────────────────────────────────────
    ("prv.watts_3_4", "home_depot", "https://www.homedepot.com/s/pressure%20reducing%20valve%203%2F4?NCNI-5"),
    ("prv.watts_3_4", "lowes", "https://www.lowes.com/search?searchTerm=pressure+reducing+valve+3/4"),
    ("valve.ball_3_4_full_port", "home_depot", "https://www.homedepot.com/s/ball%20valve%203%2F4%20full%20port?NCNI-5"),
    ("valve.ball_3_4_full_port", "lowes", "https://www.lowes.com/search?searchTerm=ball+valve+3/4+full+port"),
    ("valve.main_shutoff_1in_ball", "home_depot", "https://www.homedepot.com/s/main%20shutoff%20valve%201%20inch?NCNI-5"),
    ("valve.main_shutoff_1in_ball", "lowes", "https://www.lowes.com/search?searchTerm=main+shutoff+valve+1+inch"),
    # ── Sump Pump ─────────────────────────────────────────────────────────────
    ("pump.sump_1_3hp", "home_depot", "https://www.homedepot.com/s/sump%20pump%201%2F3%20hp?NCNI-5"),
    ("pump.sump_1_3hp", "lowes", "https://www.lowes.com/search?searchTerm=sump+pump+1/3+hp"),
    ("plumbing.sump_basin_18in", "home_depot", "https://www.homedepot.com/s/sump%20basin%2018%20inch?NCNI-5"),
    ("plumbing.sump_basin_18in", "lowes", "https://www.lowes.com/search?searchTerm=sump+basin+18+inch"),
    # ── Water Softener / Filter ───────────────────────────────────────────────
    ("softener.unit_48k_grain", "home_depot", "https://www.homedepot.com/s/water%20softener%2048%2C000%20grain?NCNI-5"),
    ("softener.unit_48k_grain", "lowes", "https://www.lowes.com/search?searchTerm=water+softener+48000+grain"),
    ("filter.sediment_whole_house_20in", "home_depot", "https://www.homedepot.com/s/whole%20house%20sediment%20filter?NCNI-5"),
    ("filter.sediment_whole_house_20in", "lowes", "https://www.lowes.com/search?searchTerm=whole+house+sediment+filter"),
    # ── Hose Bib / Outdoor ────────────────────────────────────────────────────
    ("hose_bib.frost_free_12", "home_depot", "https://www.homedepot.com/s/frost%20free%20hose%20bib?NCNI-5"),
    ("hose_bib.frost_free_12", "lowes", "https://www.lowes.com/search?searchTerm=frost+free+hose+bib"),
    ("outdoor.frost_free_sillcock_12in", "home_depot", "https://www.homedepot.com/s/frost%20free%20sillcock?NCNI-5"),
    # ── Misc / Common ─────────────────────────────────────────────────────────
    ("kitchen.basket_strainer", "home_depot", "https://www.homedepot.com/s/kitchen%20sink%20basket%20strainer?NCNI-5"),
    ("kitchen.basket_strainer", "lowes", "https://www.lowes.com/search?searchTerm=kitchen+sink+basket+strainer"),
    ("plumbing.teflon_tape", "home_depot", "https://www.homedepot.com/s/plumber%20teflon%20tape?NCNI-5"),
    ("plumbing.teflon_tape", "lowes", "https://www.lowes.com/search?searchTerm=plumber+teflon+tape"),
    ("gas.teflon_tape_yellow", "home_depot", "https://www.homedepot.com/s/yellow%20gas%20teflon%20tape?NCNI-5"),
    ("gas.teflon_tape_yellow", "lowes", "https://www.lowes.com/search?searchTerm=yellow+gas+teflon+tape"),
    ("lav.pop_up_drain", "home_depot", "https://www.homedepot.com/s/pop%20up%20drain?NCNI-5"),
    ("lav.pop_up_drain", "lowes", "https://www.lowes.com/search?searchTerm=pop+up+drain"),
    ("ptrap.chrome_1_5_inch", "home_depot", "https://www.homedepot.com/s/chrome%20p%20trap?NCNI-5"),
    ("ptrap.chrome_1_5_inch", "lowes", "https://www.lowes.com/search?searchTerm=chrome+p+trap"),
]


def _get_retail_urls(canonical_ids: list[str] | None = None) -> list[tuple[str, str, str]]:
    """Return filtered retail URL tuples for the given canonical IDs (or all)."""
    if canonical_ids:
        cid_set = set(canonical_ids)
        return [t for t in _RETAIL_SEARCH_URLS if t[0] in cid_set]
    return list(_RETAIL_SEARCH_URLS)


async def fetch_prices(
    token: str | None = None,
    actor_id: str = DEFAULT_ACTOR_ID,
    canonical_ids: list[str] | None = None,
) -> list[ApifyPrice]:
    """
    Run Apify actor to scrape plumbing product prices from Home Depot and Lowe's.
    Returns list of ApifyPrice objects for matched canonical items.
    Falls back to empty list on any error (non-blocking).

    Args:
        token: Apify API token. Defaults to settings.apify_token.
        actor_id: Apify actor ID. Defaults to settings.apify_actor_id.
        canonical_ids: Optional filter — only fetch prices for these canonical IDs.
    """
    if not _HTTPX_AVAILABLE:
        logger.warning("apify.httpx_missing")
        return []

    token = token or settings.apify_token
    actor_id = actor_id or settings.apify_actor_id or DEFAULT_ACTOR_ID
    if not token:
        logger.debug("apify.no_token")
        return []

    target_urls = _get_retail_urls(canonical_ids)
    if not target_urls:
        return []

    results: list[ApifyPrice] = []

    # Process in batches of URLS_PER_RUN
    for batch_start in range(0, len(target_urls), URLS_PER_RUN):
        batch = target_urls[batch_start : batch_start + URLS_PER_RUN]
        batch_results = await _run_apify_batch(token, actor_id, batch)
        results.extend(batch_results)

    logger.info("apify.fetch_complete", total_results=len(results), runs=(len(target_urls) + URLS_PER_RUN - 1) // URLS_PER_RUN)
    return results


async def _run_apify_batch(
    token: str,
    actor_id: str,
    batch: list[tuple[str, str, str]],
) -> list[ApifyPrice]:
    """Run a single Apify batch and parse results."""
    logger.info("apify.run_start", actor=actor_id, urls=len(batch))

    try:
        async with httpx.AsyncClient(timeout=RUN_TIMEOUT_SECONDS + 30) as client:
            run_resp = await client.post(
                f"{APIFY_BASE}/acts/{actor_id}/runs",
                params={"token": token, "waitForFinish": RUN_TIMEOUT_SECONDS},
                json={
                    "startUrls": [{"url": url} for _, _, url in batch],
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
        logger.warning("apify.batch_error", error=str(exc))
        return []

    # Build lookup: search URL → (canonical_id, retailer)
    url_to_meta: dict[str, tuple[str, str]] = {url: (cid, retailer) for cid, retailer, url in batch}

    results: list[ApifyPrice] = []
    for item in raw_items:
        price = _extract_price(item)
        if price is None:
            continue
        canonical_id, retailer = _infer_meta(item, url_to_meta)
        if not canonical_id:
            continue
        results.append(ApifyPrice(
            canonical_id=canonical_id,
            source="apify",
            retailer=retailer,
            name=item.get("title") or item.get("name") or "",
            price=price,
            sku=_extract_sku(item),
            url=item.get("url"),
        ))

    logger.info("apify.run_complete", results=len(results), urls=len(batch))
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


def _infer_meta(
    item: dict,
    url_map: dict[str, tuple[str, str]],
) -> tuple[Optional[str], str]:
    """Map a scraped item back to canonical_id and retailer using the originating search URL."""
    origin_url = item.get("loadedUrl") or item.get("url") or ""
    # Direct match on exact URL
    if origin_url in url_map:
        return url_map[origin_url]
    # Fuzzy match: check if the item URL contains key parts of any search URL
    for search_url, (canonical_id, retailer) in url_map.items():
        search_path = search_url.split("?")[0].split("/s/")[-1]
        if search_path and search_path in origin_url:
            return canonical_id, retailer
    return None, ""


def _get_page_function() -> str:
    """JS page function for website-content-crawler to extract pricing data."""
    return """
async function pageFunction({ page, request, $ }) {
    const products = [];
    $('[data-product-id], [data-sku], [class*="price"], [class*="Product"]').each((i, el) => {
        const $el = $(el);
        const priceText = $el.find('[class*="price-format"], .price, [class*="Price"], [class*="price"]').first().text();
        const title = $el.find('[class*="product-title"], h2, h3, [class*="title"]').first().text();
        const sku = $el.attr('data-sku') || $el.attr('data-product-id') || $el.attr('data-item-id');
        if (priceText && title) {
            products.push({ title, priceText, sku, url: request.url });
        }
        if (products.length >= 5) return false;
    });
    return products.length ? products[0] : { url: request.url };
}
"""
