"""
LLM Agent Orchestrator — Classifies and routes pricing requests.
RULE: Agent classifies and routes. PricingEngine calculates. Never the reverse.
"""

import re
from typing import Optional
import structlog

from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template, LABOR_TEMPLATES as LABOR_MAP

logger = structlog.get_logger()


# ─── Keyword Tables ───────────────────────────────────────────────────────────

TASK_KEYWORDS: dict[str, dict] = {
    # ── Toilet ───────────────────────────────────────────────────────────────
    "TOILET_COMFORT_HEIGHT": {
        "keywords": ["comfort height", "ada toilet", "ada commode", "tall toilet", "elongated comfort"],
        "assembly": "TOILET_INSTALL_KIT",
        "default_access": "first_floor",
        "task_override": "TOILET_REPLACE_STANDARD",  # same labor; fixture type noted in answer
    },
    "TOILET_FLANGE_REPAIR": {
        "keywords": ["toilet flange", "flange repair", "flange replace", "broken flange", "closet flange"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "TOILET_REPLACE_STANDARD": {
        "keywords": ["toilet", "commode", "throne", "water closet", "wc"],
        "assembly": "TOILET_INSTALL_KIT",
        "default_access": "first_floor",
    },
    # ── PRV ───────────────────────────────────────────────────────────────────
    "PRV_REPLACE": {
        "keywords": ["prv", "pressure reducing valve", "pressure regulator", "pressure reducer", "pressure valve"],
        "assembly": "PRV_KIT",
        "default_access": "first_floor",
    },
    # ── Hose Bib ─────────────────────────────────────────────────────────────
    "HOSE_BIB_REPLACE": {
        "keywords": ["hose bib", "hose bibb", "outdoor faucet", "sillcock", "outside faucet", "exterior faucet"],
        "assembly": "HOSE_BIB_KIT",
        "default_access": "first_floor",
    },
    # ── Shower / Tub ─────────────────────────────────────────────────────────
    "SHOWER_VALVE_REPLACE": {
        "keywords": ["shower valve", "shower cartridge", "shower mixing valve", "shower faucet"],
        "assembly": "SHOWER_VALVE_KIT",
        "default_access": "first_floor",
    },
    "TUB_SPOUT_REPLACE": {
        "keywords": ["tub spout", "bathtub spout", "bath spout", "tub faucet spout"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "SHOWER_HEAD_REPLACE": {
        "keywords": ["shower head", "showerhead", "rain shower head", "shower spray head"],
        "assembly": None,
        "default_access": "first_floor",
    },
    # ── Kitchen ───────────────────────────────────────────────────────────────
    "KITCHEN_FAUCET_REPLACE": {
        "keywords": ["kitchen faucet", "kitchen sink faucet", "kitchen tap"],
        "assembly": "KITCHEN_FAUCET_KIT",
        "default_access": "first_floor",
    },
    "GARBAGE_DISPOSAL_INSTALL": {
        "keywords": ["disposal", "garbage disposal", "insinkerator", "food disposal", "garburator"],
        "assembly": "DISPOSAL_KIT",
        "default_access": "first_floor",
    },
    # ── Lavatory ─────────────────────────────────────────────────────────────
    "LAV_SINK_REPLACE": {
        "keywords": ["bathroom sink", "lavatory sink", "lav sink", "vanity sink", "pedestal sink", "vessel sink"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "LAV_FAUCET_REPLACE": {
        "keywords": ["bathroom faucet", "lavatory faucet", "lav faucet", "sink faucet", "bath faucet"],
        "assembly": "LAV_FAUCET_KIT",
        "default_access": "first_floor",
    },
    # ── Valves & Stops ────────────────────────────────────────────────────────
    "ANGLE_STOP_REPLACE": {
        "keywords": ["angle stop", "shutoff valve", "shut off valve", "stop valve", "angle valve",
                     "supply valve", "quarter turn valve", "water shutoff"],
        "assembly": "ANGLE_STOP_KIT",
        "default_access": "first_floor",
    },
    "SUPPLY_LINE_REPLACE": {
        "keywords": ["supply line", "water supply line", "braided line", "toilet supply line", "faucet supply line"],
        "assembly": None,
        "default_access": "first_floor",
    },
    # ── Drain ─────────────────────────────────────────────────────────────────
    "PTRAP_REPLACE": {
        "keywords": ["p-trap", "ptrap", "p trap", "drain trap", "s-trap"],
        "assembly": "PTRAP_KIT",
        "default_access": "first_floor",
    },
    "MAIN_LINE_CLEAN": {
        "keywords": ["main line", "main drain", "sewer line", "main sewer", "sewer clean",
                     "main stoppage", "sewer backup", "main clog"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "DRAIN_CLEAN_STANDARD": {
        "keywords": ["drain clean", "clogged drain", "slow drain", "stopped drain",
                     "clear drain", "snake drain", "drain snake", "blocked drain"],
        "assembly": None,
        "default_access": "first_floor",
    },
    # ── Gas ───────────────────────────────────────────────────────────────────
    "GAS_SHUTOFF_REPLACE": {
        "keywords": ["gas shutoff", "gas shut off", "gas shutoff valve", "gas ball valve", "gas valve replace"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "GAS_LINE_REPAIR_MINOR": {
        "keywords": ["gas line", "gas leak", "gas fitting", "gas pipe", "gas repair"],
        "assembly": None,
        "default_access": "first_floor",
    },
}

ACCESS_KEYWORDS: dict[str, list[str]] = {
    "attic":        ["attic", "in the attic", "attic install", "in attic"],
    "second_floor": ["second floor", "2nd floor", "upstairs", "second story", "2nd story", "upper floor"],
    "crawlspace":   ["crawl space", "crawlspace", "under the house", "crawl", "under house"],
    "slab":         ["slab", "slab foundation", "under slab"],
    "basement":     ["basement"],
    "first_floor":  ["first floor", "1st floor", "ground floor", "downstairs", "garage", "utility room", "hall closet"],
}

URGENCY_KEYWORDS: dict[str, list[str]] = {
    "emergency": ["emergency", "urgent", "asap", "right now", "immediately", "tonight",
                  "flooding", "flood", "burst", "no water", "water off"],
    "same_day":  ["same day", "today", "this afternoon", "this morning", "few hours"],
    "standard":  [],
}

COUNTY_KEYWORDS: dict[str, list[str]] = {
    "dallas":   ["dallas", "highland park", "university park", "desoto", "duncanville",
                 "garland", "mesquite", "richardson", "rowlett", "balch springs",
                 "cedar hill", "farmers branch", "glenn heights", "grand prairie",
                 "irving", "lancaster", "seagoville", "sunnyvale"],
    "tarrant":  ["fort worth", "arlington", "mansfield", "burleson", "hurst",
                 "bedford", "euless", "grapevine", "north richland hills", "keller",
                 "southlake", "colleyville", "saginaw", "azle", "crowley",
                 "benbrook", "white settlement", "river oaks", "forest hill"],
    "collin":   ["plano", "mckinney", "frisco", "allen", "prosper", "celina",
                 "wylie", "murphy", "sachse", "anna", "melissa", "fairview",
                 "new hope", "nevada", "blue ridge"],
    "denton":   ["denton", "lewisville", "flower mound", "coppell", "carrollton",
                 "the colony", "little elm", "highland village", "corinth",
                 "lake dallas", "lantana", "argyle", "trophy club", "roanoke",
                 "northlake", "pilot point"],
    "rockwall": ["rockwall", "royse city", "heath", "fate", "rowlett"],
    "parker":   ["weatherford", "aledo", "willow park", "hudson oaks", "springtown"],
    "kaufman":  ["kaufman", "forney", "terrell", "crandall", "mesquite"],
}


def classify_request(message: str) -> dict:
    """
    Rule-based classification of plumbing service request.
    Returns: {task_code, assembly_code, access_type, urgency, county, confidence}
    """
    msg = message.lower()

    # Urgency
    urgency = "standard"
    for urg, kws in URGENCY_KEYWORDS.items():
        if any(kw in msg for kw in kws):
            urgency = urg
            break

    # Access
    access_type = "first_floor"
    for access, kws in ACCESS_KEYWORDS.items():
        if any(kw in msg for kw in kws):
            access_type = access
            break

    # County — city names take precedence
    county = "Dallas"
    for county_name, kws in COUNTY_KEYWORDS.items():
        if any(kw in msg for kw in kws):
            county = county_name.capitalize()
            break

    # Supplier preference
    preferred_supplier = None
    for sup in ["ferguson", "moore supply", "moore_supply", "apex"]:
        if sup.replace("_", " ") in msg:
            preferred_supplier = sup.replace(" ", "_")
            break

    # ── Water heater — handled first (most complex) ───────────────────────────
    task_code = None
    assembly_code = None
    confidence = 0.70

    if "water heater" in msg or "hot water heater" in msg or "hot water tank" in msg:
        if access_type == "attic" or "attic" in msg:
            task_code, assembly_code, confidence = "WH_50G_GAS_ATTIC", "WH_50G_GAS_ATTIC_KIT", 0.85
        elif "tankless" in msg or "on demand" in msg or "instantaneous" in msg:
            task_code, assembly_code, confidence = "WH_TANKLESS_GAS", "WH_TANKLESS_GAS_KIT", 0.90
        elif "electric" in msg or "elec" in msg:
            task_code, assembly_code, confidence = "WH_50G_ELECTRIC_STANDARD", "WH_50G_ELECTRIC_KIT", 0.85
        elif re.search(r'\b40\b|\b40g\b|\b40-gal', msg):
            task_code, assembly_code, confidence = "WH_40G_GAS_STANDARD", "WH_40G_GAS_KIT", 0.85
        elif re.search(r'\b50\b|\b50g\b|\b50-gal', msg):
            task_code, assembly_code, confidence = "WH_50G_GAS_STANDARD", "WH_50G_GAS_KIT", 0.88
        else:
            task_code, assembly_code, confidence = "WH_50G_GAS_STANDARD", "WH_50G_GAS_KIT", 0.78

    # ── Gas detection — must run before general valve keywords ────────────────
    if not task_code and "gas" in msg:
        if any(kw in msg for kw in ["shutoff", "shut off", "ball valve", "gas valve"]):
            task_code, confidence = "GAS_SHUTOFF_REPLACE", 0.88
        elif any(kw in msg for kw in ["line", "leak", "pipe", "fitting", "repair", "pressure"]):
            task_code, confidence = "GAS_LINE_REPAIR_MINOR", 0.85

    # ── Drain detection — check main line before generic drain ────────────────
    if not task_code and any(kw in msg for kw in ["sewer", "main line", "main drain", "main stoppage"]):
        task_code, confidence = "MAIN_LINE_CLEAN", 0.88

    # ── All other jobs — keyword matching ─────────────────────────────────────
    if not task_code:
        for code, cfg in TASK_KEYWORDS.items():
            if any(kw in msg for kw in cfg.get("keywords", [])):
                task_code = cfg.get("task_override", code)
                assembly_code = cfg.get("assembly")
                confidence = 0.88
                break

    return {
        "task_code":          task_code,
        "assembly_code":      assembly_code,
        "access_type":        access_type,
        "urgency":            urgency,
        "county":             county,
        "preferred_supplier": preferred_supplier,
        "confidence":         confidence,
        "raw_message":        message,
    }


def format_estimate_response(result: EstimateResult, classification: dict, message: str) -> dict:
    """Format EstimateResult into a clear, structured chat response."""

    template = get_template(result.template_code or "")
    template_name = template.name if template else result.template_code

    # Supplier used for materials
    mat_suppliers = list({li.supplier for li in result.line_items if li.line_type == "material" and li.supplier})
    supplier_note = mat_suppliers[0].replace("_", " ").title() if len(mat_suppliers) == 1 else "lowest-cost DFW supplier"

    urgency = classification.get("urgency", "standard")
    access  = classification.get("access_type", "first_floor")

    access_label = {
        "first_floor": "1st floor", "second_floor": "2nd floor", "attic": "attic",
        "crawlspace": "crawlspace", "slab": "slab", "basement": "basement",
    }.get(access, access)

    lines = [
        f"**${result.grand_total:,.0f}** — {template_name}",
        "",
        f"| Line | Amount |",
        f"|------|--------|",
        f"| Labor | ${result.labor_total:,.0f} |",
        f"| Materials | ${result.materials_total:,.0f} |",
    ]
    if result.markup_total > 0:
        lines.append(f"| Materials markup | ${result.markup_total:,.0f} |")
    if result.misc_total > 0:
        lines.append(f"| Misc / Disposal | ${result.misc_total:,.0f} |")
    if result.tax_total > 0:
        lines.append(f"| Tax ({result.county} Co.) | ${result.tax_total:,.2f} |")
    lines += [
        "",
        f"**Confidence: {result.confidence_label}** ({int(result.confidence_score*100)}%) · "
        f"Location: {access_label} · Supplier: {supplier_note}",
    ]
    if urgency != "standard":
        lines.append(f"⚡ {urgency.replace('_', '-').title()} pricing applied")
    if result.assumptions:
        lines += ["", "_Note: " + " · ".join(result.assumptions[:2]) + "_"]

    return {
        "answer":             "\n".join(lines),
        "estimate": {
            "labor_total":    result.labor_total,
            "materials_total":result.materials_total,
            "tax_total":      result.tax_total,
            "markup_total":   result.markup_total,
            "misc_total":     result.misc_total,
            "subtotal":       result.subtotal,
            "grand_total":    result.grand_total,
            "line_items": [
                {
                    "line_type":    li.line_type,
                    "description":  li.description,
                    "quantity":     li.quantity,
                    "unit":         li.unit,
                    "unit_cost":    li.unit_cost,
                    "total_cost":   li.total_cost,
                    "supplier":     li.supplier,
                    "sku":          li.sku,
                }
                for li in result.line_items
            ],
        },
        "confidence":         result.confidence_score,
        "confidence_label":   result.confidence_label,
        "assumptions":        result.assumptions,
        "sources":            result.sources,
        "job_type_detected":  result.job_type,
        "template_used":      result.template_code,
        "classification":     classification,
    }


async def process_chat_message(
    message: str,
    county: Optional[str] = None,
    preferred_supplier: Optional[str] = None,
    job_type: Optional[str] = None,
    db=None,
) -> dict:
    """
    Main entry point: classify → fetch materials → price (deterministic) → format.
    """
    classification = classify_request(message)
    if county:
        classification["county"] = county
    if preferred_supplier:
        classification["preferred_supplier"] = preferred_supplier

    task_code     = classification.get("task_code")
    assembly_code = classification.get("assembly_code")

    if not task_code:
        return {
            "answer": (
                "I can price any DFW plumbing service. Try:\n"
                "- _Replace 50G gas water heater in attic — Dallas_\n"
                "- _Toilet replacement upstairs — Plano_\n"
                "- _Emergency PRV valve replace — Fort Worth_\n"
                "- _Drain cleaning — Frisco_"
            ),
            "estimate":         None,
            "confidence":       0.0,
            "confidence_label": "LOW",
            "assumptions":      ["Job type not recognized — try rephrasing"],
            "sources":          [],
        }

    # Fetch material costs
    materials: list[MaterialItem] = []
    if assembly_code:
        materials = await supplier_service.get_assembly_costs(
            assembly_code,
            preferred_supplier=classification.get("preferred_supplier"),
            db=db,
        )

    # Deterministic pricing — sync, no I/O
    result = pricing_engine.calculate_service_estimate(
        task_code=task_code,
        materials=materials,
        assembly_code=assembly_code,
        access=classification["access_type"],
        urgency=classification["urgency"],
        county=classification["county"],
        preferred_supplier=classification.get("preferred_supplier"),
    )

    response = format_estimate_response(result, classification, message)
    response["_estimate_result"] = result
    return response
