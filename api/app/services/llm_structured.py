"""
LLM Structured Output Service — v3

Reliable Pydantic-structured generation with retry logic.
Replaces the fragile `json_object` + `json.loads()` pattern used in v1.

Strategy
--------
1. Use OpenAI's native `parse()` with Pydantic response models when available.
2. Fall back to `instructor` library for broader provider support.
3. 3 retries with exponential backoff on validation failures.
4. On total failure, return None so the pipeline falls back to keyword classification.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional, Literal, cast
import structlog

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.labor_engine import list_template_codes
from app.services.pricing_engine import County

logger = structlog.get_logger()

_VALID_TASK_CODES = frozenset(code.upper() for code in list_template_codes())
_COUNTIES = {c.value for c in County}

# Curated subset of common residential/commercial task codes used in the classify
# prompt. Using all 314+ codes makes the prompt ~2000 tokens which is too slow
# for local inference. These 69 cover >95% of real requests; the full
# _VALID_TASK_CODES set is still used for post-LLM validation.
_PROMPT_TASK_CODES: frozenset[str] = frozenset({
    "ANGLE_STOP_REPLACE", "ANGLE_STOP_REPLACE_PAIR", "BACKFLOW_PREVENTER_INSTALL",
    "BACKFLOW_TEST_ANNUAL", "BATHTUB_DRAIN_REPAIR", "CAMERA_INSPECTION",
    "CLEAN_OUT_INSTALL", "DISHWASHER_HOOKUP", "DRAIN_CLEAN_BATHTUB",
    "DRAIN_CLEAN_KITCHEN", "DRAIN_CLEAN_SHOWER", "DRAIN_CLEAN_STANDARD",
    "EXPANSION_TANK_INSTALL", "EXPANSION_TANK_ONLY", "FAUCET_CARTRIDGE_REPAIR",
    "GARBAGE_DISPOSAL_INSTALL", "GARBAGE_DISPOSAL_REPAIR", "GAS_LINE_NEW_RUN",
    "GAS_LINE_REPAIR_MINOR", "GAS_PRESSURE_TEST", "GAS_SHUTOFF_REPLACE",
    "HOSE_BIB_ADD_NEW", "HOSE_BIB_REPLACE", "HYDROJETTING",
    "ICE_MAKER_LINE_INSTALL", "IRRIGATION_BACKFLOW_REPAIR", "KITCHEN_FAUCET_REPLACE",
    "LAV_FAUCET_REPLACE", "LAV_SINK_REPLACE", "LEAK_DETECTION",
    "MAIN_LINE_CLEAN", "MAIN_SHUTOFF_REPLACE", "MIXING_VALVE_REPLACE",
    "OUTDOOR_SHOWER_INSTALL", "PRV_INSTALL_NEW", "PRV_REPLACE",
    "PTRAP_REPLACE", "RECIRCULATION_PUMP_INSTALL", "SEWER_SPOT_REPAIR",
    "SHOWER_HEAD_REPLACE", "SHOWER_PAN_LINER_REPAIR", "SHOWER_VALVE_REPLACE",
    "SLAB_LEAK_REPAIR", "SUPPLY_LINE_REPLACE", "TOILET_COMFORT_HEIGHT",
    "TOILET_FILL_VALVE_REPLACE", "TOILET_FLANGE_REPAIR", "TOILET_FLAPPER_REPLACE",
    "TOILET_INSTALL_NEW", "TOILET_REPLACE_STANDARD", "TUB_SPOUT_REPLACE",
    "TUB_SHOWER_COMBO_REPLACE", "UNDER_SINK_FILTER_INSTALL", "URINAL_REPLACE",
    "WATER_HEATER_FLUSH", "WATER_SOFTENER_INSTALL",
    "WH_40G_GAS_STANDARD", "WH_50G_GAS_STANDARD", "WH_50G_GAS_ATTIC",
    "WH_40G_ELEC_STANDARD", "WH_50G_ELEC_STANDARD",
    "WH_ANODE_REPLACE", "WH_ELEMENT_REPLACE", "WH_FLUSH_MAINTENANCE",
    "WH_REPAIR_GAS", "WH_TANKLESS_GAS", "WH_TANKLESS_ELEC",
    "WHOLE_HOUSE_FILTER_INSTALL", "WHOLE_HOUSE_REPIPING",
})
# Keep only codes that actually exist in the labor template catalog
_PROMPT_TASK_CODES = _PROMPT_TASK_CODES & _VALID_TASK_CODES


# ── Pydantic Response Models ──────────────────────────────────────────────────

class ClassifyResult(BaseModel):
    task_code: Optional[str] = Field(
        None,
        description="Best-matching labor template code, or null if unknown"
    )
    access_type: Literal[
        "first_floor", "second_floor", "attic", "crawlspace", "slab", "basement"
    ] = "first_floor"
    urgency: Literal["standard", "same_day", "emergency"] = "standard"
    county: str = "Dallas"
    city: Optional[str] = None
    quantity: int = Field(default=1, ge=1, le=20)
    preferred_supplier: Optional[Literal["ferguson", "moore_supply", "apex"]] = None
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    reasoning: str = Field(
        default="",
        description="Chain-of-thought explaining the classification decision"
    )


class ClarificationRequest(BaseModel):
    questions: list[str] = Field(
        default_factory=list,
        description="Follow-up questions to ask the user when intent is unclear"
    )


class IntakeInference(BaseModel):
    """Structured intake inference for v6.6.0 intake agent."""
    intent: str = Field(default="general_plumbing", description="Short intent slug, e.g. toilet_replace")
    fixture_counts: dict[str, int] = Field(default_factory=dict, description="Map of fixture key to count")
    location: Optional[str] = Field(default=None, description="DFW city or county if mentioned")
    urgency: Literal["standard", "same_day", "emergency"] = "standard"
    preferred_tier: Literal["budget", "standard", "premium"] = "standard"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# ── Prompts ───────────────────────────────────────────────────────────────────

def _build_classify_system_prompt(task_codes: frozenset[str] | None = None) -> str:
    # Use curated common codes (~69) not all 314 — keeps prompt ~400 tokens for fast local inference.
    # When task_codes is provided (from semantic search), merge with the common set.
    codes = task_codes if task_codes is not None else _PROMPT_TASK_CODES
    codes = codes & _VALID_TASK_CODES
    task_codes_str = ", ".join(sorted(codes))
    return f"""\
