"""
Agent v3 — Tool-calling AI orchestrator for PlumbPrice 3.0

Evolves from v1's "classify → price" pipeline to an agentic system that:
1. Classifies with structured Pydantic outputs + reasoning
2. Calls tools in parallel to gather real-time data
3. Applies dynamic market pricing transparently
4. Returns full agent traces for auditability

RULE: Agent reasons and gathers data. PricingEngine calculates. Never the reverse.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field, replace
from typing import Optional, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_structured import llm_structured, ClassifyResult
from app.services.market_pricing import market_pricing_engine
from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem, LineItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template
from app.services.llm_service import llm_service
from app.services.task_code_embeddings import task_code_embedding_service
from app.services.memory_service import memory_service
from app.services.intake_agent import infer_intake, IntakeResult as IntakeAgentResult
from app.services.revision_suggestions import suggest_revisions, RevisionSuggestion
from app.config import settings

logger = structlog.get_logger()


# ── Tool Call Result Types ────────────────────────────────────────────────────

@dataclass
class ToolCallResult:
    tool_name: str
    arguments: dict
    result: Any
    latency_ms: int = 0
    error: Optional[str] = None


@dataclass
class SuggestedContext:
    """Proactive suggestion for missing context based on user memories."""
    field: str  # county | preferred_supplier | job_type | access_type
    value: str
    reason: str
    confidence: float = 0.8


@dataclass
class AgentV3Result:
    """Complete result from the v3 agent pipeline."""
    classification: ClassifyResult
    estimate: EstimateResult
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    market_adjustments_applied: list[dict] = field(default_factory=list)
    overall_market_factor: float = 1.0
    narrative: Optional[str] = None
    clarification_questions: Optional[list[str]] = None
    suggested_context: list[SuggestedContext] = field(default_factory=list)
    classified_by: str = "keyword"
    agent_trace: dict = field(default_factory=dict)
    estimate_diff: Optional[dict] = None
    blueprint_seeded: bool = False
    intake_result: Optional[IntakeAgentResult] = None
    revision_suggestions: list[RevisionSuggestion] = field(default_factory=list)


@dataclass
class RevisionDelta:
    """Parsed delta from a revision request."""
    new_task_code: Optional[str] = None
    quantity_delta: int = 0
    new_access_type: Optional[str] = None
    new_urgency: Optional[str] = None
    notes: str = ""


_REVISION_KEYWORDS = {
    "upgrade", "downgrade", "add", "remove", "swap", "change",
    "instead of", "switch to", "replace with", "make it", "bigger",
    "smaller", "larger", "extra", "additional", "another", "second",
    "third", "both", "pair", "remove the", "take out", "delete",
    "get rid of", "upsize", "downsize",
}

# Fixture types from vision pipeline → task code prefixes for quantity seeding.
_FIXTURE_TO_TASK_PATTERNS: dict[str, list[str]] = {
    "toilet": ["TOILET"],
    "water_closet": ["TOILET"],
    "wc": ["TOILET"],
    "lavatory": ["LAV_"],
    "lav": ["LAV_"],
    "bathroom_sink": ["LAV_", "SINK_REPLACE_BATH"],
    "sink": ["KITCHEN_FAUCET", "SINK_REPLACE_KITCHEN", "KITCHEN_SINK"],
    "kitchen_sink": ["KITCHEN_FAUCET", "SINK_REPLACE_KITCHEN", "KITCHEN_SINK"],
    "shower": ["SHOWER_"],
    "tub": ["TUB_"],
    "bathtub": ["TUB_"],
    "tub_shower": ["TUB_SHOWER", "TUB_", "SHOWER_"],
    "water_heater": ["WH_", "WATER_HEATER"],
    "wh": ["WH_", "WATER_HEATER"],
    "disposal": ["GARBAGE_DISPOSAL"],
    "garbage_disposal": ["GARBAGE_DISPOSAL"],
    "dishwasher": ["DISHWASHER"],
    "hose_bib": ["HOSE_BIB"],
    "prv": ["PRV_"],
}


def _seed_quantity_from_blueprint(task_code: str, fixtures: dict[str, int]) -> tuple[int, str] | None:
    """Return (quantity, fixture_type) if the task maps to a blueprint-detected fixture."""
    if not task_code or not fixtures:
        return None
    tc = task_code.upper()
    for fixture_type, patterns in _FIXTURE_TO_TASK_PATTERNS.items():
        count = fixtures.get(fixture_type)
        if not count:
            continue
        for pat in patterns:
            if pat in tc:
                return (count, fixture_type)
    return None


# Assembly code variants for budget / premium tiers.
# Maps a standard assembly → dict with optional budget/premium alternatives.
# If an alternative doesn't exist, the standard assembly is used.
_VARIANT_ASSEMBLY_MAP: dict[str, dict[str, str]] = {
    "WH_50G_GAS_KIT": {"premium": "WH_TANKLESS_GAS_KIT"},
    "WH_50G_ELECTRIC_KIT": {"premium": "WH_TANKLESS_ELECTRIC_KIT"},
    "TOILET_INSTALL_KIT": {"premium": "SMART_TOILET_KIT", "budget": "TOILET_FILL_VALVE_KIT"},
    "LAV_SINK_KIT": {"premium": "BATH_SINK_KIT"},
    "KITCHEN_FAUCET_KIT": {"premium": "BATH_SINK_KIT"},
    "SHOWER_VALVE_KIT": {"premium": "ANTI_SCALD_KIT"},
    "TUB_SHOWER_VALVE_KIT": {"premium": "ANTI_SCALD_KIT"},
    "DISPOSAL_KIT": {"premium": "DISPOSAL_HP_KIT"},
}

# Labor template variants for budget / premium tiers.
_VARIANT_LABOR_MAP: dict[str, dict[str, str]] = {
    "WH_50G_GAS_STANDARD": {"premium": "WH_TANKLESS_GAS_STANDARD"},
    "WH_50G_ELECTRIC_STANDARD": {"premium": "WH_TANKLESS_ELECTRIC_STANDARD"},
}


def _resolve_variant_assembly(standard_assembly: str, tier: str) -> str:
    """Return the assembly code for a given tier, falling back to standard."""
    if tier == "standard":
        return standard_assembly
    mapping = _VARIANT_ASSEMBLY_MAP.get(standard_assembly, {})
    return mapping.get(tier, standard_assembly)


def _resolve_variant_labor(standard_labor: str, tier: str) -> str:
    """Return the labor template code for a given tier, falling back to standard."""
    if tier == "standard":
        return standard_labor
    mapping = _VARIANT_LABOR_MAP.get(standard_labor, {})
    return mapping.get(tier, standard_labor)


def _build_variant_estimate(
    base_estimate: EstimateResult,
    tier: str,
    classification: ClassifyResult,
) -> EstimateResult:
    """Create a tiered variant from a base estimate by routing through the pricing engine.

    Budget:  reduce markup by 20%, remove misc line items, use economy assemblies.
    Premium: increase markup by 15%, add warranty line item, use upgraded assemblies.
    """
    variant_labor = _resolve_variant_labor(base_estimate.template_code or "", tier)
    variant_assembly = _resolve_variant_assembly(base_estimate.assembly_code or "", tier)

    # Route through the full pricing engine for correct base totals
    variant = pricing_engine.quick_estimate(
        task_code=variant_labor or base_estimate.template_code or "",
        assembly_code=variant_assembly or base_estimate.assembly_code,
        access=classification.access_type,
        urgency=classification.urgency,
        county=classification.county,
        city=classification.city,
        preferred_supplier=classification.preferred_supplier,
        quantity=classification.quantity,
    )

    if tier == "budget":
        # Reduce markup by 20%
        for li in variant.line_items:
            if li.line_type == "markup":
                li.unit_cost = round(li.unit_cost * 0.8, 2)
                li.total_cost = round(li.total_cost * 0.8, 2)
        # Remove misc items
        variant.line_items = [li for li in variant.line_items if li.line_type != "misc"]
        variant = pricing_engine.recompute_totals(variant)
        variant.assumptions = [*variant.assumptions, "Budget tier: economy materials, reduced markup"]

    elif tier == "premium":
        # Increase markup by 15%
        for li in variant.line_items:
            if li.line_type == "markup":
                li.unit_cost = round(li.unit_cost * 1.15, 2)
                li.total_cost = round(li.total_cost * 1.15, 2)
        # Add warranty line item
        warranty_li = LineItem(
            line_type="misc",
            description="Extended labor warranty (2-year parts & labor)",
            quantity=1,
            unit="ea",
            unit_cost=round(base_estimate.grand_total * 0.05, 2),
            total_cost=round(base_estimate.grand_total * 0.05, 2),
            canonical_item="warranty_premium",
        )
        variant.line_items.append(warranty_li)
        variant = pricing_engine.recompute_totals(variant)
        variant.assumptions = [*variant.assumptions, "Premium tier: upgraded materials, extended warranty"]

    return variant


def _detect_revision_intent(message: str) -> bool:
    """Quick heuristic: does the message look like a revision to a previous estimate?"""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in _REVISION_KEYWORDS)


async def _parse_revision_delta(
    message: str,
    previous_estimate: dict,
) -> Optional[RevisionDelta]:
    """Use a lightweight LLM prompt to parse what changed in a revision request.

    Returns None if the message doesn't contain a parseable revision.
    """
    system_prompt = """\
