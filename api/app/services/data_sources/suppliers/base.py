from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timezone

@dataclass
class ScrapedProduct:
    canonical_item: str
    sku: str
    name: str
    cost: float
    currency: str = "USD"
    scraped_at: datetime = datetime.now(timezone.utc)
    source_url: Optional[str] = None

class SupplierScraper(ABC):
    def __init__(self, supplier_slug: str):
        self.supplier_slug = supplier_slug

    @abstractmethod
    async def fetch_prices(self, canonical_items: List[str]) -> List[ScrapedProduct]:
        """Fetch prices for a list of canonical items from the supplier."""
        pass
