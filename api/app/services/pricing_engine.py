"""
Pricing Engine — Deterministic plumbing price calculator.
RULE: No LLM in the calculation path. Every dollar is traceable.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from app.services.labor_engine import (
    LABOR_TEMPLATES, LaborTemplateData, get_template,
    AccessType, UrgencyType
)


class County(str, Enum):
    DALLAS = "Dallas"
    TARRANT = "Tarrant"
    COLLIN = "Collin"
    DENTON = "Denton"
    ROCKWALL = "Rockwall"
    PARKER = "Parker"
    KAUFMAN = "Kaufman"


# Texas tax rates — labor is non-taxable in TX
# This map is now loaded from the database via the seed script.
TAX_RATES: dict[str, float] = {}

# Default markup rules by job type
# This map is now loaded from the database via the seed script.
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
        preferred_supplier: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> EstimateResult:
        """Calculate a complete service estimate."""

        template = get_template(task_code)
        if not template:
            raise ValueError(f"Unknown labor template: {task_code}")

        # 1. Labor calculation
        labor_data = template.calculate_labor_cost(access=access, urgency=urgency)
        labor_cost = labor_data["total_labor_cost"]

        # 2. Materials cost
        materials_cost = sum(m.total_cost for m in materials)

        # 3. Tax (materials only in TX)
        tax_rate = self._get_tax_rate(county)
        tax_amount = round(materials_cost * tax_rate, 2)

        # 4. Markup
        markup_rules = MARKUP_RULES.get("service", MARKUP_RULES["service"])
        materials_markup = round(materials_cost * markup_rules["materials_markup_pct"], 2)
        misc_flat = markup_rules["misc_flat"]

        # 5. Totals
        subtotal = labor_cost + materials_cost + materials_markup + misc_flat
        grand_total = round(subtotal + tax_amount, 2)

        # 6. Build line items with traces
        line_items = []

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
        for i, mat in enumerate(materials):
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

        assumptions = self._build_assumptions(template, access, urgency, county, preferred_supplier)

        return EstimateResult(
            template_code=task_code,
            assembly_code=assembly_code,
            job_type="service",
            access_type=access,
            urgency_type=urgency,
            county=county,
            tax_rate=tax_rate,
            labor_total=round(labor_cost, 2),
            materials_total=round(materials_cost, 2),
            tax_total=tax_amount,
            markup_total=round(materials_markup, 2),
            misc_total=round(misc_flat, 2),
            subtotal=round(subtotal, 2),
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
                "totals": {
                    "labor": labor_cost,
                    "materials": materials_cost,
                    "markup": materials_markup,
                    "misc": misc_flat,
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
        preferred_supplier: Optional[str] = None,
    ) -> EstimateResult:
        """Calculate a new construction estimate."""

        rough_template = get_template("ROUGH_IN_PER_BATH_GROUP")
        topout_template = get_template("TOP_OUT_PER_FIXTURE")
        final_template = get_template("FINAL_SET_PER_FIXTURE")
        underground_template = get_template("UNDERGROUND_PER_LF")

        line_items = []
        labor_total = 0.0

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
        tax_rate = self._get_tax_rate(county)
        tax_amount = round(materials_cost * tax_rate, 2)
        markup_rules = MARKUP_RULES.get("construction", MARKUP_RULES["construction"])
        materials_markup = round(materials_cost * markup_rules["materials_markup_pct"], 2)
        misc_flat = markup_rules["misc_flat"]

        subtotal = labor_total + materials_cost + materials_markup + misc_flat
        grand_total = round(subtotal + tax_amount, 2)

        return EstimateResult(
            template_code="CONSTRUCTION_ESTIMATE",
            assembly_code=None,
            job_type="construction",
            access_type="first_floor",
            urgency_type="standard",
            county=county,
            tax_rate=tax_rate,
            labor_total=round(labor_total, 2),
            materials_total=round(materials_cost, 2),
            tax_total=tax_amount,
            markup_total=round(materials_markup, 2),
            misc_total=round(misc_flat, 2),
            subtotal=round(subtotal, 2),
            grand_total=grand_total,
            confidence_score=0.75,
            confidence_label="MEDIUM",
            line_items=line_items,
            assumptions=[
                f"Based on {bath_groups} bath group(s) and {fixture_count} fixtures",
                "Material costs require itemized quote",
                f"County: {county}, Tax rate: {tax_rate*100:.2f}%",
            ],
            sources=["Labor templates: ROUGH_IN_PER_BATH_GROUP, TOP_OUT_PER_FIXTURE, FINAL_SET_PER_FIXTURE"],
            pricing_trace={
                "bath_groups": bath_groups,
                "fixture_count": fixture_count,
                "underground_lf": underground_lf,
                "labor_total": labor_total,
                "grand_total": grand_total,
            }
        )

    def _get_tax_rate(self, county: str) -> float:
        return TAX_RATES.get(county.lower(), 0.0825)

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
        county: str, preferred_supplier: Optional[str]
    ) -> list[str]:
        assumptions = []
        access_labels = {
            "first_floor": "first floor",
            "second_floor": "second floor",
            "attic": "attic",
            "crawlspace": "crawlspace",
            "slab": "slab foundation",
        }
        assumptions.append(f"Location: {access_labels.get(access, access)}")
        if urgency != "standard":
            assumptions.append(f"Urgency pricing: {urgency}")
        assumptions.append(f"County: {county} — Tax rate: {self._get_tax_rate(county)*100:.2f}%")
        if preferred_supplier:
            assumptions.append(f"Preferred supplier: {preferred_supplier}")
        else:
            assumptions.append("Material prices based on lowest available DFW supplier")
        if template.notes:
            assumptions.append(template.notes)
        return assumptions


# Singleton
pricing_engine = PricingEngine()
