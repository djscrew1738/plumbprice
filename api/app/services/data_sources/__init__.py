"""
Data Sources — External pricing integrations for the PlumbPrice engine.

Fallback chain (highest → lowest priority):
  1. In-memory TTL cache (populated by tiers below)
  2. Apify Platform  — live Home Depot / Lowe's scraped prices (requires APIFY_TOKEN)
  3. ConstructDataAPI — self-hosted Node.js construction data API (requires CONSTRUCT_API_URL)
  4. DDC CWICR        — static reference data embedded in code (always available)
  5. CANONICAL_MAP    — original hardcoded DFW wholesale prices (final fallback)
"""

from .price_enrichment import PriceEnrichmentService, get_enrichment_service

__all__ = ["PriceEnrichmentService", "get_enrichment_service"]
