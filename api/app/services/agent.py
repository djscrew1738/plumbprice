"""
LLM Agent Orchestrator — Classifies and routes pricing requests.
RULE: Agent classifies and routes. PricingEngine calculates. Never the reverse.
"""

import json
import re
from typing import Optional, Any
import structlog

from app.config import settings
from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template, LABOR_TEMPLATES as LABOR_MAP

logger = structlog.get_logger()


# ─── Job Classification ───────────────────────────────────────────────────────

TASK_KEYWORDS: dict[str, dict] = {
    "TOILET_REPLACE_STANDARD": {
        "keywords": ["toilet", "commode", "throne", "water closet", "wc"],
        "actions": ["replace", "install", "swap", "new", "fix"],
        "assembly": "TOILET_INSTALL_KIT",
        "default_access": "first_floor",
    },
    "TOILET_COMFORT_HEIGHT": {
        "keywords": ["comfort height", "ada toilet", "tall toilet", "elongated comfort"],
        "actions": ["replace", "install"],
        "assembly": "TOILET_COMFORT_HEIGHT_KIT",
        "default_access": "first_floor",
    },
    "WH_50G_GAS_STANDARD": {
        "keywords": ["water heater", "hot water heater", "50 gallon", "50g", "gas water heater"],
        "actions": ["replace", "install", "new", "swap"],
        "assembly": "WH_50G_GAS_KIT",
        "default_access": "first_floor",
    },
    "WH_50G_GAS_ATTIC": {
        "keywords": ["water heater", "hot water heater"],
        "access_required": "attic",
        "assembly": "WH_50G_GAS_ATTIC_KIT",
        "default_access": "attic",
    },
    "WH_40G_GAS_STANDARD": {
        "keywords": ["40 gallon", "40g", "water heater"],
        "actions": ["replace", "install"],
        "assembly": "WH_40G_GAS_KIT",
        "default_access": "first_floor",
    },
    "WH_50G_ELECTRIC_STANDARD": {
        "keywords": ["electric water heater", "electric wh"],
        "actions": ["replace", "install"],
        "assembly": "WH_50G_ELECTRIC_KIT",
        "default_access": "first_floor",
    },
    "WH_TANKLESS_GAS": {
        "keywords": ["tankless", "on demand", "instantaneous", "combi"],
        "actions": ["install", "replace"],
        "assembly": "WH_TANKLESS_GAS_KIT",
        "default_access": "first_floor",
    },
    "PRV_REPLACE": {
        "keywords": ["prv", "pressure reducing valve", "pressure regulator", "pressure reducer"],
        "actions": ["replace", "install", "fix"],
        "assembly": "PRV_KIT",
        "default_access": "first_floor",
    },
    "HOSE_BIB_REPLACE": {
        "keywords": ["hose bib", "hose bibb", "outdoor faucet", "sillcock", "outside faucet"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "HOSE_BIB_KIT",
        "default_access": "first_floor",
    },
    "SHOWER_VALVE_REPLACE": {
        "keywords": ["shower valve", "shower cartridge", "shower mixing valve", "shower faucet"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "SHOWER_VALVE_KIT",
        "default_access": "first_floor",
    },
    "KITCHEN_FAUCET_REPLACE": {
        "keywords": ["kitchen faucet", "kitchen sink faucet", "kitchen tap"],
        "actions": ["replace", "install", "swap"],
        "assembly": "KITCHEN_FAUCET_KIT",
        "default_access": "first_floor",
    },
    "GARBAGE_DISPOSAL_INSTALL": {
        "keywords": ["disposal", "garbage disposal", "insinkerator", "food disposal", "garburator"],
        "actions": ["install", "replace", "swap"],
        "assembly": "DISPOSAL_KIT",
        "default_access": "first_floor",
    },
    "LAV_FAUCET_REPLACE": {
        "keywords": ["bathroom faucet", "lavatory faucet", "lav faucet", "sink faucet", "bath faucet"],
        "actions": ["replace", "install", "swap"],
        "assembly": "LAV_FAUCET_KIT",
        "default_access": "first_floor",
    },
    "ANGLE_STOP_REPLACE": {
        "keywords": ["angle stop", "shutoff valve", "shut off valve", "stop valve", "angle valve"],
        "actions": ["replace", "install", "fix"],
        "assembly": "ANGLE_STOP_KIT",
        "default_access": "first_floor",
    },
    "PTRAP_REPLACE": {
        "keywords": ["p-trap", "ptrap", "p trap", "drain trap"],
        "actions": ["replace", "install", "fix"],
        "assembly": "PTRAP_KIT",
        "default_access": "first_floor",
    },
}

ACCESS_KEYWORDS = {
    "attic": ["attic", "in the attic", "attic install"],
    "second_floor": ["second floor", "2nd floor", "upstairs", "second story", "2nd story"],
    "crawlspace": ["crawl space", "crawlspace", "under the house", "crawl"],
    "slab": ["slab", "slab foundation"],
    "basement": ["basement"],
    "first_floor": ["first floor", "1st floor", "ground floor", "downstairs"],
}

URGENCY_KEYWORDS = {
    "emergency": ["emergency", "urgent", "asap", "right now", "immediately", "tonight", "flooding"],
    "same_day": ["same day", "today", "this afternoon", "this morning"],
    "standard": [],
}

COUNTY_KEYWORDS = {
    "dallas": ["dallas", "highland park", "university park", "desoto", "duncanville", "garland", "mesquite", "richardson", "rowlett"],
    "tarrant": ["fort worth", "arlington", "mansfield", "burleson", "hurst", "bedford", "euless", "grapevine", "north richland hills"],
    "collin": ["plano", "mckinney", "frisco", "allen", "prosper", "celina", "wylie", "murphy"],
    "denton": ["denton", "lewisville", "flower mound", "coppell", "carrollton", "the colony", "little elm"],
    "rockwall": ["rockwall", "royse city", "heath"],
    "parker": ["weatherford", "aledo", "willow park"],
}


def classify_request(message: str) -> dict:
    """
    Rule-based classification of plumbing service request.
    Returns: {task_code, assembly_code, access_type, urgency, county, confidence, detected}
    """
    msg_lower = message.lower()

    # Detect urgency first
    urgency = "standard"
    for urg, keywords in URGENCY_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            urgency = urg
            break

    # Detect access type
    access_type = "first_floor"
    for access, keywords in ACCESS_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            access_type = access
            break

    # Detect county
    county = "Dallas"
    for county_name, keywords in COUNTY_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            county = county_name.capitalize()
            break

    # Detect task — check for attic water heater first (special case)
    task_code = None
    assembly_code = None
    confidence = 0.7

    if "water heater" in msg_lower or "hot water" in msg_lower:
        if access_type == "attic" or "attic" in msg_lower:
            task_code = "WH_50G_GAS_ATTIC"
            assembly_code = "WH_50G_GAS_ATTIC_KIT"
            confidence = 0.85
        elif "tankless" in msg_lower or "on demand" in msg_lower:
            task_code = "WH_TANKLESS_GAS"
            assembly_code = "WH_TANKLESS_GAS_KIT"
            confidence = 0.90
        elif "electric" in msg_lower:
            task_code = "WH_50G_ELECTRIC_STANDARD"
            assembly_code = "WH_50G_ELECTRIC_KIT"
            confidence = 0.85
        elif re.search(r'\b40\b', msg_lower):
            task_code = "WH_40G_GAS_STANDARD"
            assembly_code = "WH_40G_GAS_KIT"
            confidence = 0.85
        else:
            task_code = "WH_50G_GAS_STANDARD"
            assembly_code = "WH_50G_GAS_KIT"
            confidence = 0.80  # assume 50G gas unless told otherwise

    else:
        for code, cfg in TASK_KEYWORDS.items():
            kws = cfg.get("keywords", [])
            if any(kw in msg_lower for kw in kws):
                task_code = code
                assembly_code = cfg.get("assembly")
                confidence = 0.88
                break

    # Extract preferred supplier
    preferred_supplier = None
    for sup in ["ferguson", "moore supply", "moore_supply", "apex"]:
        if sup.replace("_", " ") in msg_lower:
            preferred_supplier = sup.replace(" ", "_")
            break

    return {
        "task_code": task_code,
        "assembly_code": assembly_code,
        "access_type": access_type,
        "urgency": urgency,
        "county": county,
        "preferred_supplier": preferred_supplier,
        "confidence": confidence,
        "raw_message": message,
    }


def format_estimate_response(
    result: EstimateResult,
    classification: dict,
    message: str,
) -> dict:
    """Format EstimateResult into a user-friendly chat response."""

    template = get_template(result.template_code or "")
    template_name = template.name if template else result.template_code

    # Build human-readable answer
    lines = []
    lines.append(f"**Recommended Price: ${result.grand_total:,.0f}**")
    lines.append("")
    if template_name:
        lines.append(f"_{template_name}_")
    lines.append("")
    lines.append(f"• Labor: **${result.labor_total:,.0f}**")
    lines.append(f"• Materials: **${result.materials_total:,.0f}**")
    if result.markup_total > 0:
        lines.append(f"• Materials markup: ${result.markup_total:,.0f}")
    if result.misc_total > 0:
        lines.append(f"• Misc/Disposal: ${result.misc_total:,.0f}")
    lines.append(f"• Tax ({result.county} County): ${result.tax_total:,.2f}")
    lines.append("")
    lines.append(f"**Confidence: {result.confidence_label}** ({int(result.confidence_score*100)}%)")

    if result.assumptions:
        lines.append("")
        lines.append("_Assumptions:_")
        for assumption in result.assumptions[:3]:
            lines.append(f"• {assumption}")

    answer = "\n".join(lines)

    return {
        "answer": answer,
        "estimate": {
            "labor_total": result.labor_total,
            "materials_total": result.materials_total,
            "tax_total": result.tax_total,
            "markup_total": result.markup_total,
            "misc_total": result.misc_total,
            "subtotal": result.subtotal,
            "grand_total": result.grand_total,
            "line_items": [
                {
                    "line_type": li.line_type,
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_cost": li.unit_cost,
                    "total_cost": li.total_cost,
                    "supplier": li.supplier,
                    "sku": li.sku,
                }
                for li in result.line_items
            ],
        },
        "confidence": result.confidence_score,
        "confidence_label": result.confidence_label,
        "assumptions": result.assumptions,
        "sources": result.sources,
        "job_type_detected": result.job_type,
        "template_used": result.template_code,
        "classification": classification,
    }


async def process_chat_message(
    message: str,
    county: Optional[str] = None,
    preferred_supplier: Optional[str] = None,
    job_type: Optional[str] = None,
    db=None,
) -> dict:
    """
    Main entry point for chat pricing requests.
    1. Classify → 2. Fetch materials → 3. Price (deterministic) → 4. Format
    """

    # Step 1: Classify
    classification = classify_request(message)
    if county:
        classification["county"] = county
    if preferred_supplier:
        classification["preferred_supplier"] = preferred_supplier

    task_code = classification.get("task_code")
    assembly_code = classification.get("assembly_code")

    if not task_code:
        # Can't classify — return helpful message
        return {
            "answer": (
                "I can help price plumbing services! Try asking something like:\n"
                "• _How much to replace a water heater in the attic?_\n"
                "• _Price to replace a toilet first floor_\n"
                "• _Cost for a kitchen faucet in Dallas_"
            ),
            "estimate": None,
            "confidence": 0.0,
            "confidence_label": "LOW",
            "assumptions": ["Could not classify job type from message"],
            "sources": [],
        }

    # Step 2: Get material costs
    materials: list[MaterialItem] = []
    if assembly_code:
        materials = await supplier_service.get_assembly_costs(
            assembly_code,
            preferred_supplier=classification.get("preferred_supplier"),
            db=db,
        )

    # Step 3: Deterministic pricing
    result = await pricing_engine.calculate_service_estimate(
        task_code=task_code,
        materials=materials,
        assembly_code=assembly_code,
        access=classification["access_type"],
        urgency=classification["urgency"],
        county=classification["county"],
        preferred_supplier=classification.get("preferred_supplier"),
        db=db,
    )

    # Step 4: Format
    response = format_estimate_response(result, classification, message)
    response["_estimate_result"] = result  # raw result for callers that need it (not serialized)
    return response
