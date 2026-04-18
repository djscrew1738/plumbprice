"""Celery task: Refresh supplier prices daily."""

from worker.worker import app
import structlog
import httpx
import random
import os
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, or_, func
from app.database import AsyncSessionLocal
from app.models.suppliers import SupplierProduct
from app.services.data_sources.suppliers.service import get_scraper_service
from app.services.supplier_service import CANONICAL_MAP

logger = structlog.get_logger()

DATABASE_URL = os.getenv("DATABASE_URL", "")


async def _async_decrement_confidence_scores():
    """Internal async implementation of confidence decrement."""
    async with AsyncSessionLocal() as db:
        try:
            # Stale if last_verified is > 7 days ago
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Find products that are stale and still have some confidence left
            query = (
                select(SupplierProduct)
                .where(
                    or_(
                        SupplierProduct.last_verified < seven_days_ago,
                        SupplierProduct.last_verified.is_(None)
                    ),
                    SupplierProduct.confidence_score > 0
                )
            )
            
            result = await db.execute(query)
            stale_products = result.scalars().all()
            
            if not stale_products:
                logger.info("No stale products found for confidence decrement")
                return 0

            count = 0
            for product in stale_products:
                new_score = max(0.0, product.confidence_score - 0.05)
                product.confidence_score = new_score
                count += 1
            
            await db.commit()
            logger.info("Decremented confidence scores", updated_count=count)
            return count
        except Exception as e:
            await db.rollback()
            logger.error("Failed to decrement confidence scores", error=str(e))
            raise


@app.task
def decrement_confidence_scores():
    """
    Decrement confidence scores on stale prices.
    Run daily. Products not updated in 7+ days lose 0.05 confidence/day.
    """
    logger.info("Starting stale confidence score decrement")
    count = asyncio.run(_async_decrement_confidence_scores())
    return {"status": "complete", "updated_count": count}


async def _async_refresh_all_suppliers():
    """Internal async implementation of global refresh."""
    async with AsyncSessionLocal() as db:
        # Get all canonical IDs from the map
        canonical_ids = list(CANONICAL_MAP.keys())
        
        # Use simulation mode if not in production or if no API keys present
        simulation = os.getenv("ENVIRONMENT") != "production" or not os.getenv("APIFY_TOKEN")
        scraper_service = get_scraper_service(simulation_mode=simulation)
        
        stats = await scraper_service.refresh_all(db, canonical_ids)
        return stats


@app.task(bind=True, max_retries=3)
def refresh_all_suppliers(self):
    """
    Refresh prices for all active suppliers.
    Phase 2 implementation: Uses SupplierScraperService.
    """
    logger.info("Starting global supplier price refresh")

    try:
        results = asyncio.run(_async_refresh_all_suppliers())
        
        # Trigger confidence score decrement as part of the daily cycle
        decrement_confidence_scores.delay()

        logger.info("Supplier refresh complete", results=results)
        return {"status": "complete", "suppliers": results}

    except Exception as exc:
        logger.error("Supplier refresh failed", error=str(exc), exc_info=True)
        backoff = min(300 * (2 ** self.request.retries) + random.uniform(0, 60), 3600)
        raise self.retry(exc=exc, countdown=backoff)


async def _async_refresh_supplier(supplier_slug: str):
    """Internal async implementation of single supplier refresh."""
    async with AsyncSessionLocal() as db:
        canonical_ids = list(CANONICAL_MAP.keys())
        simulation = os.getenv("ENVIRONMENT") != "production" or not os.getenv("APIFY_TOKEN")
        scraper_service = get_scraper_service(simulation_mode=simulation)
        
        count = await scraper_service.refresh_supplier(db, supplier_slug, canonical_items=canonical_ids)
        return count


@app.task
def refresh_supplier(supplier_slug: str):
    """Refresh prices for a single supplier."""
    logger.info(f"Refreshing single supplier: {supplier_slug}")
    count = asyncio.run(_async_refresh_supplier(supplier_slug))
    return {"supplier": supplier_slug, "status": "complete", "updated_count": count}
