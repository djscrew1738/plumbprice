"""Celery task: Refresh supplier prices daily."""

from worker.worker import app
import structlog
import httpx
import os

logger = structlog.get_logger()

DATABASE_URL = os.getenv("DATABASE_URL", "")


@app.task(bind=True, max_retries=3)
def refresh_all_suppliers(self):
    """
    Refresh prices for all active suppliers.
    Phase 2: Implement web scraping or API calls per supplier.
    For now: logs that refresh was triggered and decrements confidence scores.
    """
    logger.info("Starting supplier price refresh")

    try:
        # Phase 2: implement per-supplier scraping
        # For now, log the task is running
        suppliers = ["ferguson", "moore_supply", "apex"]
        results = {}

        for supplier in suppliers:
            logger.info(f"Refreshing prices for {supplier}")
            # TODO Phase 2: Call supplier API or scrape prices
            results[supplier] = {"status": "pending", "items_updated": 0}

        logger.info("Supplier refresh complete", results=results)
        return {"status": "complete", "suppliers": results}

    except Exception as exc:
        logger.error("Supplier refresh failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@app.task
def refresh_supplier(supplier_slug: str):
    """Refresh prices for a single supplier."""
    logger.info(f"Refreshing single supplier: {supplier_slug}")
    # TODO Phase 2: implement per-supplier logic
    return {"supplier": supplier_slug, "status": "pending"}


@app.task
def decrement_confidence_scores():
    """
    Decrement confidence scores on stale prices.
    Run daily. Products not updated in 7+ days lose 0.05 confidence/day.
    """
    logger.info("Decrementing stale confidence scores")
    # TODO: query DB, find stale products, reduce confidence_score
    return {"status": "complete"}