You are a plumbing estimator assistant. The user previously received an estimate and now wants to change it.
Parse their revision request into a JSON delta.

Previous estimate: {previous_task} with total ${previous_total}

Respond with JSON only:
{
  "new_task_code": "WH_75G_GAS_STANDARD or null if same task",
  "quantity_delta": 0,
  "new_access_type": "attic or null if same",
  "new_urgency": "emergency or null if same",
  "notes": "brief description of change"
}"""

    prev_task = previous_estimate.get("template_code", "unknown")
    prev_total = previous_estimate.get("grand_total", 0)

    prompt = system_prompt.format(previous_task=prev_task, previous_total=prev_total)

    client = llm_structured.make_structured_client(timeout=10.0)
    if client is None:
        return None

    try:
        response = await client.chat.completions.create(
            model=llm_structured._active_model(),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f'Revision request: "{message}"'},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=256,
        )
        raw = (response.choices[0].message.content or "{}").strip()
        import json as _json
        data = _json.loads(raw)
        return RevisionDelta(
            new_task_code=data.get("new_task_code") or None,
            quantity_delta=data.get("quantity_delta", 0),
            new_access_type=data.get("new_access_type") or None,
            new_urgency=data.get("new_urgency") or None,
            notes=data.get("notes", ""),
        )
    except Exception as exc:
        logger.warning("agent_v3.revision_parse_failed", error=str(exc))
        return None


def _compute_estimate_diff(old: EstimateResult, new: EstimateResult) -> dict:
    """Compute a structural diff between two estimates for frontend rendering."""
    old_items = {li.canonical_item or li.description: li for li in old.line_items}
    new_items = {li.canonical_item or li.description: li for li in new.line_items}

    added = []
    removed = []
    modified = []

    for key, li in new_items.items():
        if key not in old_items:
            added.append({
                "description": li.description,
                "quantity": li.quantity,
                "unit_cost": li.unit_cost,
                "total_cost": li.total_cost,
            })
        else:
            old_li = old_items[key]
            if abs(old_li.total_cost - li.total_cost) > 0.01 or old_li.quantity != li.quantity:
                modified.append({
                    "description": li.description,
                    "old_quantity": old_li.quantity,
                    "new_quantity": li.quantity,
                    "old_total": old_li.total_cost,
                    "new_total": li.total_cost,
                })

    for key, li in old_items.items():
        if key not in new_items:
            removed.append({
                "description": li.description,
                "quantity": li.quantity,
                "unit_cost": li.unit_cost,
                "total_cost": li.total_cost,
            })

    return {
        "previous_total": round(old.grand_total, 2),
        "new_total": round(new.grand_total, 2),
        "total_delta": round(new.grand_total - old.grand_total, 2),
        "added_line_items": added,
        "removed_line_items": removed,
        "modified_line_items": modified,
    }


async def _generate_suggested_context(
    db: AsyncSession,
    user_id: int,
    classification: ClassifyResult,
    memories: list[dict],
) -> list[SuggestedContext]:
    """Generate proactive suggestions for missing classification fields from memories."""
    suggestions: list[SuggestedContext] = []

    # County suggestion
    if not classification.county or classification.county == "Dallas":
        county_memories = [m for m in memories if "county" in m.get("content", "").lower()]
        if county_memories:
            content = county_memories[0]["content"]
            counties = ["Dallas", "Tarrant", "Collin", "Denton", "Rockwall", "Parker", "Kaufman", "Ellis", "Johnson"]
            for c in counties:
                if c.lower() in content.lower():
                    suggestions.append(SuggestedContext(
                        field="county",
                        value=c,
                        reason=f"From your past conversations: {content[:80]}",
                        confidence=round(county_memories[0].get("score", 0.5) or 0.5, 2),
                    ))
                    break

    # Supplier suggestion
    if not classification.preferred_supplier:
        supplier_memories = [m for m in memories if any(s in m.get("content", "").lower() for s in ["ferguson", "moore", "apex", "supplier"])]
        if supplier_memories:
            content = supplier_memories[0]["content"].lower()
            for supplier in ["ferguson", "moore_supply", "apex"]:
                if supplier.replace("_", "") in content or supplier in content:
                    suggestions.append(SuggestedContext(
                        field="preferred_supplier",
                        value=supplier,
                        reason=f"From your past conversations: {supplier_memories[0]['content'][:80]}",
                        confidence=round(supplier_memories[0].get("score", 0.5) or 0.5, 2),
                    ))
                    break

    # Access type suggestion
    if classification.access_type == "first_floor":
        access_memories = [m for m in memories if any(a in m.get("content", "").lower() for a in ["attic", "crawlspace", "slab", "basement", "second floor"])]
        if access_memories:
            content = access_memories[0]["content"].lower()
            access_map = {
                "attic": "attic",
                "crawlspace": "crawlspace",
                "slab": "slab",
                "basement": "basement",
                "second floor": "second_floor",
            }
            for keyword, access_type in access_map.items():
                if keyword in content:
                    suggestions.append(SuggestedContext(
                        field="access_type",
                        value=access_type,
                        reason=f"From your past conversations: {access_memories[0]['content'][:80]}",
                        confidence=round(access_memories[0].get("score", 0.5) or 0.5, 2),
                    ))
                    break

    return suggestions[:3]  # Cap at 3 suggestions


# ── Tool Registry ─────────────────────────────────────────────────────────────

class AgentTools:
    """Tools the v3 agent can call to gather pricing data."""

    @staticmethod
    async def search_materials(task_code: str, preferred_supplier: Optional[str] = None) -> dict:
        """Find material assembly and costs for a task code."""
        from app.services.data_sources.price_enrichment import get_enrichment_service

        assembly_code = _default_assembly_for_task(task_code)
        materials: list[MaterialItem] = []

        if assembly_code and assembly_code in MATERIAL_ASSEMBLIES:
            assembly = MATERIAL_ASSEMBLIES[assembly_code]
            enrichment = get_enrichment_service()
            for canonical_item, qty in assembly["items"].items():
                enriched_cost = enrichment.get_cached_cost(canonical_item)
                if enriched_cost is not None:
                    materials.append(MaterialItem(
                        canonical_item=canonical_item,
                        description=canonical_item.replace(".", " ").title(),
                        quantity=qty,
                        unit="ea",
                        unit_cost=enriched_cost,
                        supplier="enrichment",
                    ))
                else:
                    # Fallback to canonical map
                    prices = supplier_service.canonical_map.get(canonical_item, {})
                    if prices:
                        supplier = preferred_supplier or list(prices.keys())[0]
                        data = prices.get(supplier, list(prices.values())[0])
                        materials.append(MaterialItem(
                            canonical_item=canonical_item,
                            description=data["name"],
                            quantity=qty,
                            unit="ea",
                            unit_cost=data["cost"],
                            supplier=supplier,
                            sku=data.get("sku"),
                        ))

        return {
            "assembly_code": assembly_code,
            "material_count": len(materials),
            "materials": [
                {
                    "canonical_item": m.canonical_item,
                    "description": m.description,
                    "quantity": m.quantity,
                    "unit_cost": m.unit_cost,
                    "supplier": m.supplier,
                }
                for m in materials
            ],
        }

    @staticmethod
    async def get_labor_template(task_code: str, access: str = "first_floor", urgency: str = "standard") -> dict:
        """Fetch labor template data with multipliers applied."""
        template = get_template(task_code)
        if not template:
            return {"error": f"Unknown template: {task_code}"}

        labor_data = template.calculate_labor_cost(access=access, urgency=urgency)
        return {
            "code": template.code,
            "name": template.name,
            "category": template.category,
            "base_hours": template.base_hours,
            "adjusted_hours": labor_data["adjusted_hours"],
            "total_labor_cost": labor_data["total_labor_cost"],
            "access_multiplier": labor_data["access_multiplier"],
            "urgency_multiplier": labor_data["urgency_multiplier"],
            "lead_rate": template.lead_rate,
            "helper_required": template.helper_required,
        }

    @staticmethod
    async def lookup_permit_cost(task_code: str, county: str = "Dallas") -> dict:
        """Check if a task requires a permit and what it costs."""
        from app.services.pricing_engine import _PERMIT_REQUIRED
        from app.services.pricing_config_service import pricing_config_service

        permit_category = _PERMIT_REQUIRED.get(task_code)
        if not permit_category:
            return {"required": False, "cost": 0.0, "category": None}

        cost = pricing_config_service.get_permit_cost(county, permit_category)
        return {"required": True, "cost": cost, "category": permit_category}

# ── Helper ────────────────────────────────────────────────────────────────────

def _default_assembly_for_task(task_code: str) -> Optional[str]:
    """Map a task code to its default material assembly."""
    template = get_template(task_code)
    if template and template.applicable_assemblies:
        return template.applicable_assemblies[0]
    return None


# ── Main Orchestrator ─────────────────────────────────────────────────────────

class AgentV3:
    """v3 agent orchestrator with structured outputs, tool calling, and market pricing."""

    def __init__(self) -> None:
        self.tools = AgentTools()
        self.clarification_threshold = 0.80

    async def process_message(
        self,
        message: str,
        county: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        history: list[dict] | None = None,
        db: Optional[AsyncSession] = None,
        skip_llm_response: bool = False,
        user_id: Optional[int] = None,
        blueprint_context: Optional[dict] = None,
        previous_estimate: Optional[dict] = None,
        confirmed_intake: Optional[dict] = None,
    ) -> AgentV3Result:
        """Main v3 entry point for chat pricing requests.

        Pipeline:
          1. Structured LLM classification with reasoning
          2. (Optional) Clarification if confidence < threshold
          3. Parallel tool calls to gather pricing data
          4. Deterministic pricing (PricingEngine)
          5. Market pricing adjustments
          6. LLM narrative generation
        """
        t0 = asyncio.get_event_loop().time()

        # ── Step -1: Intake inference ─────────────────────────────────────────
        # Only run intake on first messages (no previous estimate / no revision)
        intake_result: Optional[IntakeAgentResult] = None
        if (
            settings.intake_agent_enabled
            and not previous_estimate
            and not _detect_revision_intent(message)
        ):
            if confirmed_intake:
                # User confirmed/edited intake from a previous turn
                intake_result = IntakeAgentResult(
                    intent=confirmed_intake.get("intent", ""),
                    fixture_counts=confirmed_intake.get("fixture_counts", {}),
                    location=confirmed_intake.get("location"),
                    urgency=confirmed_intake.get("urgency"),
                    preferred_tier=confirmed_intake.get("preferred_tier"),
                    confidence=1.0,
                )
                logger.info("agent_v3.intake_confirmed", intent=intake_result.intent)
            else:
                intake_result = await infer_intake(message, county=county)
                if intake_result and intake_result.confidence > 0:
                    logger.info(
                        "agent_v3.intake_inferred",
                        intent=intake_result.intent,
                        confidence=intake_result.confidence,
                        fixtures=intake_result.fixture_counts,
                    )

        # ── Step 0: Revision detection ────────────────────────────────────────
        revision_delta: Optional[RevisionDelta] = None
        if previous_estimate and _detect_revision_intent(message):
            logger.info("agent_v3.revision_detected", message=message[:80])
            revision_delta = await _parse_revision_delta(message, previous_estimate)
            if revision_delta:
                logger.info(
                    "agent_v3.revision_parsed",
                    new_task_code=revision_delta.new_task_code,
                    quantity_delta=revision_delta.quantity_delta,
                    notes=revision_delta.notes,
                )

        # ── Step 0.5: Retrieve long-term memories for context ─────────────────
        memory_context = ""
        memories: list[dict] = []
        if db is not None and user_id is not None:
            try:
                memories = await memory_service.retrieve(
                    db, user_id=user_id, query=message, top_k=3, kinds=["preference", "profile", "fact"]
                )
                if memories:
                    memory_lines = "\n".join(
                        f"- [{m['kind']}] {m['content']}" for m in memories
                    )
                    memory_context = f"Relevant memories from past conversations:\n{memory_lines}"
                    logger.info("agent_v3.memories_retrieved", count=len(memories))
            except Exception as exc:
                logger.warning("agent_v3.memory_retrieval_failed", error=str(exc))

        # ── Step 1: Structured classification ─────────────────────────────────
        # Fast path: run keyword classifier first (0 ms). If it's highly
        # confident, skip the LLM entirely — saves 5-12 s per clear request.
        from app.services.agent import classify_request
        keyword_result = classify_request(message)
        kw_confidence = keyword_result.get("confidence", 0.0)

        _KEYWORD_FAST_PATH_THRESHOLD = 0.88

        if kw_confidence >= _KEYWORD_FAST_PATH_THRESHOLD:
            classification = ClassifyResult(
                task_code=keyword_result.get("task_code"),
                access_type=keyword_result.get("access_type", "first_floor"),
                urgency=keyword_result.get("urgency", "standard"),
                county=keyword_result.get("county", county or "Dallas"),
                city=keyword_result.get("city"),
                quantity=keyword_result.get("quantity", 1),
                preferred_supplier=keyword_result.get("preferred_supplier") or preferred_supplier,
                confidence=kw_confidence,
                reasoning=f"Keyword fast-path (confidence={kw_confidence:.2f})",
            )
            classified_by = "keyword_fast_path"
        else:
            # Semantic task-code retrieval: surface the most relevant codes for this query
            dynamic_codes: frozenset[str] | None = None
            if db is not None:
                try:
                    similar = await task_code_embedding_service.search_similar(db, message, top_k=20)
                    dynamic_codes = frozenset(similar)
                    logger.info("agent_v3.task_codes_retrieved", count=len(dynamic_codes))
                except Exception as exc:
                    logger.warning("agent_v3.task_code_retrieval_failed", error=str(exc))

            # LLM classification for ambiguous requests (dynamic task codes when available)
            classification = await llm_structured.classify(
                message, history=history, task_codes=dynamic_codes, memory_context=memory_context or None
            )

            if classification is None:
                # LLM timed out or failed — use keyword result
                classification = ClassifyResult(
                    task_code=keyword_result.get("task_code"),
                    access_type=keyword_result.get("access_type", "first_floor"),
                    urgency=keyword_result.get("urgency", "standard"),
                    county=keyword_result.get("county", "Dallas"),
                    city=keyword_result.get("city"),
                    quantity=keyword_result.get("quantity", 1),
                    preferred_supplier=keyword_result.get("preferred_supplier"),
                    confidence=keyword_result.get("confidence", 0.75),
                    reasoning="Fallback to keyword classification (structured LLM unavailable)",
                )
                classified_by = "keyword"
            else:
                classified_by = "llm_structured"

        # Caller overrides
        if county:
            classification.county = county
        if preferred_supplier:
            classification.preferred_supplier = preferred_supplier

        # Apply intake facts to classification when present
        if intake_result:
            if intake_result.urgency:
                classification.urgency = intake_result.urgency
                classification.reasoning += f" | Intake urgency={intake_result.urgency}"
            if intake_result.location and not classification.city:
                classification.city = intake_result.location
                classification.reasoning += f" | Intake city={intake_result.location}"
            # Quantity from fixture counts only if classification task matches a fixture
            if intake_result.fixture_counts and classification.task_code:
                seeded = _seed_quantity_from_blueprint(
                    classification.task_code, intake_result.fixture_counts
                )
                if seeded:
                    qty, fixture_type = seeded
                    classification.quantity = qty
                    classification.reasoning += f" | Intake seeded {fixture_type} qty={qty}"

        # ── Step 0.6: Proactive context suggestions from memory ───────────────
        suggested_context: list[SuggestedContext] = []
        if db is not None and user_id is not None:
            try:
                suggested_context = await _generate_suggested_context(
                    db, user_id, classification, memories or []
                )
                if suggested_context:
                    logger.info("agent_v3.suggestions_generated", count=len(suggested_context))
            except Exception as exc:
                logger.warning("agent_v3.suggestion_generation_failed", error=str(exc))

        # Apply revision delta if parsed
        if revision_delta:
            if revision_delta.new_task_code:
                classification.task_code = revision_delta.new_task_code.upper()
                classification.reasoning += f" | Revision: changed task to {classification.task_code}"
            if revision_delta.quantity_delta:
                classification.quantity = max(1, min(20, classification.quantity + revision_delta.quantity_delta))
                classification.reasoning += f" | Revision: qty delta {revision_delta.quantity_delta}"
            if revision_delta.new_access_type:
                classification.access_type = revision_delta.new_access_type
                classification.reasoning += f" | Revision: access={revision_delta.new_access_type}"
            if revision_delta.new_urgency:
                classification.urgency = revision_delta.new_urgency
                classification.reasoning += f" | Revision: urgency={revision_delta.new_urgency}"
            classified_by = f"revision_from_{classified_by}"

        # Blueprint context enrichment
        blueprint_seeded = False
        if blueprint_context:
            fixtures = blueprint_context.get("fixtures") or {}
            seeded = _seed_quantity_from_blueprint(classification.task_code, fixtures)
            if seeded:
                qty, fixture_type = seeded
                classification.quantity = qty
                classification.reasoning += f" | Blueprint seeded {fixture_type} count={qty}"
                blueprint_seeded = True
                logger.info("agent_v3.blueprint_quantity_seeded", task_code=classification.task_code, fixture=fixture_type, quantity=qty)
            else:
                classification.reasoning += f" | Blueprint context: {blueprint_context}"

        logger.info(
            "agent_v3.classified",
            task_code=classification.task_code,
            confidence=classification.confidence,
            classified_by=classified_by,
            reasoning=classification.reasoning[:120],
        )

        # ── Step 2: Clarification check ───────────────────────────────────────
        if classification.confidence < self.clarification_threshold and not classification.task_code:
            clarification = await llm_structured.request_clarification(message, classification, history)
            if clarification and clarification.questions:
                return AgentV3Result(
                    classification=classification,
                    estimate=EstimateResult(
                        template_code=None,
                        assembly_code=None,
                        job_type="service",
                        access_type="first_floor",
                        urgency_type="standard",
                        county=classification.county,
                        tax_rate=0.0825,
                        line_items=[],
                        labor_total=0.0,
                        materials_total=0.0,
                        tax_total=0.0,
                        markup_total=0.0,
                        misc_total=0.0,
                        subtotal=0.0,
                        grand_total=0.0,
                        confidence_score=classification.confidence,
                        confidence_label="LOW",
                        assumptions=["Insufficient information to generate estimate"],
                        sources=["agent_v3_clarification"],
                        pricing_trace={},
                    ),
                    clarification_questions=clarification.questions,
                    classified_by=classified_by,
                )

        # ── Step 3: Parallel tool calls ───────────────────────────────────────
        tool_calls: list[ToolCallResult] = []

        if classification.task_code:
            tool_tasks = [
                self._execute_tool(
                    "search_materials",
                    {
                        "task_code": classification.task_code,
                        "preferred_supplier": classification.preferred_supplier,
                    },
                ),
                self._execute_tool(
                    "get_labor_template",
                    {
                        "task_code": classification.task_code,
                        "access": classification.access_type,
                        "urgency": classification.urgency,
                    },
                ),
                self._execute_tool(
                    "lookup_permit_cost",
                    {
                        "task_code": classification.task_code,
                        "county": classification.county,
                    },
                ),
            ]
            tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)
            for tr in tool_results:
                if isinstance(tr, ToolCallResult):
                    tool_calls.append(tr)
                elif isinstance(tr, Exception):
                    tool_calls.append(ToolCallResult(
                        tool_name="unknown",
                        arguments={},
                        result=None,
                        error=str(tr),
                    ))

        # ── Step 4: Deterministic pricing ─────────────────────────────────────
        if classification.task_code:
            # Build materials from tool result
            materials: list[MaterialItem] = []
            materials_tool = next((t for t in tool_calls if t.tool_name == "search_materials"), None)
            if materials_tool and not materials_tool.error:
                for m in materials_tool.result.get("materials", []):
                    materials.append(MaterialItem(
                        canonical_item=m["canonical_item"],
                        description=m["description"],
                        quantity=m["quantity"],
                        unit="ea",
                        unit_cost=m["unit_cost"],
                        supplier=m.get("supplier") or "",
                    ))

            estimate = pricing_engine.calculate_service_estimate(
                task_code=classification.task_code,
                materials=materials,
                access=classification.access_type,
                urgency=classification.urgency,
                county=classification.county,
                city=classification.city,
                preferred_supplier=classification.preferred_supplier,
            )
        else:
            # Unclassifiable
            estimate = EstimateResult(
                template_code=None,
                assembly_code=None,
                job_type="service",
                access_type="first_floor",
                urgency_type="standard",
                county=classification.county,
                tax_rate=0.0825,
                line_items=[],
                labor_total=0.0,
                materials_total=0.0,
                tax_total=0.0,
                markup_total=0.0,
                misc_total=0.0,
                subtotal=0.0,
                grand_total=0.0,
                confidence_score=classification.confidence,
                confidence_label="LOW",
                assumptions=["Could not identify the plumbing task from the description"],
                sources=["agent_v3_unclassifiable"],
                pricing_trace={},
            )

        # ── Step 5: Market pricing adjustments ────────────────────────────────
        market_adjustments_applied: list[dict] = []
        overall_market_factor = 1.0

        if db and classification.task_code:
            try:
                adjustments = await market_pricing_engine.get_active_adjustments(
                    db, classification.county, categories=["materials", "labor"]
                )
                if adjustments:
                    estimate_dict = {
                        "labor_total": estimate.labor_total,
                        "materials_total": estimate.materials_total,
                        "markup_total": estimate.markup_total,
                        "tax_total": estimate.tax_total,
                        "misc_total": estimate.misc_total,
                        "subtotal": estimate.subtotal,
                        "grand_total": estimate.grand_total,
                        "trip_charge": estimate.trip_total,
                        "tax_rate": estimate.tax_rate,
                        "county": classification.county,
                        "confidence_components": {},
                    }
                    adjusted_dict, applied = market_pricing_engine.apply_adjustments(
                        estimate_dict, adjustments
                    )

                    # Rebuild EstimateResult with adjusted values
                    estimate = replace(
                        estimate,
                        labor_total=adjusted_dict["labor_total"],
                        materials_total=adjusted_dict["materials_total"],
                        markup_total=adjusted_dict["markup_total"],
                        tax_total=adjusted_dict["tax_total"],
                        misc_total=adjusted_dict["misc_total"],
                        subtotal=adjusted_dict["subtotal"],
                        grand_total=adjusted_dict["grand_total"],
                        confidence_components=adjusted_dict.get("confidence_components", {}),
                    )

                    overall_market_factor = adjusted_dict["market_adjustment_applied"]
                    market_adjustments_applied = [
                        {"name": a.name, "category": a.category, "factor": a.factor}
                        for a in applied
                    ]
            except Exception as exc:
                logger.warning("agent_v3.market_pricing_failed", error=str(exc))

        # ── Step 5.5: Proactive revision suggestions ──────────────────────────
        revision_suggestions: list[RevisionSuggestion] = []
        if (
            settings.revision_suggestions_enabled
            and classification.task_code
            and not previous_estimate
        ):
            try:
                revision_suggestions = suggest_revisions(estimate)
                if revision_suggestions:
                    logger.info(
                        "agent_v3.revision_suggestions",
                        count=len(revision_suggestions),
                    )
            except Exception as exc:
                logger.warning("agent_v3.revision_suggestions_failed", error=str(exc))

        # ── Step 6: LLM narrative ─────────────────────────────────────────────
        narrative = None
        if not skip_llm_response and classification.task_code:
            try:
                narrative = await asyncio.wait_for(
                    llm_service.generate_response(
                        message=message,
                        grand_total=estimate.grand_total,
                        labor_total=estimate.labor_total,
                        materials_total=estimate.materials_total,
                        tax_total=estimate.tax_total,
                        template_name=estimate.template_code or classification.task_code,
                        county=classification.county,
                        quantity=classification.quantity,
                        history=history,
                    ),
                    timeout=float(settings.llm_timeout),
                )
            except asyncio.TimeoutError:
                logger.warning("agent_v3.narrative_timeout", timeout=settings.llm_timeout)
                narrative = None

        total_latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

        agent_trace = {
            "classified_by": classified_by,
            "classification_reasoning": classification.reasoning,
            "tool_calls": [
                {
                    "tool": tc.tool_name,
                    "latency_ms": tc.latency_ms,
                    "error": tc.error,
                }
                for tc in tool_calls
            ],
            "market_adjustment_applied": overall_market_factor,
            "total_latency_ms": total_latency_ms,
        }

        # Compute estimate diff for revision requests
        estimate_diff = None
        if previous_estimate and revision_delta and classification.task_code:
            from app.services.pricing_engine import LineItem
            old_lines = [
                LineItem(
                    line_type=li.get("line_type", "material"),
                    description=li.get("description", ""),
                    quantity=li.get("quantity", 1),
                    unit=li.get("unit", "ea"),
                    unit_cost=li.get("unit_cost", 0),
                    total_cost=li.get("total_cost", 0),
                    canonical_item=li.get("canonical_item"),
                )
                for li in previous_estimate.get("line_items", [])
            ]
            old_estimate = EstimateResult(
                template_code=previous_estimate.get("template_code"),
                assembly_code=None,
                job_type="service",
                access_type=classification.access_type,
                urgency_type=classification.urgency,
                county=classification.county,
                tax_rate=0.0825,
                line_items=old_lines,
                labor_total=previous_estimate.get("labor_total", 0),
                materials_total=previous_estimate.get("materials_total", 0),
                tax_total=0,
                markup_total=0,
                misc_total=0,
                subtotal=0,
                grand_total=previous_estimate.get("grand_total", 0),
                confidence_score=0,
                confidence_label="LOW",
                assumptions=[],
                sources=[],
                pricing_trace={},
            )
            estimate_diff = _compute_estimate_diff(old_estimate, estimate)
            # Override narrative for revisions
            if narrative and estimate_diff:
                narrative = f"Updated estimate: ${estimate_diff['new_total']:,.2f} ({estimate_diff['total_delta']:+.2f}). {narrative}"

        return AgentV3Result(
            classification=classification,
            estimate=estimate,
            tool_calls=tool_calls,
            market_adjustments_applied=market_adjustments_applied,
            overall_market_factor=overall_market_factor,
            narrative=narrative,
            suggested_context=suggested_context,
            classified_by=classified_by,
            agent_trace=agent_trace,
            estimate_diff=estimate_diff,
            blueprint_seeded=blueprint_seeded,
            intake_result=intake_result,
            revision_suggestions=revision_suggestions,
        )

    async def generate_variants(
        self,
        message: str,
        county: Optional[str] = None,
        preferred_supplier: Optional[str] = None,
        history: list[dict] | None = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        blueprint_context: Optional[dict] = None,
        previous_estimate: Optional[dict] = None,
        tiers: list[str] | None = None,
        confirmed_intake: Optional[IntakeAgentResult] = None,
    ) -> list[AgentV3Result]:
        """Generate multiple estimate variants (budget/standard/premium) for comparison.

        1. Classify once (same as process_message)
        2. Build standard estimate
        3. Derive budget + premium variants by adjusting assemblies, labor, markup, and warranty
        """
        tiers = tiers or ["budget", "standard", "premium"]

        # Build the standard estimate using the normal pipeline
        standard_result = await self.process_message(
            message=message,
            county=county,
            preferred_supplier=preferred_supplier,
            history=history,
            db=db,
            user_id=user_id,
            skip_llm_response=True,
            blueprint_context=blueprint_context,
            previous_estimate=previous_estimate,
            confirmed_intake=confirmed_intake,
        )

        if standard_result.clarification_questions or not standard_result.estimate.template_code:
            # Can't variant-ify a clarification or unclassifiable request
            return [standard_result]

        variants: list[AgentV3Result] = []
        for tier in tiers:
            if tier == "standard":
                variants.append(standard_result)
                continue

            # Route through the full pricing engine for correct variant totals
            tier_estimate = _build_variant_estimate(
                standard_result.estimate, tier, standard_result.classification
            )

            variant_result = AgentV3Result(
                classification=standard_result.classification,
                estimate=tier_estimate,
                tool_calls=standard_result.tool_calls,
                market_adjustments_applied=standard_result.market_adjustments_applied,
                overall_market_factor=standard_result.overall_market_factor,
                narrative=None,
                suggested_context=standard_result.suggested_context,
                classified_by=f"{standard_result.classified_by}_variant_{tier}",
                agent_trace={**standard_result.agent_trace, "variant_tier": tier},
                estimate_diff=standard_result.estimate_diff,
                blueprint_seeded=standard_result.blueprint_seeded,
            )
            variants.append(variant_result)

        return variants

    async def _execute_tool(self, tool_name: str, arguments: dict) -> ToolCallResult:
        """Execute a single tool and measure latency."""
        t0 = time.monotonic()
        try:
            tool_method = getattr(self.tools, tool_name)
            result = await tool_method(**arguments)
            latency_ms = int((time.monotonic() - t0) * 1000)
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                latency_ms=latency_ms,
                error=str(exc),
            )


# ── Singleton ─────────────────────────────────────────────────────────────────

agent_v3 = AgentV3()
