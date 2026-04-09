"""
Price Enrichment Service — unified fallback chain for plumbing material costs.

Resolution order per canonical item:
  1. In-memory TTL cache          (populated from tiers below)
  2. Apify Platform               (live retail prices — requires APIFY_TOKEN)
  3. ConstructDataAPI             (self-hosted construction data — requires CONSTRUCT_API_URL)
  4. DDC CWICR reference          (static 2025 Q2 DFW plumbing reference costs)
  5. CANONICAL_MAP                (original hardcoded wholesale prices — always available)

Cache TTL: 24 hours by default (PRICE_CACHE_TTL_HOURS env var).
Background refresh: call `refresh()` on startup / scheduled task.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Optional
import structlog

from app.services.data_sources import cwicr_reference
from app.services.data_sources import apify_source
from app.services.data_sources import construct_api_adapter

logger = structlog.get_logger()

# ─── Configuration from env ───────────────────────────────────────────────────
_APIFY_TOKEN       = os.getenv("APIFY_TOKEN", "")
_APIFY_ACTOR_ID    = os.getenv("APIFY_ACTOR_ID", apify_source.DEFAULT_ACTOR_ID)
_CONSTRUCT_API_URL = os.getenv("CONSTRUCT_API_URL", "")
_CACHE_TTL_SECS    = int(os.getenv("PRICE_CACHE_TTL_HOURS", "24")) * 3600


@dataclass
class EnrichedPrice:
    canonical_id: str
    unit_cost: float
    source: str          # "apify" | "construct_api" | "cwicr" | "canonical_map"
    retailer: str = ""
    name: str = ""
    sku: Optional[str] = None
    fetched_at: float = field(default_factory=time.monotonic)

    def is_stale(self) -> bool:
        return (time.monotonic() - self.fetched_at) > _CACHE_TTL_SECS


class PriceEnrichmentService:
    """
    Thread-safe singleton service that enriches canonical item prices from
    multiple external data sources with in-memory TTL caching.
    """

    def __init__(self) -> None:
        self._cache: dict[str, EnrichedPrice] = {}
        self._lock = asyncio.Lock()
        self._last_refresh: float = 0.0

    # ─── Public API ───────────────────────────────────────────────────────────

    async def get_price(
        self,
        canonical_id: str,
        fallback_cost: Optional[float] = None,
    ) -> Optional[EnrichedPrice]:
        """
        Return the best available price for a canonical item.
        Checks cache first; if stale/missing, attempts live lookup.
        Falls back to CWICR reference, then to fallback_cost.
        """
        cached = self._cache.get(canonical_id)
        if cached and not cached.is_stale():
            return cached

        # Try each tier in order
        price = await self._lookup_apify(canonical_id)
        if price is None:
            price = await self._lookup_construct_api(canonical_id)
        if price is None:
            price = self._lookup_cwicr(canonical_id)
        if price is None and fallback_cost is not None:
            price = EnrichedPrice(
                canonical_id=canonical_id,
                unit_cost=fallback_cost,
                source="canonical_map",
            )

        if price is not None:
            self._cache[canonical_id] = price

        return price

    async def refresh(self, canonical_ids: Optional[list[str]] = None) -> dict[str, float]:
        """
        Eagerly refresh prices for the given canonical IDs (or all known ones).
        Returns a dict of {canonical_id: unit_cost} for refreshed items.
        Called on API startup and periodically by a background task.
        """
        async with self._lock:
            if canonical_ids is None:
                canonical_ids = cwicr_reference.all_canonical_ids()

            results: dict[str, float] = {}

            # Tier 2: Apify (batched run for all requested items)
            apify_prices = await self._fetch_apify_batch(canonical_ids)
            for p in apify_prices:
                self._cache[p.canonical_id] = p
                results[p.canonical_id] = p.unit_cost

            # Tier 3: ConstructDataAPI (fills gaps left by Apify)
            missing = [cid for cid in canonical_ids if cid not in results]
            construct_prices = await self._fetch_construct_batch(missing)
            for p in construct_prices:
                self._cache[p.canonical_id] = EnrichedPrice(
                    canonical_id=p.canonical_id,
                    unit_cost=p.unit_cost,
                    source="construct_api",
                    name=p.name,
                )
                results[p.canonical_id] = p.unit_cost

            # Tier 4: CWICR fills any remaining gaps
            still_missing = [cid for cid in canonical_ids if cid not in results]
            for cid in still_missing:
                cwicr = cwicr_reference.lookup(cid)
                if cwicr:
                    enriched = EnrichedPrice(
                        canonical_id=cid,
                        unit_cost=cwicr.unit_cost_usd,
                        source="cwicr",
                        name=cwicr.name,
                    )
                    self._cache[cid] = enriched
                    results[cid] = cwicr.unit_cost_usd

            self._last_refresh = time.monotonic()
            logger.info(
                "price_enrichment.refresh_done",
                total=len(canonical_ids),
                enriched=len(results),
                apify=len(apify_prices),
                construct=len(construct_prices),
                cwicr=len(still_missing),
            )
            return results

    def get_cached_cost(self, canonical_id: str) -> Optional[float]:
        """Synchronous cache-only lookup — zero latency, used in hot path."""
        entry = self._cache.get(canonical_id)
        if entry and not entry.is_stale():
            return entry.unit_cost
        return None

    def cache_stats(self) -> dict:
        total = len(self._cache)
        fresh = sum(1 for e in self._cache.values() if not e.is_stale())
        by_source: dict[str, int] = {}
        for e in self._cache.values():
            by_source[e.source] = by_source.get(e.source, 0) + 1
        return {
            "total": total,
            "fresh": fresh,
            "stale": total - fresh,
            "by_source": by_source,
            "last_refresh_ago_s": int(time.monotonic() - self._last_refresh) if self._last_refresh else None,
        }

    # ─── Internal per-tier lookups ────────────────────────────────────────────

    async def _lookup_apify(self, canonical_id: str) -> Optional[EnrichedPrice]:
        if not _APIFY_TOKEN:
            return None
        cached = self._cache.get(canonical_id)
        if cached and cached.source == "apify" and not cached.is_stale():
            return cached
        # Run a targeted single-item fetch
        try:
            prices = await apify_source.fetch_prices(
                token=_APIFY_TOKEN,
                actor_id=_APIFY_ACTOR_ID,
                canonical_ids=[canonical_id],
            )
            for p in prices:
                if p.canonical_id == canonical_id:
                    return EnrichedPrice(
                        canonical_id=canonical_id,
                        unit_cost=p.price,
                        source="apify",
                        retailer=p.retailer,
                        name=p.name,
                        sku=p.sku,
                    )
        except Exception as exc:
            logger.warning("price_enrichment.apify_error", error=str(exc))
        return None

    async def _lookup_construct_api(self, canonical_id: str) -> Optional[EnrichedPrice]:
        if not _CONSTRUCT_API_URL:
            return None
        try:
            prices = await construct_api_adapter.fetch_prices(_CONSTRUCT_API_URL)
            for p in prices:
                if p.canonical_id == canonical_id:
                    return EnrichedPrice(
                        canonical_id=canonical_id,
                        unit_cost=p.unit_cost,
                        source="construct_api",
                        name=p.name,
                    )
        except Exception as exc:
            logger.warning("price_enrichment.construct_api_error", error=str(exc))
        return None

    def _lookup_cwicr(self, canonical_id: str) -> Optional[EnrichedPrice]:
        item = cwicr_reference.lookup(canonical_id)
        if item:
            return EnrichedPrice(
                canonical_id=canonical_id,
                unit_cost=item.unit_cost_usd,
                source="cwicr",
                name=item.name,
            )
        return None

    async def _fetch_apify_batch(self, canonical_ids: list[str]) -> list[apify_source.ApifyPrice]:
        if not _APIFY_TOKEN or not canonical_ids:
            return []
        try:
            return await apify_source.fetch_prices(
                token=_APIFY_TOKEN,
                actor_id=_APIFY_ACTOR_ID,
                canonical_ids=canonical_ids,
            )
        except Exception as exc:
            logger.warning("price_enrichment.apify_batch_error", error=str(exc))
            return []

    async def _fetch_construct_batch(
        self, canonical_ids: list[str]
    ) -> list[construct_api_adapter.ConstructAPIPrice]:
        if not _CONSTRUCT_API_URL or not canonical_ids:
            return []
        try:
            all_prices = await construct_api_adapter.fetch_prices(_CONSTRUCT_API_URL)
            return [p for p in all_prices if p.canonical_id in canonical_ids]
        except Exception as exc:
            logger.warning("price_enrichment.construct_batch_error", error=str(exc))
            return []


# ─── Singleton ────────────────────────────────────────────────────────────────
_enrichment_service: Optional[PriceEnrichmentService] = None


def get_enrichment_service() -> PriceEnrichmentService:
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = PriceEnrichmentService()
    return _enrichment_service
