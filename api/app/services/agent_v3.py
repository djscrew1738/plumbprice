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
from app.services.pricing_engine import pricing_engine, EstimateResult, MaterialItem
from app.services.supplier_service import supplier_service, MATERIAL_ASSEMBLIES
from app.services.labor_engine import get_template
from app.services.llm_service import llm_service
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
class AgentV3Result:
    """Complete result from the v3 agent pipeline."""
    classification: ClassifyResult
    estimate: EstimateResult
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    market_adjustments_applied: list[dict] = field(default_factory=list)
    overall_market_factor: float = 1.0
    narrative: Optional[str] = None
    clarification_questions: Optional[list[str]] = None
    classified_by: str = "keyword"
    agent_trace: dict = field(default_factory=dict)


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

        # ── Step 1: Structured classification ─────────────────────────────────
        classification = await llm_structured.classify(message, history=history)

        if classification is None:
            # Total failure — fall back to keyword classifier from v1
            from app.services.agent import classify_request
            keyword_result = classify_request(message)
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

        # Blueprint context enrichment
        if blueprint_context:
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

        return AgentV3Result(
            classification=classification,
            estimate=estimate,
            tool_calls=tool_calls,
            market_adjustments_applied=market_adjustments_applied,
            overall_market_factor=overall_market_factor,
            narrative=narrative,
            classified_by=classified_by,
            agent_trace=agent_trace,
        )

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
