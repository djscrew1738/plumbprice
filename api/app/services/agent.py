"""
LLM Agent Orchestrator — Classifies and routes pricing requests.
RULE: Agent classifies and routes. PricingEngine calculates. Never the reverse.

Classification pipeline (in order):
  1. Keyword classifier  — fast, deterministic, always runs first
  2. Hermes LLM          — called when keyword confidence < threshold or no match
  3. Unclassified         — polite fallback if neither resolves a task_code
"""

import re
from typing import Optional
import structlog

from app.config import settings
from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template, LABOR_TEMPLATES as LABOR_MAP
from app.services.llm_service import llm_service

logger = structlog.get_logger()

# Word-to-digit map for spoken quantities
_WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}


def _extract_quantity(msg_lower: str) -> int:
    """Extract a quantity from natural language (e.g. '3 toilets', 'two faucets')."""
    # Digit first: e.g. "3 toilets", "replace 4 angle stops"
    m = re.search(r'\b([2-9]|1[0-9]|20)\b', msg_lower)
    if m:
        return int(m.group(1))
    # Word numbers
    for word, val in _WORD_NUMBERS.items():
        if re.search(rf'\b{word}\b', msg_lower):
            return val
    return 1


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
        "assembly": "TOILET_INSTALL_KIT",
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
    "TOILET_FLAPPER_REPLACE": {
        "keywords": ["flapper", "running toilet", "toilet running", "toilet won't stop", "toilet keeps running",
                     "toilet runs", "phantom flush", "ghost flush", "water wasting toilet"],
        "actions": ["replace", "fix", "repair", "stop"],
        "assembly": "TOILET_FLAPPER_KIT",
        "default_access": "first_floor",
    },
    "TOILET_FILL_VALVE_REPLACE": {
        "keywords": ["fill valve", "toilet fill", "ballcock", "toilet hissing", "hissing toilet",
                     "toilet constantly filling", "toilet tank slow"],
        "actions": ["replace", "fix", "repair"],
        "assembly": "TOILET_FILL_VALVE_KIT",
        "default_access": "first_floor",
    },
    "TOILET_COMFORT_HEIGHT": {
        "keywords": ["comfort height", "ada toilet", "tall toilet", "elongated comfort", "raised toilet",
                     "accessibility toilet", "handicap toilet"],
        "actions": ["replace", "install", "swap"],
        "assembly": "TOILET_COMFORT_HEIGHT_KIT",
        "default_access": "first_floor",
    },
    "TUB_SPOUT_REPLACE": {
        "keywords": ["tub spout", "bathtub spout", "tub faucet spout", "spout replace", "tub dripping spout"],
        "actions": ["replace", "install", "fix"],
        "assembly": "TUB_SPOUT_KIT",
        "default_access": "first_floor",
    },
    "SHOWER_HEAD_REPLACE": {
        "keywords": ["shower head", "showerhead", "shower nozzle", "rain head", "handheld shower"],
        "actions": ["replace", "install", "upgrade", "swap"],
        "assembly": "SHOWER_HEAD_KIT",
        "default_access": "first_floor",
    },
    "LAV_SINK_REPLACE": {
        "keywords": ["bathroom sink", "lav sink", "vanity sink", "lavatory sink", "sink replace",
                     "pedestal sink"],
        "actions": ["replace", "install", "swap"],
        "assembly": "LAV_SINK_KIT",
        "default_access": "first_floor",
    },
    "GAS_SHUTOFF_REPLACE": {
        "keywords": ["gas shutoff", "gas shut off", "gas valve", "appliance shutoff", "gas cock"],
        "actions": ["replace", "install", "fix"],
        "assembly": "GAS_SHUTOFF_KIT",
        "default_access": "first_floor",
    },
    "CLEAN_OUT_INSTALL": {
        "keywords": ["clean out install", "add clean out", "cleanout install", "need a clean out",
                     "no clean out", "add cleanout"],
        "actions": ["install", "add", "cut in"],
        "assembly": "CLEAN_OUT_KIT",
        "default_access": "first_floor",
    },
    "CAMERA_INSPECTION": {
        "keywords": ["camera inspection", "camera line", "video inspection", "scope the line", "sewer camera",
                     "drain camera", "scope drain"],
        "actions": ["inspect", "scope", "camera"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "DRAIN_CLEAN_STANDARD": {
        "keywords": ["drain clean", "clogged drain", "slow drain", "drain snake", "sink clog", "tub clog",
                     "shower drain clog", "blocked drain"],
        "actions": ["clean", "unclog", "clear", "snake"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "MAIN_LINE_CLEAN": {
        "keywords": ["main line", "main drain", "sewer line", "main sewer", "rooter", "root intrusion"],
        "actions": ["clean", "clear", "snake", "rooter"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "HYDROJETTING": {
        "keywords": ["hydro jet", "hydrojet", "hydrojetting", "jetting", "high pressure clean", "water jet drain"],
        "actions": ["jet", "clean", "clear"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "SLAB_LEAK_REPAIR": {
        "keywords": ["slab leak", "under slab", "foundation leak", "concrete leak", "slab pipe"],
        "actions": ["repair", "fix", "locate", "reroute"],
        "assembly": None,
        "default_access": "slab",
    },
    "LEAK_DETECTION": {
        "keywords": ["leak detection", "find the leak", "locate leak", "leak locate", "water leak find",
                     "detect leak"],
        "actions": ["detect", "find", "locate"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "WATER_SOFTENER_INSTALL": {
        "keywords": ["water softener", "softener", "water conditioner", "salt system", "ion exchange",
                     "water treatment"],
        "actions": ["install", "replace", "add"],
        "assembly": "WATER_SOFTENER_KIT",
        "default_access": "first_floor",
    },
    "TUB_SHOWER_COMBO_REPLACE": {
        "keywords": ["tub faucet", "tub valve", "bathtub faucet", "tub shower valve", "bath valve",
                     "tub diverter", "roman tub"],
        "actions": ["replace", "install", "fix", "repair"],
        "assembly": "TUB_SHOWER_VALVE_KIT",
        "default_access": "first_floor",
    },
    "EXPANSION_TANK_ONLY": {
        "keywords": ["expansion tank", "thermal expansion", "expansion vessel"],
        "actions": ["add", "install", "replace"],
        "assembly": "EXPANSION_TANK_KIT",
        "default_access": "first_floor",
    },
    "GAS_LINE_REPAIR_MINOR": {
        "keywords": ["gas line", "gas leak", "gas repair", "gas fitting", "gas valve repair"],
        "actions": ["repair", "fix", "replace"],
        "assembly": None,
        "default_access": "first_floor",
    },
    "GAS_LINE_NEW_RUN": {
        "keywords": ["new gas line", "gas line run", "gas line install", "add gas line", "gas connection"],
        "actions": ["install", "run", "add"],
        "assembly": None,
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
                # Higher confidence when an action word also matches
                action_kws = cfg.get("actions", [])
                if action_kws and any(a in msg_lower for a in action_kws):
                    confidence = 0.88
                else:
                    confidence = 0.75
                break

    # Extract preferred supplier
    preferred_supplier = None
    for sup in ["ferguson", "moore supply", "moore_supply", "apex"]:
        if sup.replace("_", " ") in msg_lower:
            preferred_supplier = sup.replace(" ", "_")
            break

    quantity = _extract_quantity(msg_lower)

    return {
        "task_code": task_code,
        "assembly_code": assembly_code,
        "access_type": access_type,
        "urgency": urgency,
        "county": county,
        "preferred_supplier": preferred_supplier,
        "confidence": confidence,
        "quantity": quantity,
        "raw_message": message,
    }


def _format_breakdown(result: EstimateResult, quantity: int) -> str:
    """Build the structured cost breakdown section (always shown)."""
    lines = []
    if quantity > 1:
        lines.append(f"**Total: ${result.grand_total:,.0f}** _(×{quantity} units — ${result.grand_total / quantity:,.0f} each)_")
    else:
        lines.append(f"**Total: ${result.grand_total:,.0f}**")
    lines.append("")
    lines.append(f"• Labor: **${result.labor_total:,.0f}**")
    lines.append(f"• Materials: **${result.materials_total:,.0f}**")
    if result.markup_total > 0:
        lines.append(f"• Materials markup: ${result.markup_total:,.0f}")
    if result.misc_total > 0:
        lines.append(f"• Misc/Disposal: ${result.misc_total:,.0f}")
    lines.append(f"• Tax ({result.county} County): ${result.tax_total:,.2f}")
    lines.append("")
    lines.append(f"**Confidence: {result.confidence_label}** ({int(result.confidence_score * 100)}%)")
    if result.assumptions:
        lines.append("")
        lines.append("_Assumptions:_")
        for a in result.assumptions[:3]:
            lines.append(f"• {a}")
    return "\n".join(lines)


def format_estimate_response(
    result: EstimateResult,
    classification: dict,
    message: str,
    llm_opener: Optional[str] = None,
) -> dict:
    """Format EstimateResult into a user-friendly chat response.

    If llm_opener is provided (Hermes-generated text), it is prepended to the
    structured breakdown. Otherwise the breakdown leads with the price headline.
    """
    template = get_template(result.template_code or "")
    template_name = template.name if template else result.template_code
    quantity = classification.get("quantity", 1)

    breakdown = _format_breakdown(result, quantity)

    if llm_opener:
        # Hermes wrote the opener — put it first, then the numbers
        answer = f"{llm_opener}\n\n{breakdown}"
    else:
        # Fallback: lead with the template name then the breakdown
        header = f"_{template_name}_\n\n" if template_name else ""
        answer = header + breakdown

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

    Pipeline:
      1. Keyword classify  (fast, always runs)
      2. LLM classify      (Hermes 3 via Ollama — runs when keyword confidence
                            is below threshold or no task matched)
      3. Deterministic price (PricingEngine — never bypassed)
      4. LLM response      (natural language opener — optional, falls back to
                            template if Hermes unavailable)
    """

    # ── Step 1: Keyword classification (fast path) ───────────────────────────
    classification = classify_request(message)

    # Caller-supplied overrides take precedence
    if county:
        classification["county"] = county
    if preferred_supplier:
        classification["preferred_supplier"] = preferred_supplier

    keyword_task_code  = classification.get("task_code")
    keyword_confidence = classification.get("confidence", 0.0)
    threshold          = settings.llm_classify_threshold

    # ── Step 2: LLM classification (escalation path) ─────────────────────────
    # Escalate when: no keyword match OR confidence below threshold
    classified_by = "keyword"
    if not keyword_task_code or keyword_confidence < threshold:
        llm_result = await llm_service.classify(message)
        if llm_result and llm_result.get("task_code"):
            # LLM resolved the intent — merge into classification
            for key in ("task_code", "access_type", "urgency", "quantity"):
                if llm_result.get(key) is not None:
                    classification[key] = llm_result[key]

            # Override county only when keyword didn't detect one and caller
            # didn't supply one
            if not county and llm_result.get("county"):
                classification["county"] = llm_result["county"]

            if not preferred_supplier and llm_result.get("preferred_supplier"):
                classification["preferred_supplier"] = llm_result["preferred_supplier"]

            # Inject assembly from TASK_KEYWORDS if LLM resolved a task_code
            # that the keyword classifier missed
            new_task = classification["task_code"]
            if not classification.get("assembly_code") and new_task in TASK_KEYWORDS:
                classification["assembly_code"] = TASK_KEYWORDS[new_task].get("assembly")

            classification["confidence"] = llm_result.get("confidence", 0.85)
            classified_by = "llm"

            logger.info(
                "LLM classification upgraded keyword result",
                keyword_task=keyword_task_code,
                llm_task=new_task,
                confidence=classification["confidence"],
            )

    classification["classified_by"] = classified_by

    # ── Unclassifiable ────────────────────────────────────────────────────────
    task_code    = classification.get("task_code")
    assembly_code = classification.get("assembly_code")

    if not task_code:
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

    quantity = classification.get("quantity", 1)
    preferred_supplier = classification.get("preferred_supplier")

    # ── Steps 3+4: Material costs + Deterministic pricing ────────────────────
    # Fast path: no DB → use pure in-memory canonical map (zero DB round-trips)
    # Standard path: DB session present → single batched query for all assembly items
    if not db:
        result = pricing_engine.quick_estimate(
            task_code=task_code,
            assembly_code=assembly_code,
            access=classification["access_type"],
            urgency=classification["urgency"],
            county=classification["county"],
            preferred_supplier=preferred_supplier,
            quantity=quantity,
        )
    else:
        materials: list[MaterialItem] = []
        if assembly_code:
            materials = await supplier_service.get_assembly_costs(
                assembly_code,
                preferred_supplier=preferred_supplier,
                db=db,
            )
        result = pricing_engine.calculate_service_estimate(
            task_code=task_code,
            materials=materials,
            assembly_code=assembly_code,
            access=classification["access_type"],
            urgency=classification["urgency"],
            county=classification["county"],
            preferred_supplier=preferred_supplier,
        )
        if quantity > 1:
            result = pricing_engine.scale_estimate(result, quantity)

    # ── Step 5: LLM response generation (optional) ───────────────────────────
    template      = get_template(result.template_code or "")
    template_name = template.name if template else (result.template_code or "")

    llm_opener = await llm_service.generate_response(
        message=message,
        grand_total=result.grand_total,
        labor_total=result.labor_total,
        materials_total=result.materials_total,
        tax_total=result.tax_total,
        template_name=template_name,
        county=result.county,
        quantity=quantity,
    )

    # ── Step 6: Format final response ────────────────────────────────────────
    response = format_estimate_response(result, classification, message, llm_opener=llm_opener)
    response["_estimate_result"] = result  # raw, for callers (not serialised)
    return response
