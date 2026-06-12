"""Hourly price feed sync task.

Runs all registered price feed adapters, updates supplier_products in the DB,
and writes price history entries for significant changes.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select

logger = structlog.get_logger()

# Register adapters on module load
from app.services.price_feed_adapter import registry
from app.services.price_feeds.ferguson_adapter import FergusonAdapter
from app.services.price_feeds.retail_benchmark_adapter import RetailBenchmarkAdapter
from app.services.price_feeds.kohler_scraper import KohlerScraper
from app.services.price_feeds.moen_scraper import MoenScraper
from app.services.price_feeds.ao_smith_scraper import AOSmithScraper

registry.register(FergusonAdapter())
registry.register(RetailBenchmarkAdapter())
registry.register(KohlerScraper())
registry.register(MoenScraper())
registry.register(AOSmithScraper())


@shared_task(name="worker.tasks.price_feed_sync.run_sync")
def run_price_feed_sync() -> dict:
    """Celery task: sync all price feeds and update the database.

    Returns a summary dict with adapter results.
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_async_sync())


async def _async_sync() -> dict:
    from app.database import AsyncSessionLocal
    from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory

    summary: dict[str, dict] = {}

    async with AsyncSessionLocal() as session:
        # Get all active canonical items
        result = await session.execute(
            select(SupplierProduct.canonical_item).distinct()
            .where(SupplierProduct.is_active == True)
        )
        canonical_items = [r[0] for r in result.all()]

        if not canonical_items:
            logger.warning("price_feed_sync.no_items")
            return {"status": "skipped", "reason": "no_active_items"}

        logger.info("price_feed_sync.start", items=len(canonical_items))

        # Run all adapters
        all_results = await registry.run_all(canonical_items)

        for adapter_name, results in all_results.items():
            updated = 0
            created_history = 0
            errors = 0

            for feed_result in results:
                try:
                    # Find matching supplier product
                    # Manufacturer feeds don't map 1:1 to supplier slug,
                    # so we update the product with matching canonical_item
                    # and manufacturer field
                    stmt = select(SupplierProduct).where(
                        SupplierProduct.canonical_item == feed_result.canonical_item,
                        SupplierProduct.is_active == True,
                    )
                    prod_result = await session.execute(stmt)
                    products = prod_result.scalars().all()

                    for product in products:
                        old_cost = product.cost
                        product.cost = feed_result.cost
                        product.msrp = feed_result.msrp
                        product.last_verified = feed_result.scraped_at
                        product.confidence_score = feed_result.confidence
                        if feed_result.in_stock is not None:
                            product.in_stock = feed_result.in_stock
                        if feed_result.lead_time:
                            product.lead_time = feed_result.lead_time

                        # Record price history if change > 1%
                        if abs(old_cost - feed_result.cost) / max(old_cost, 0.01) > 0.01:
                            session.add(SupplierPriceHistory(
                                product_id=product.id,
                                cost=feed_result.cost,
                                source=adapter_name,
                            ))
                            created_history += 1
                        updated += 1

                except Exception as exc:
                    logger.error(
                        "price_feed_sync.update_error",
                        adapter=adapter_name,
                        item=feed_result.canonical_item,
                        error=str(exc),
                    )
                    errors += 1

            summary[adapter_name] = {
                "fetched": len(results),
                "updated": updated,
                "history_entries": created_history,
                "errors": errors,
            }

        await session.commit()

    # Collect health stats
    health_map = await registry.health_all()
    for name, health in health_map.items():
        summary[name]["health"] = health.status

    logger.info("price_feed_sync.complete", summary=summary)
    return {"status": "success", "adapters": summary}