/no_think
You are a plumbing estimator AI for DFW (Dallas-Fort Worth) Texas contractors.
Classify the plumbing request into structured JSON. Pick the best task_code or null.

Relevant task codes: {task_codes_str}

Rules:
- "clogged/backed up/slow drain" → DRAIN_CLEAN_STANDARD (not a replacement)
- "toilet won't flush/clogged" → DRAIN_CLEAN_STANDARD, not TOILET_REPLACE_STANDARD
- "angle stop/shutoff valve" → ANGLE_STOP_REPLACE or ANGLE_STOP_REPLACE_PAIR
- "sewer line broken/collapsed" → SEWER_SPOT_REPAIR, not MAIN_LINE_CLEAN
- Quantity: extract from "two/three/both/pair" (both/pair=2). Default 1.
- county: DFW county name (Dallas, Tarrant, Collin, Denton, etc.)

Respond with valid JSON only. Include a brief reasoning field."""


# ── Service ───────────────────────────────────────────────────────────────────

class LLMStructuredService:
    """Reliable structured LLM output with Pydantic validation and retry."""

    def __init__(self) -> None:
        # Use fewer retries for local LLMs to fail fast and fall back to keyword classification.
        self._max_retries = 1
        self._base_delay = 1.0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_client(self, timeout: float):
        """Create an AsyncOpenAI client."""
        try:
            from openai import AsyncOpenAI

            provider = (settings.default_llm_provider or "openai").lower()
            if provider == "openai" and settings.openai_api_key:
                return AsyncOpenAI(
                    base_url="https://api.openai.com/v1",
                    api_key=settings.openai_api_key,
                    timeout=timeout,
                )
            if provider == "anthropic" and settings.anthropic_api_key:
                return AsyncOpenAI(
                    base_url=getattr(settings, "anthropic_base_url", None) or "https://api.anthropic.com/v1",
                    api_key=settings.anthropic_api_key,
                    timeout=timeout,
                )
            if provider == "deepseek" and settings.deepseek_api_key:
                return AsyncOpenAI(
                    base_url="https://api.deepseek.com/v1",
                    api_key=settings.deepseek_api_key,
                    timeout=timeout,
                )
            # Fallback to local Ollama
            return AsyncOpenAI(
                base_url=settings.hermes_endpoint_url,
                api_key=settings.hermes_api_key,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("llm_structured.client_creation_failed", error=str(exc))
            return None

    def _active_model(self) -> str:
        """Return the model to use for structured output."""
        provider = (settings.default_llm_provider or "openai").lower()
        if provider in ("openai", "anthropic", "deepseek"):
            return settings.default_llm_model
        return settings.llm_primary_model

    def _is_cloud_provider(self) -> bool:
        """Return True when using OpenAI or Anthropic cloud APIs."""
        provider = (settings.default_llm_provider or "openai").lower()
        if provider == "openai" and settings.openai_api_key:
            return True
        if provider == "anthropic" and settings.anthropic_api_key:
            return True
        if provider == "deepseek" and settings.deepseek_api_key:
            return True
        return False

    async def _call_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        timeout: float = 20.0,
    ) -> Optional[BaseModel]:
        """Call LLM with structured output, returning a validated Pydantic model."""
        client = self._make_client(timeout=timeout)
        if client is None:
            return None

        model = self._active_model()

        # beta.parse() is OpenAI-native structured outputs — Ollama hangs on it,
        # so only attempt it for real cloud providers.
        if self._is_cloud_provider():
            try:
                response = await client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_model,
                    temperature=0.0,
                    max_tokens=640,
                )
                parsed = response.choices[0].message.parsed
                if parsed is not None:
                    return parsed
            except Exception as parse_exc:
                logger.debug("llm_structured.parse_failed", error=str(parse_exc), model=model)

        # JSON mode + manual validation (works with Ollama and cloud fallback)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=640,
            )
            raw = (response.choices[0].message.content or "{}").strip()
            # Strip <think>...</think> reasoning blocks (qwen3 and similar models)
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Extract first JSON object if the model still prepends text
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                raw = json_match.group(0)
            data = json.loads(raw)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("llm_structured.validation_failed", error=str(exc), raw=raw[:200])
            return None
        except Exception as exc:
            logger.warning("llm_structured.call_failed", error=str(exc))
            return None

    async def _call_with_retry(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        timeout: float = 20.0,
    ) -> Optional[BaseModel]:
        """Retry structured call with exponential backoff and hard wall-clock timeout."""
        for attempt in range(1, self._max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._call_structured(messages, response_model, timeout),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("llm_structured.timeout", attempt=attempt, timeout=timeout)
                result = None
            if result is not None:
                return result

            if attempt < self._max_retries:
                delay = self._base_delay * (2 ** (attempt - 1))
                logger.info("llm_structured.retry", attempt=attempt, delay=delay)
                await asyncio.sleep(delay)

        logger.warning("llm_structured.all_retries_exhausted", retries=self._max_retries)
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def make_structured_client(self, timeout: float = 30.0):
        """Return an AsyncOpenAI client for structured LLM calls."""
        return self._make_client(timeout=timeout)

    async def classify(
        self,
        message: str,
        history: list[dict] | None = None,
        task_codes: frozenset[str] | None = None,
        memory_context: str | None = None,
    ) -> Optional[ClassifyResult]:
        """Extract structured intent from a natural-language plumbing request.

        Returns a validated ClassifyResult on success, or None on total failure
        (caller should fall back to keyword classification).
        """
        messages: list[dict] = [{"role": "system", "content": _build_classify_system_prompt(task_codes)}]
        if history:
            for turn in history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        user_content = message
        if memory_context:
            user_content = f"[Memory context]\n{memory_context}\n\n[User request]\n{message}"
        messages.append({"role": "user", "content": user_content})

        result = await self._call_with_retry(messages, ClassifyResult, timeout=settings.llm_classify_timeout)
        if result is None:
            return None

        # Sanitize fields against our allowlists
        county = str(result.county or "Dallas").strip().title()
        if county not in _COUNTIES:
            county = "Dallas"
        result.county = county

        task_code = (result.task_code or "").strip().upper()
        if task_code and task_code not in _VALID_TASK_CODES:
            task_code = None
        result.task_code = task_code

        quantity = max(1, min(20, result.quantity))
        result.quantity = quantity

        confidence = max(0.0, min(1.0, result.confidence))
        result.confidence = confidence

        logger.info(
            "llm_structured.classify",
            task_code=result.task_code,
            county=result.county,
            confidence=result.confidence,
            reasoning=result.reasoning[:100],
        )
        return result

    async def infer_intake(
        self,
        message: str,
        county: Optional[str] = None,
    ) -> Optional[IntakeInference]:
        """Infer job facts from a user's first message.

        Lightweight structured call used as a fallback when regex heuristics are
        uncertain. Returns None on failure so the caller can keep the heuristic.
        """
        system_prompt = """\
