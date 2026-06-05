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
from typing import Optional, Literal
import structlog

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.labor_engine import list_template_codes
from app.services.pricing_engine import County

logger = structlog.get_logger()

_VALID_TASK_CODES = frozenset(code.upper() for code in list_template_codes())
_COUNTIES = {c.value for c in County}


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


# ── Prompts ───────────────────────────────────────────────────────────────────

def _build_classify_system_prompt() -> str:
    task_codes = ",\n  ".join(sorted(_VALID_TASK_CODES))
    counties = " | ".join(f'"{c}"' for c in sorted(_COUNTIES))
    return f"""\
/no_think
You are a plumbing estimator AI for DFW (Dallas-Fort Worth) Texas contractors.
Classify the user's natural-language plumbing, construction, or commercial request into structured data.

Valid task_code values (pick the single best match from the real labor template catalog, or null if unknown):
  {task_codes}

Disambiguation rules (apply BEFORE picking task_code):
- "sink backed up / clogged / slow / draining slow / won't drain" → DRAIN_CLEAN_STANDARD (or DRAIN_CLEAN_KITCHEN / MAIN_LINE_CLEAN), NOT a fixture replacement.
- "toilet won't flush / clogged / backed up" → DRAIN_CLEAN_STANDARD, NOT TOILET_REPLACE.
- "angle stop(s) / shutoff valve / supply valve leaking / replace" → ANGLE_STOP_REPLACE (or ANGLE_STOP_REPLACE_PAIR if two/both/pair). The fact that they sit under a sink does NOT mean the sink itself is being replaced.
- "sewer line broken / cracked / collapsed / needs excavation" → SEWER_SPOT_REPAIR, NOT MAIN_LINE_CLEAN.
- Quantity: extract integer from words like "two", "three", "both", "pair" (both/pair = 2). Default 1.

Respond with valid JSON matching the expected schema. Include a brief reasoning field explaining your classification.
"""


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
        if provider in ("openai", "anthropic"):
            return settings.default_llm_model
        return settings.llm_primary_model

    def _is_cloud_provider(self) -> bool:
        """Return True when using OpenAI or Anthropic cloud APIs."""
        provider = (settings.default_llm_provider or "openai").lower()
        if provider == "openai" and settings.openai_api_key:
            return True
        if provider == "anthropic" and settings.anthropic_api_key:
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

    async def classify(
        self,
        message: str,
        history: list[dict] | None = None,
    ) -> Optional[ClassifyResult]:
        """Extract structured intent from a natural-language plumbing request.

        Returns a validated ClassifyResult on success, or None on total failure
        (caller should fall back to keyword classification).
        """
        messages: list[dict] = [{"role": "system", "content": _build_classify_system_prompt()}]
        if history:
            for turn in history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

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
