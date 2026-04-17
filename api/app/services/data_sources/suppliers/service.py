import asyncio
import structlog
from typing import List, Dict, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from . import FergusonScraper, MooreScraper, ApexScraper, ScrapedProduct

logger = structlog.get_logger()

class SupplierScraperService:
    def __init__(self, simulation_mode: bool = True):
        self.scrapers = {
            "ferguson": FergusonScraper(simulation_mode),
            "moore_supply": MooreScraper(simulation_mode),
            "apex": ApexScraper(simulation_mode),
        }

    async def refresh_all(self, db: AsyncSession, canonical_items: List[str]) -> Dict[str, int]:
        """Refresh prices for all suppliers and all given canonical items."""
        stats = {}
        for slug, scraper in self.scrapers.items():
            count = await self.refresh_supplier(db, slug, canonical_items)
            stats[slug] = count
        return stats

    async def refresh_supplier(self, db: AsyncSession, supplier_slug: str, canonical_items: List[str]) -> int:
        """Refresh prices for a specific supplier."""
        scraper = self.scrapers.get(supplier_slug)
        if not scraper:
            logger.warning("scraper.not_found", supplier=supplier_slug)
            return 0

        logger.info("scraper.refresh_start", supplier=supplier_slug, items=len(canonical_items))
        
        # Get the supplier ID from the DB
        result = await db.execute(select(Supplier).where(Supplier.slug == supplier_slug))
        supplier = result.scalar_one_or_none()
        if not supplier:
            logger.error("scraper.supplier_not_found_in_db", supplier=supplier_slug)
            return 0

        scraped_products = await scraper.fetch_prices(canonical_items)
        updated_count = 0

        for scraped in scraped_products:
            # Find existing product or create new
            query = select(SupplierProduct).where(
                and_(
                    SupplierProduct.supplier_id == supplier.id,
                    SupplierProduct.canonical_item == scraped.canonical_item
                )
            )
            result = await db.execute(query)
            product = result.scalar_one_or_none()

            if product:
                # Update existing product if cost changed
                old_cost = product.cost
                if abs(old_cost - scraped.cost) > 0.001:
                    product.cost = scraped.cost
                    # Add to history
                    db.add(SupplierPriceHistory(
                        product_id=product.id,
                        cost=scraped.cost,
                        source=f"scraper:{scraper.supplier_slug}"
                    ))
                
                product.last_verified = scraped.scraped_at
                product.confidence_score = 1.0  # Reset confidence on success
                updated_count += 1
            else:
                # Create new product entry
                new_product = SupplierProduct(
                    supplier_id=supplier.id,
                    canonical_item=scraped.canonical_item,
                    sku=scraped.sku,
                    name=scraped.name,
                    cost=scraped.cost,
                    last_verified=scraped.scraped_at,
                    confidence_score=1.0,
                    is_active=True
                )
                db.add(new_product)
                await db.flush() # Get ID for history
                
                db.add(SupplierPriceHistory(
                    product_id=new_product.id,
                    cost=scraped.cost,
                    source=f"scraper:{scraper.supplier_slug}"
                ))
                updated_count += 1

        await db.commit()
        logger.info("scraper.refresh_complete", supplier=supplier_slug, updated=updated_count)
        return updated_count

# Global singleton
_scraper_service = None

def get_scraper_service(simulation_mode: bool = True) -> SupplierScraperService:
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = SupplierScraperService(simulation_mode)
    return _scraper_service
