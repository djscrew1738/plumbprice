"""
Pricing Engine — Deterministic plumbing price calculator.
RULE: No LLM in the calculation path. Every dollar is traceable.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import structlog

from app.services.labor_engine import (
    LABOR_TEMPLATES, LaborTemplateData, get_template,
    AccessType, UrgencyType
)
from app.services.pricing_config_service import pricing_config_service

logger = structlog.get_logger()


class County(str, Enum):
    DALLAS = "Dallas"
    TARRANT = "Tarrant"
    COLLIN = "Collin"
    DENTON = "Denton"
    ROCKWALL = "Rockwall"
    PARKER = "Parker"
    KAUFMAN = "Kaufman"
    ELLIS = "Ellis"
    JOHNSON = "Johnson"


# Texas combined sales tax rates (state 6.25% + max local 2%).
# Source: Texas Comptroller of Public Accounts, 2025 Q1.
# Managed by pricing_config_service.

# ─── Permit cost schedule ─────────────────────────────────────────────────────
# Managed by pricing_config_service.

# Labor templates that require a permit (mapped to permit category key)
_PERMIT_REQUIRED: dict[str, str] = {
    "WH_50G_GAS_STANDARD":      "water_heater",
    "WH_50G_GAS_ATTIC":         "water_heater",
    "WH_40G_GAS_STANDARD":      "water_heater",
    "WH_50G_ELECTRIC_STANDARD": "water_heater",
    "WH_TANKLESS_GAS":          "water_heater",
    "GAS_LINE_NEW_RUN":         "gas",
    "GAS_LINE_REPAIR_MINOR":    "gas",
    "GAS_SHUTOFF_REPLACE":      "gas",
    "GAS_PRESSURE_TEST":        "gas",
    "WHOLE_HOUSE_REPIPE_PEX":   "repipe",
    "SLAB_LEAK_REROUTE":        "repipe",
    "SEWER_SPOT_REPAIR":        "sewer",
    "CLEAN_OUT_INSTALL":        "sewer",
    "BACKFLOW_PREVENTER_INSTALL": "backflow",
    "BACKFLOW_TEST_ANNUAL":     "backflow",
    # ── DFW expansion: new permit-required templates ──
    "WH_50G_ELECTRIC_ATTIC":        "water_heater",
    "WH_TANKLESS_ELECTRIC":         "water_heater",
    "WH_HYBRID_HEAT_PUMP":          "water_heater",
    "COMMERCIAL_WATER_HEATER_INSTALL": "water_heater",
    "GAS_LINE_DRYER":               "gas",
    "GAS_LINE_RANGE_OVEN":          "gas",
    "GAS_LINE_FIREPLACE":           "gas",
    "GAS_LINE_GRILL_OUTDOOR":       "gas",
    "SEWER_LINER_CIPP":             "sewer",
    "SEWER_BELLY_REPAIR":           "sewer",
    "IRRIGATION_BACKFLOW_INSTALL":  "backflow",
    # ── Phase 3: additional permit-required templates ──
    "GAS_LINE_POOL_HEATER":         "gas",
    "GAS_LINE_GENERATOR":           "gas",
    "GAS_LINE_TANKLESS_WH":         "gas",
    "GAS_METER_UPGRADE_COORD":      "gas",
    "EJECTOR_PUMP_INSTALL":         "sewer",
    "SEWER_LINE_REPLACE_FULL":      "sewer",
    "WATER_LINE_REPLACE_MAIN_STREET": "repipe",
    "BARRIER_FREE_SHOWER_INSTALL":  "general",
    # ── Phase 4: construction, commercial & specialty permits ──
    "ROUGH_IN_MASTER_BATH":         "general",
    "ROUGH_IN_SECONDARY_BATH":      "general",
    "ROUGH_IN_HALF_BATH":           "general",
    "ROUGH_IN_KITCHEN":             "general",
    "ROUGH_IN_LAUNDRY":             "general",
    "ROUGH_IN_OUTDOOR":             "general",
    "ROUGH_IN_GAS_WHOLE_HOUSE":     "gas",
    "ROUGH_IN_WH_LOCATION":        "water_heater",
    "SEWER_TAP_CONNECTION":         "sewer",
    "WATER_TAP_CONNECTION":         "repipe",
    "FIRE_SPRINKLER_RESIDENTIAL":   "fire_sprinkler",
    "SLAB_PLUMBING_LAYOUT":        "general",
    "MULTI_STORY_RISER_PER_FLOOR": "general",
    "COMMERCIAL_TOILET_INSTALL":    "general",
    "COMMERCIAL_WALL_HUNG_TOILET":  "general",
    "COMMERCIAL_URINAL_INSTALL":    "general",
    "EYE_WASH_STATION_INSTALL":     "general",
    "GREASE_INTERCEPTOR_INSTALL":   "sewer",
    "SEWAGE_LIFT_STATION":          "sewer",
    "COMMERCIAL_WATER_SOFTENER":    "general",
    "EARTHQUAKE_VALVE_INSTALL":     "gas",
    "GAS_RANGE_CONNECTOR_REPLACE":  "gas",
    "RADIANT_FLOOR_LOOP":           "general",
    "GREYWATER_SYSTEM_INSTALL":     "general",
    "FLOOR_DRAIN_RESIDENTIAL":      "general",
    "CLEANOUT_INSTALL_EXTERIOR":    "sewer",
    # ── Phase 5: pipe material, remodel, multi-family, medical permits ──
    "CAST_IRON_STACK_REPLACE":      "general",
    "GALVANIZED_WHOLE_HOUSE_REPIPE":"repipe",
    "LEAD_SERVICE_LINE_REPLACE":    "repipe",
    "ORANGEBURG_SEWER_REPLACE":     "sewer",
    "BATH_REMODEL_PLUMBING_MASTER": "general",
    "TUB_TO_SHOWER_CONVERSION":     "general",
    "SHOWER_TO_TUB_CONVERSION":     "general",
    "LAUNDRY_ROOM_RELOCATE":        "general",
    "MEDICAL_GAS_OUTLET_INSTALL":   "general",
    "LAB_WASTE_SYSTEM":             "general",
    "RESTAURANT_FLOOR_DRAIN_INSTALL":"general",
    "THREE_COMPARTMENT_SINK_INSTALL":"general",
    "WALK_IN_TUB_INSTALL":          "general",
    "SLAB_LEAK_TUNNEL_REPAIR":      "general",
    "WH_POWER_VENT_REPLACE":        "water_heater",
    "WH_CONVERSION_GAS_TO_ELECTRIC":"water_heater",
    "SHARED_SEWER_LINE_REPAIR":     "sewer",
}

# ─── Trip / Service Call Charge ───────────────────────────────────────────────
# Minimum charge per visit (covers truck roll, diagnostics, 1st hour).
# Source: DFW plumbing contractor rate surveys 2025-2026.
_TRIP_CHARGES: dict[str, float] = {
    "dallas":   115.0,
    "tarrant":  105.0,
    "collin":   110.0,
    "denton":   105.0,
    "rockwall": 100.0,
    "parker":    95.0,
    "kaufman":   95.0,
    "ellis":     90.0,
    "johnson":   90.0,
}

# ─── DFW City / Zone Premium Multipliers ─────────────────────────────────────
# Applied to grand total when a specific high-demand city is specified.
# Source: DFW plumbing contractor market analysis Q1 2026.
# Managed by pricing_config_service.

def get_city_multiplier(city: Optional[str]) -> float:
    """Return the pricing zone multiplier for a DFW city (case-insensitive)."""
    return pricing_config_service.get_city_multiplier(city)

def get_permit_cost(task_code: str, county: str) -> float:
    """Return permit cost for a job in a given county, or 0 if no permit required."""
    permit_cat = _PERMIT_REQUIRED.get(task_code)
    if not permit_cat:
        return 0.0
    return pricing_config_service.get_permit_cost(county, permit_cat)

def get_trip_charge(county: str) -> float:
    """Return the minimum trip/service charge for a county."""
    return pricing_config_service.get_trip_charge(county)


# Local copies maintained for sync with main.py _sync_runtime_config
# which has been updated to use pricing_config_service.
TAX_RATES: dict[str, float] = {}
MARKUP_RULES: dict[str, dict] = {}


@dataclass
class MaterialItem:
    canonical_item: str
    description: str
    quantity: float
    unit: str
    unit_cost: float
    supplier: str
    sku: Optional[str] = None
    total_cost: float = field(init=False)

    def __post_init__(self):
        self.total_cost = round(self.quantity * self.unit_cost, 2)


@dataclass
class LineItem:
    line_type: str       # labor, material, tax, markup, misc
    description: str
    quantity: float
    unit: str
    unit_cost: float
    total_cost: float
    supplier: Optional[str] = None
    sku: Optional[str] = None
    canonical_item: Optional[str] = None
    trace_json: Optional[dict] = None


@dataclass
class EstimateResult:
    template_code: Optional[str]
    assembly_code: Optional[str]
    job_type: str
    access_type: str
    urgency_type: str
    county: str
    tax_rate: float
    labor_total: float
    materials_total: float
    tax_total: float
    markup_total: float
    misc_total: float
    subtotal: float
    grand_total: float
    confidence_score: float
    confidence_label: str
    line_items: list[LineItem]
    assumptions: list[str]
    sources: list[str]
    pricing_trace: dict   # full deterministic trace
    # Optional fields added for construction/service parity
    city: Optional[str] = None
    trip_total: float = 0.0
    permit_total: float = 0.0
    city_premium: float = 0.0


class PricingEngine:
    """
    The single source of deterministic pricing truth.
    Inputs → Templates → Deterministic math → EstimateResult
    No LLM involved in calculations.
    """

    def calculate_service_estimate(
        self,
        task_code: str,
        materials: list[MaterialItem],
        assembly_code: Optional[str] = None,
        access: str = "first_floor",
        urgency: str = "standard",
        county: str = "Dallas",
        city: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        notes: Optional[str] = None,
        include_trip_charge: bool = True,
    ) -> EstimateResult:
        """Calculate a complete service estimate."""

        template = get_template(task_code)
        if not template:
            raise ValueError(f"Unknown labor template: {task_code}")

        job_type = template.category

        # 1. Labor calculation
        labor_data = template.calculate_labor_cost(access=access, urgency=urgency)
        labor_cost = labor_data["total_labor_cost"]

        # 2. Materials cost
        materials_cost = sum(m.total_cost for m in materials)

        # 3. Tax (materials only in TX)
        tax_rate = pricing_config_service.get_tax_rate(county)
        tax_amount = round(materials_cost * tax_rate, 2)

        # 4. Markup
        markup_rules = pricing_config_service.get_markup_rule(job_type)
        materials_markup = round(materials_cost * markup_rules["materials_markup_pct"], 2)
        misc_flat = markup_rules["misc_flat"]

        # 5. Trip charge (first-visit service call)
        trip_cost = get_trip_charge(county) if include_trip_charge and job_type == "service" else 0.0

        # 6. Permit (if required for this job type)
        permit_cost = get_permit_cost(task_code, county)

        # 7. City zone premium multiplier (applied to labor + markup only, not tax/permit)
        city_mult = get_city_multiplier(city)

        # Base before city multiplier
        base_subtotal = (labor_cost + materials_cost + materials_markup +
                         misc_flat + trip_cost + permit_cost)
        # City multiplier applies to labor + markup portions only (not materials, tax, permit)
        city_premium = round((labor_cost + materials_markup + misc_flat + trip_cost)
                              * (city_mult - 1.0), 2) if city_mult != 1.0 else 0.0

        subtotal = round(base_subtotal + city_premium, 2)
        grand_total = round(subtotal + tax_amount, 2)

        # 8. Build line items with traces
        line_items = []

        # Trip charge (first line — always visible)
        if include_trip_charge and trip_cost > 0:
            line_items.append(LineItem(
                line_type="trip",
                description=f"Service Call / Trip Charge — {county} County",
                quantity=1,
                unit="visit",
                unit_cost=trip_cost,
                total_cost=trip_cost,
                trace_json={"county": county, "city": city},
            ))

        # Labor line
        line_items.append(LineItem(
            line_type="labor",
            description=f"Labor — {template.name}",
            quantity=labor_data["adjusted_hours"],
            unit="hr",
            unit_cost=template.lead_rate,
            total_cost=labor_data["lead_cost"],
            trace_json=labor_data,
        ))

        if labor_data["helper_required"] and labor_data["helper_cost"] > 0:
            line_items.append(LineItem(
                line_type="labor",
                description="Helper/Apprentice Labor",
                quantity=labor_data["helper_hours"],
                unit="hr",
                unit_cost=template.helper_rate,
                total_cost=labor_data["helper_cost"],
            ))

        if labor_data["disposal_cost"] > 0:
            line_items.append(LineItem(
                line_type="labor",
                description="Disposal/Haul-Away Labor",
                quantity=labor_data["disposal_hours"],
                unit="hr",
                unit_cost=template.lead_rate,
                total_cost=labor_data["disposal_cost"],
            ))

        # Material lines
        for mat in materials:
            line_items.append(LineItem(
                line_type="material",
                description=mat.description,
                quantity=mat.quantity,
                unit=mat.unit,
                unit_cost=mat.unit_cost,
                total_cost=mat.total_cost,
                supplier=mat.supplier,
                sku=mat.sku,
                canonical_item=mat.canonical_item,
                trace_json={"canonical_item": mat.canonical_item, "supplier": mat.supplier},
            ))

        # Markup line
        if materials_markup > 0:
            line_items.append(LineItem(
                line_type="markup",
                description=f"Materials Markup ({int(markup_rules['materials_markup_pct']*100)}%)",
                quantity=1,
                unit="lot",
                unit_cost=materials_markup,
                total_cost=materials_markup,
                trace_json={"markup_pct": markup_rules["materials_markup_pct"], "base": materials_cost},
            ))

        # Misc/disposal
        if misc_flat > 0:
            line_items.append(LineItem(
                line_type="misc",
                description="Misc Supplies & Disposal",
                quantity=1,
                unit="lot",
                unit_cost=misc_flat,
                total_cost=misc_flat,
            ))

        # City premium line (only if non-zero)
        if city_premium > 0:
            line_items.append(LineItem(
                line_type="misc",
                description=f"Market Zone Adjustment — {city} (+{int((city_mult-1)*100)}%)",
                quantity=1,
                unit="lot",
                unit_cost=city_premium,
                total_cost=city_premium,
                trace_json={"city": city, "multiplier": city_mult},
            ))

        # Permit line
        if permit_cost > 0:
            line_items.append(LineItem(
                line_type="permit",
                description=f"Permit — {county} County ({_PERMIT_REQUIRED.get(task_code, 'general')})",
                quantity=1,
                unit="permit",
                unit_cost=permit_cost,
                total_cost=permit_cost,
                trace_json={"task_code": task_code, "county": county},
            ))

        # Tax line
        if tax_amount > 0:
            line_items.append(LineItem(
                line_type="tax",
                description=f"Sales Tax — {county} County ({tax_rate*100:.2f}%)",
                quantity=1,
                unit="lot",
                unit_cost=tax_amount,
                total_cost=tax_amount,
                trace_json={"rate": tax_rate, "taxable_base": materials_cost, "county": county},
            ))

        # Confidence based on data quality
        confidence, confidence_label = self._calculate_confidence(
            template=template, materials=materials, access=access
        )

        assumptions = self._build_assumptions(
            template, access, urgency, county, city, preferred_supplier,
            permit_cost=permit_cost, trip_cost=trip_cost, city_mult=city_mult,
        )

        return EstimateResult(
            template_code=task_code,
            assembly_code=assembly_code,
            job_type=job_type,
            access_type=access,
            urgency_type=urgency,
            county=county,
            city=city,
            tax_rate=tax_rate,
            labor_total=round(labor_cost, 2),
            materials_total=round(materials_cost, 2),
            tax_total=tax_amount,
            markup_total=round(materials_markup, 2),
            misc_total=round(misc_flat, 2),
            trip_total=round(trip_cost, 2),
            permit_total=round(permit_cost, 2),
            city_premium=round(city_premium, 2),
            subtotal=subtotal,
            grand_total=grand_total,
            confidence_score=confidence,
            confidence_label=confidence_label,
            line_items=line_items,
            assumptions=assumptions,
            sources=[f"Labor template: {task_code}", f"Tax rate: {county} county"],
            pricing_trace={
                "labor": labor_data,
                "materials": [{"canonical": m.canonical_item, "cost": m.total_cost} for m in materials],
                "tax": {"rate": tax_rate, "amount": tax_amount},
                "markup": markup_rules,
                "trip_charge": trip_cost,
                "permit": permit_cost,
                "city_multiplier": city_mult,
                "city_premium": city_premium,
                "totals": {
                    "labor": labor_cost,
                    "materials": materials_cost,
                    "markup": materials_markup,
                    "misc": misc_flat,
                    "trip": trip_cost,
                    "permit": permit_cost,
                    "city_premium": city_premium,
                    "tax": tax_amount,
                    "grand_total": grand_total,
                }
            }
        )

    def calculate_construction_estimate(
        self,
        bath_groups: int = 1,
        fixture_count: int = 5,
        underground_lf: float = 0.0,
        county: str = "Dallas",
        city: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        include_trip_charge: bool = True,
    ) -> EstimateResult:
        """Calculate a new construction estimate."""

        rough_template = get_template("ROUGH_IN_PER_BATH_GROUP")
        topout_template = get_template("TOP_OUT_PER_FIXTURE")
        final_template = get_template("FINAL_SET_PER_FIXTURE")
        underground_template = get_template("UNDERGROUND_PER_LF")

        line_items = []
        labor_total = 0.0

        # Trip charge
        trip_cost = get_trip_charge(county) if include_trip_charge else 0.0
        if trip_cost > 0:
            line_items.append(LineItem(
                line_type="trip",
                description=f"Service Call / Trip Charge — {county} County",
                quantity=1,
                unit="visit",
                unit_cost=trip_cost,
                total_cost=trip_cost,
                trace_json={"county": county, "city": city},
            ))

        # Rough-in
        if rough_template:
            rough_data = rough_template.calculate_labor_cost()
            rough_cost = round(rough_data["total_labor_cost"] * bath_groups, 2)
            labor_total += rough_cost
            line_items.append(LineItem(
                line_type="labor",
                description=f"Rough-In Labor ({bath_groups} bath group{'s' if bath_groups > 1 else ''})",
                quantity=bath_groups,
                unit="bath group",
                unit_cost=rough_data["total_labor_cost"],
                total_cost=rough_cost,
                trace_json=rough_data,
            ))

        # Top-out
        if topout_template:
            topout_data = topout_template.calculate_labor_cost()
            topout_cost = round(topout_data["total_labor_cost"] * fixture_count, 2)
            labor_total += topout_cost
            line_items.append(LineItem(
                line_type="labor",
                description=f"Top-Out Labor ({fixture_count} fixtures)",
                quantity=fixture_count,
                unit="fixture",
                unit_cost=topout_data["total_labor_cost"],
                total_cost=topout_cost,
                trace_json=topout_data,
            ))

        # Final set
        if final_template:
            final_data = final_template.calculate_labor_cost()
            final_cost = round(final_data["total_labor_cost"] * fixture_count, 2)
            labor_total += final_cost
            line_items.append(LineItem(
                line_type="labor",
                description=f"Final Set Labor ({fixture_count} fixtures)",
                quantity=fixture_count,
                unit="fixture",
                unit_cost=final_data["total_labor_cost"],
                total_cost=final_cost,
            ))

        # Underground
        if underground_lf > 0 and underground_template:
            ug_data = underground_template.calculate_labor_cost()
            ug_cost = round(ug_data["total_labor_cost"] * underground_lf, 2)
            labor_total += ug_cost
            line_items.append(LineItem(
                line_type="labor",
                description=f"Underground Drain ({underground_lf:.0f} LF)",
                quantity=underground_lf,
                unit="LF",
                unit_cost=ug_data["total_labor_cost"],
                total_cost=ug_cost,
                trace_json=ug_data,
            ))

        # Materials placeholder (no assembly lookup for construction default)
        materials_cost = 0.0
        tax_rate = pricing_config_service.get_tax_rate(county)
        tax_amount = round(materials_cost * tax_rate, 2)
        markup_rules = pricing_config_service.get_markup_rule("construction")
        materials_markup = round(materials_cost * markup_rules["materials_markup_pct"], 2)
        misc_flat = markup_rules["misc_flat"]

        # Permit cost (construction typically requires a plumbing permit)
        permit_cost = get_permit_cost("WHOLE_HOUSE_REPIPE_PEX", county)

        # City zone premium multiplier
        city_mult = get_city_multiplier(city)

        base_subtotal = (labor_total + materials_cost + materials_markup +
                         misc_flat + trip_cost + permit_cost)
        city_premium = round((labor_total + materials_markup + misc_flat + trip_cost)
                              * (city_mult - 1.0), 2) if city_mult != 1.0 else 0.0

        subtotal = round(base_subtotal + city_premium, 2)
        grand_total = round(subtotal + tax_amount, 2)

        # Markup line
        if materials_markup > 0:
            line_items.append(LineItem(
                line_type="markup",
                description=f"Materials Markup ({int(markup_rules['materials_markup_pct']*100)}%)",
                quantity=1, unit="lot",
                unit_cost=materials_markup, total_cost=materials_markup,
            ))

        # Misc line
        if misc_flat > 0:
            line_items.append(LineItem(
                line_type="misc",
                description="Misc Supplies & Disposal",
                quantity=1, unit="lot",
                unit_cost=misc_flat, total_cost=misc_flat,
            ))

        # City premium line
        if city_premium > 0:
            line_items.append(LineItem(
                line_type="misc",
                description=f"Market Zone Adjustment — {city} (+{int((city_mult-1)*100)}%)",
                quantity=1, unit="lot",
                unit_cost=city_premium, total_cost=city_premium,
                trace_json={"city": city, "multiplier": city_mult},
            ))

        # Permit line
        if permit_cost > 0:
            line_items.append(LineItem(
                line_type="permit",
                description=f"Permit — {county} County (plumbing)",
                quantity=1, unit="permit",
                unit_cost=permit_cost, total_cost=permit_cost,
            ))

        # Tax line
        if tax_amount > 0:
            line_items.append(LineItem(
                line_type="tax",
                description=f"Sales Tax — {county} County ({tax_rate*100:.2f}%)",
                quantity=1, unit="lot",
                unit_cost=tax_amount, total_cost=tax_amount,
            ))

        return EstimateResult(
            template_code="CONSTRUCTION_ESTIMATE",
            assembly_code=None,
            job_type="construction",
            access_type="first_floor",
            urgency_type="standard",
            county=county,
            city=city,
            tax_rate=tax_rate,
            labor_total=round(labor_total, 2),
            materials_total=round(materials_cost, 2),
            tax_total=tax_amount,
            markup_total=round(materials_markup, 2),
            misc_total=round(misc_flat, 2),
            trip_total=round(trip_cost, 2),
            permit_total=round(permit_cost, 2),
            city_premium=round(city_premium, 2),
            subtotal=round(subtotal, 2),
            grand_total=grand_total,
            confidence_score=0.75,
            confidence_label="MEDIUM",
            line_items=line_items,
            assumptions=[a for a in [
                f"Based on {bath_groups} bath group(s) and {fixture_count} fixtures",
                "Material costs require itemized quote",
                f"County: {county}, Tax rate: {tax_rate*100:.2f}%",
                f"Trip charge: ${trip_cost:.2f}" if trip_cost else None,
                f"Permit: ${permit_cost:.2f}" if permit_cost else None,
                f"City premium: {city} ({city_mult}x)" if city and city_mult != 1.0 else None,
            ] if a is not None],
            sources=["Labor templates: ROUGH_IN_PER_BATH_GROUP, TOP_OUT_PER_FIXTURE, FINAL_SET_PER_FIXTURE"],
            pricing_trace={
                "bath_groups": bath_groups,
                "fixture_count": fixture_count,
                "underground_lf": underground_lf,
                "labor_total": labor_total,
                "trip_cost": trip_cost,
                "permit_cost": permit_cost,
                "city_mult": city_mult,
                "city_premium": city_premium,
                "grand_total": grand_total,
            }
        )

    def quick_estimate(
        self,
        task_code: str,
        assembly_code: Optional[str] = None,
        access: str = "first_floor",
        urgency: str = "standard",
        county: str = "Dallas",
        city: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        quantity: int = 1,
        include_trip_charge: bool = True,
    ) -> EstimateResult:
        """
        Synchronous, pure in-memory estimate — no DB calls, returns instantly.
        Uses enrichment cache (if warm) then CANONICAL_MAP. Ideal for fast chat responses.
        """
        from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
        from app.services.data_sources.price_enrichment import get_enrichment_service

        enrichment = get_enrichment_service()
        materials: list[MaterialItem] = []

        if assembly_code:
            assembly = MATERIAL_ASSEMBLIES.get(assembly_code)
            if assembly:
                for canonical_item, qty in assembly["items"].items():
                    # Try enrichment cache first (up-to-date DFW market price)
                    enriched_cost = enrichment.get_cached_cost(canonical_item)
                    if enriched_cost is not None:
                        # Use enriched price with a generic supplier label
                        materials.append(MaterialItem(
                            canonical_item=canonical_item,
                            description=canonical_item.replace(".", " ").replace("_", " ").title(),
                            quantity=qty,
                            unit="ea",
                            unit_cost=enriched_cost,
                            supplier="market_price",
                            sku=None,
                        ))
                    else:
                        # Fall back to CANONICAL_MAP supplier lookup
                        result = supplier_service._canonical_lookup(canonical_item, preferred_supplier)
                        if result:
                            materials.append(MaterialItem(
                                canonical_item=canonical_item,
                                description=result.name,
                                quantity=qty,
                                unit="ea",
                                unit_cost=result.unit_cost,
                                supplier=result.selected_supplier,
                                sku=result.sku,
                            ))

        estimate = self.calculate_service_estimate(
            task_code=task_code,
            materials=materials,
            assembly_code=assembly_code,
            access=access,
            urgency=urgency,
            county=county,
            city=city,
            preferred_supplier=preferred_supplier,
            include_trip_charge=include_trip_charge,
        )

        if quantity > 1:
            estimate = self.scale_estimate(estimate, quantity)

        return estimate

    def scale_estimate(self, result: EstimateResult, quantity: int) -> EstimateResult:
        """Scale a single-unit estimate by a whole-number quantity.

        Trip charge and permit fee are per-visit fixed costs — NOT scaled by quantity.
        Labor, materials, markup, misc, and tax scale linearly with quantity.
        """
        if quantity <= 1:
            return result
        q = quantity

        scaled_lines = []
        trip_total = 0.0
        permit_total = 0.0
        for li in result.line_items:
            if li.line_type in ("trip", "permit"):
                # Fixed per-visit costs — keep as-is
                scaled_lines.append(li)
                if li.line_type == "trip":
                    trip_total = li.total_cost
                else:
                    permit_total = li.total_cost
            else:
                scaled_lines.append(LineItem(
                    line_type=li.line_type,
                    description=li.description,
                    quantity=round(li.quantity * q, 4),
                    unit=li.unit,
                    unit_cost=li.unit_cost,
                    total_cost=round(li.total_cost * q, 2),
                    supplier=li.supplier,
                    sku=li.sku,
                    canonical_item=li.canonical_item,
                    trace_json=li.trace_json,
                ))

        # Recalculate grand_total to keep trip/permit fixed
        grand_total = round(
            result.labor_total * q
            + result.materials_total * q
            + result.markup_total * q
            + result.misc_total * q
            + result.tax_total * q
            + trip_total
            + permit_total,
            2,
        )

        return EstimateResult(
            template_code=result.template_code,
            assembly_code=result.assembly_code,
            job_type=result.job_type,
            access_type=result.access_type,
            urgency_type=result.urgency_type,
            county=result.county,
            city=result.city,
            tax_rate=result.tax_rate,
            labor_total=round(result.labor_total * q, 2),
            materials_total=round(result.materials_total * q, 2),
            tax_total=round(result.tax_total * q, 2),
            markup_total=round(result.markup_total * q, 2),
            misc_total=round(result.misc_total * q, 2),
            trip_total=round(trip_total, 2),
            permit_total=round(permit_total, 2),
            city_premium=round(result.city_premium * q, 2) if result.city_premium else 0.0,
            subtotal=round(
                result.labor_total * q
                + result.materials_total * q
                + result.markup_total * q
                + result.misc_total * q
                + trip_total
                + permit_total,
                2,
            ),
            grand_total=grand_total,
            confidence_score=result.confidence_score,
            confidence_label=result.confidence_label,
            line_items=scaled_lines,
            assumptions=result.assumptions + [f"Quantity: {q} units — trip charge & permit billed once"],
            sources=result.sources,
            pricing_trace={**result.pricing_trace, "quantity": q},
        )

    def _get_tax_rate(self, county: str) -> float:
        return pricing_config_service.get_tax_rate(county)

    def _calculate_confidence(
        self, template: LaborTemplateData, materials: list[MaterialItem], access: str
    ) -> tuple[float, str]:
        score = 0.90  # base

        if not materials:
            score -= 0.15  # no material data
        elif any(m.unit_cost == 0 for m in materials):
            score -= 0.10  # some zero-cost items

        if access in ("attic", "crawlspace"):
            score -= 0.05  # access uncertainty

        score = max(0.30, min(1.0, score))

        if score >= 0.85:
            label = "HIGH"
        elif score >= 0.65:
            label = "MEDIUM"
        else:
            label = "LOW"

        return round(score, 2), label

    def _build_assumptions(
        self, template: LaborTemplateData, access: str, urgency: str,
        county: str, city: Optional[str], preferred_supplier: Optional[str],
        permit_cost: float = 0.0, trip_cost: float = 0.0, city_mult: float = 1.0,
    ) -> list[str]:
        assumptions = []
        access_labels = {
            "first_floor": "first floor",
            "second_floor": "second floor",
            "attic": "attic",
            "crawlspace": "crawlspace",
            "slab": "slab foundation",
            "basement": "basement",
        }
        if city:
            assumptions.append(f"City: {city.title()} — {county} County")
        else:
            assumptions.append(f"County: {county}")
        assumptions.append(f"Location: {access_labels.get(access, access)}")
        if urgency != "standard":
            assumptions.append(f"Urgency pricing: {urgency}")
        assumptions.append(f"Sales tax rate: {self._get_tax_rate(county)*100:.2f}% (materials only)")
        if trip_cost > 0:
            assumptions.append(f"Service call / trip charge included: ${trip_cost:.0f}")
        if permit_cost > 0:
            assumptions.append(f"Permit fee included: ${permit_cost:.0f} ({county} County)")
        if city_mult != 1.0:
            assumptions.append(
                f"Market zone premium: {city.title() if city else county} "
                f"({'+' if city_mult > 1 else ''}{int((city_mult-1)*100)}%)"
            )
        if preferred_supplier:
            assumptions.append(f"Preferred supplier: {preferred_supplier}")
        else:
            assumptions.append("Material prices based on lowest available DFW supplier")
        if template.notes:
            assumptions.append(template.notes)
        return assumptions


# Singleton
pricing_engine = PricingEngine()
