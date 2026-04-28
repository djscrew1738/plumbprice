from sqlalchemy.future import select
from app.models.pricing_rules import PermitCostRule, CityZoneMultiplier, TripChargeRule
from app.models.labor import MarkupRule
from app.models.tax import TaxRate
from app.database import AsyncSessionLocal
from app.services.pricing_defaults import (
    TAX_RATES, TRIP_CHARGES, MARKUP_RULES,
    PERMIT_COSTS, CITY_ZONE_MULTIPLIERS
)
import structlog
from typing import Optional, Dict

logger = structlog.get_logger()


class PricingConfigService:
    def __init__(self):
        # In-memory caches for high-frequency lookups
        self._tax_rates: Dict[str, float] = dict(TAX_RATES)
        self._trip_charges: Dict[str, float] = dict(TRIP_CHARGES)
        self._zone_multipliers: Dict[str, float] = dict(CITY_ZONE_MULTIPLIERS)
        self._permit_costs: Dict[str, Dict[str, float]] = dict(PERMIT_COSTS)
        self._markup_rules: Dict[str, Dict] = dict(MARKUP_RULES)

    async def refresh_cache(self):
        """Reload all pricing rules from DB into memory."""
        try:
            async with AsyncSessionLocal() as db:
                # Load Tax Rates
                tax_result = await db.execute(select(TaxRate).where(TaxRate.is_active == True))
                tax_rates = {r.county.lower(): r.rate for r in tax_result.scalars().all()}
                if tax_rates:
                    self._tax_rates = tax_rates

                # Load Trip Charges
                trip_result = await db.execute(select(TripChargeRule).where(TripChargeRule.is_active == True))
                trip_charges = {r.county.lower(): r.charge for r in trip_result.scalars().all()}
                if trip_charges:
                    self._trip_charges = trip_charges

                # Load Zone Multipliers
                zone_result = await db.execute(select(CityZoneMultiplier).where(CityZoneMultiplier.is_active == True))
                zone_multipliers = {r.city.lower(): r.multiplier for r in zone_result.scalars().all()}
                if zone_multipliers:
                    self._zone_multipliers = zone_multipliers

                # Load Permit Costs
                permit_result = await db.execute(select(PermitCostRule).where(PermitCostRule.is_active == True))
                permit_costs = {}
                for r in permit_result.scalars().all():
                    county = r.county.lower()
                    if county not in permit_costs:
                        permit_costs[county] = {}
                    permit_costs[county][r.job_category] = r.cost
                if permit_costs:
                    self._permit_costs = permit_costs

                # Load Markup Rules
                markup_result = await db.execute(select(MarkupRule).where(MarkupRule.is_active == True))
                markup_rules = {
                    r.job_type: {
                        "labor_markup_pct": r.labor_markup_pct,
                        "materials_markup_pct": r.materials_markup_pct,
                        "misc_flat": r.misc_flat
                    } for r in markup_result.scalars().all()
                }
                if markup_rules:
                    self._markup_rules = markup_rules

            logger.info("Pricing cache refreshed",
                        tax_count=len(self._tax_rates),
                        trip_count=len(self._trip_charges),
                        zone_count=len(self._zone_multipliers),
                        permit_count=len(self._permit_costs),
                        markup_count=len(self._markup_rules))
        except Exception as e:
            logger.error("Failed to refresh pricing cache", error=str(e))

    def get_tax_rate(self, county: str) -> float:
        return self._tax_rates.get(county.lower(), 0.0825)

    def get_trip_charge(self, county: str) -> float:
        return self._trip_charges.get(county.lower(), 105.0)

    def get_city_multiplier(self, city: Optional[str]) -> float:
        if not city:
            return 1.0
        return self._zone_multipliers.get(city.strip().lower(), 1.0)

    def get_permit_cost(self, county: str, job_category: str) -> float:
        county_rules = self._permit_costs.get(county.lower(), self._permit_costs.get("dallas", {}))
        # Fallback order: specific category -> "default" -> hardcoded baseline 85.0
        return county_rules.get(job_category, county_rules.get("default", 85.0))

    def get_markup_rule(self, job_type: str) -> Dict:
        return self._markup_rules.get(job_type, MARKUP_RULES.get("service"))


pricing_config_service = PricingConfigService()