You are a plumbing intake assistant for DFW Texas contractors.
Read the user's message and extract structured job facts.

Rules:
- intent: short slug like "toilet_replace", "water_heater_upgrade", "whole_house_repipe".
- fixture_counts: map fixture keys (toilet, sink, faucet, shower, bathtub, water_heater, garbage_disposal, dishwasher, hose_bib, angle_stop, prv, backflow, whole_house_filter) to integer counts.
- location: DFW city or county if mentioned, otherwise null.
- urgency: "emergency" for flooding/burst/no water, "same_day" for today/now, else "standard".
- preferred_tier: "budget" for cheap/basic, "premium" for high-end/luxury, else "standard".
- confidence: 0.0–1.0 based on how explicit the user was.

Respond with valid JSON only."""
        user_prompt = message
        if county:
            user_prompt = f"County hint: {county}\n\n{message}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self._call_with_retry(messages, IntakeInference, timeout=10.0)
        if raw is None:
            return None

        result = cast(IntakeInference, raw)

        # Sanitize against allowlists
        urgency = result.urgency if result.urgency in ("standard", "same_day", "emergency") else "standard"
        tier = result.preferred_tier if result.preferred_tier in ("budget", "standard", "premium") else "standard"
        location = result.location
        if location:
            location = location.strip().title()
            if location.lower() not in _COUNTIES and location.lower() not in {
                "dallas", "plano", "frisco", "mckinney", "allen", "richardson",
                "garland", "irving", "arlington", "fort worth", "denton",
                "lewisville", "carrollton", "mesquite", "rockwall",
            }:
                location = None

        result.urgency = urgency
        result.preferred_tier = tier
        result.location = location
        result.confidence = max(0.0, min(1.0, result.confidence))
        return result

    async def request_clarification(
        self,
        message: str,
        last_classification: ClassifyResult,
        history: list[dict] | None = None,
    ) -> Optional[ClarificationRequest]:
        """Generate follow-up questions when classification confidence is low."""
        system_prompt = """\
You are a helpful plumbing estimator assistant. The user's request was unclear.
Generate 1-3 concise follow-up questions to clarify the job details.
Respond with JSON: {"questions": ["...", "..."]}
"""
        user_prompt = (
            f'Original message: "{message}"\n'
            f'Partial classification: task={last_classification.task_code or "unknown"}, '
            f'confidence={last_classification.confidence:.2f}\n'
            f'Reasoning: {last_classification.reasoning}\n\n'
            "What clarifying questions should we ask?"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return await self._call_with_retry(messages, ClarificationRequest, timeout=15.0)


# ── Singleton ─────────────────────────────────────────────────────────────────

llm_structured = LLMStructuredService()
