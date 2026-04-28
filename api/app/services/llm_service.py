"""
LLM Service — dual-model Ollama backend (OpenAI-compatible API).

Model strategy
--------------
  Primary   : qwen3:8b      (better reasoning, richer JSON)
  Secondary : hermes3:3b    (fast fallback, ~3 s)

The service tracks which model is active.  When the primary model fails
(connection error or timeout) it circuit-breaks down to the secondary.
After _CIRCUIT_RESET_SECONDS of silence it retries the primary.
Both models fall through to the keyword-only classifier and template
formatter if neither is available.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import json
import time
from typing import Optional
import structlog

from app.config import settings
from app.services.labor_engine import list_template_codes
from app.services.pricing_engine import County

_CIRCUIT_RESET_SECONDS = 120   # retry primary after this many seconds

logger = structlog.get_logger()

# ── Prompts ───────────────────────────────────────────────────────────────────

_VALID_TASK_CODES = frozenset(code.upper() for code in list_template_codes())


@lru_cache(maxsize=1)
def _build_classify_system_prompt() -> str:
    task_codes = ",\n  ".join(sorted(_VALID_TASK_CODES))
    counties = " | ".join(f'"{county.value}"' for county in County)
    return f"""\
You are a plumbing estimator AI for DFW (Dallas-Fort Worth) Texas contractors.
Classify the user's natural-language plumbing, construction, or commercial request into structured JSON.

Valid task_code values (pick the single best match from the real labor template catalog, or null if unknown):
  {task_codes}

Disambiguation rules (apply BEFORE picking task_code):
- "sink backed up / clogged / slow / draining slow / won't drain" → DRAIN_CLEAN_STANDARD (or DRAIN_CLEAN_KITCHEN / MAIN_LINE_CLEAN), NOT a fixture replacement (KITCHEN_FAUCET_REPLACE, LAV_SINK_REPLACE).
- "toilet won't flush / clogged / backed up" → DRAIN_CLEAN_STANDARD, NOT TOILET_REPLACE.
- "angle stop(s) / shutoff valve / supply valve leaking / replace" → ANGLE_STOP_REPLACE (or ANGLE_STOP_REPLACE_PAIR if two/both/pair). The fact that they sit under a sink does NOT mean the sink itself is being replaced.
- "sewer line broken / cracked / collapsed / needs excavation" → SEWER_SPOT_REPAIR, NOT MAIN_LINE_CLEAN.
- Quantity: extract integer from words like "two", "three", "both", "pair" (both/pair = 2). Default 1.

Return ONLY valid JSON with these exact keys:
{{
  "task_code": string | null,
  "access_type": "first_floor" | "second_floor" | "attic" | "crawlspace" | "slab" | "basement",
  "urgency": "standard" | "same_day" | "emergency",
  "county": {counties},
  "city": string | null,
  "quantity": integer (1–20),
  "preferred_supplier": "ferguson" | "moore_supply" | "apex" | null,
  "confidence": float (0.0–1.0)
}}
"""

_RESPONSE_SYSTEM = """\
You are a professional plumbing estimator for a DFW contractor.
Write a concise, natural, direct response to a customer's pricing question.
Use the exact numbers provided. No hedging, no disclaimers about estimates varying.
2-3 sentences. Sound like an experienced plumber, not a chatbot.
"""


# ── Service ───────────────────────────────────────────────────────────────────

class LLMService:
    """
    Dual-model Ollama LLM service with primary/secondary fallback.

    Active model starts as the primary.  Connection/timeout errors trip the
    circuit breaker and promote the secondary.  After _CIRCUIT_RESET_SECONDS
    the primary is tried again automatically.
    """

    def __init__(self) -> None:
        self._client = None
        # None = untested | True = known good | False = circuit-broken
        self._available: Optional[bool] = None
        self._last_failure_at: Optional[float] = None
        # Which model tier is currently active: "primary" | "secondary" | "cloud"
        self._active_tier: str = "primary"
        # Cloud cost tracking (per UTC day)
        self._cloud_cost_day: Optional[str] = None
        self._cloud_cost_usd: float = 0.0
        self._cloud_calls_today: int = 0

    # ── Cost tracking ─────────────────────────────────────────────────────────

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_cost_if_new_day(self) -> None:
        today = self._today_key()
        if self._cloud_cost_day != today:
            self._cloud_cost_day = today
            self._cloud_cost_usd = 0.0
            self._cloud_calls_today = 0

    def _cloud_budget_remaining(self) -> float:
        self._reset_cost_if_new_day()
        return max(0.0, settings.llm_cloud_daily_cap_usd - self._cloud_cost_usd)

    def _record_cloud_usage(self, total_tokens: int) -> None:
        self._reset_cost_if_new_day()
        cost = (total_tokens / 1000.0) * settings.llm_cloud_cost_per_1k_tokens_usd
        self._cloud_cost_usd += cost
        self._cloud_calls_today += 1
        logger.info(
            "llm.cloud_usage",
            tokens=total_tokens,
            cost_usd=round(cost, 4),
            day_total_usd=round(self._cloud_cost_usd, 4),
            day_remaining_usd=round(self._cloud_budget_remaining(), 4),
        )

    def get_status(self) -> dict:
        """Public snapshot of LLM availability + cost state for /health."""
        self._reset_cost_if_new_day()
        return {
            "active_tier": self._active_tier,
            "active_model": self._active_model,
            "available": self._available is not False,
            "cloud_fallback_enabled": settings.llm_cloud_fallback_enabled,
            "cloud_calls_today": self._cloud_calls_today,
            "cloud_cost_today_usd": round(self._cloud_cost_usd, 4),
            "cloud_cap_usd": settings.llm_cloud_daily_cap_usd,
            "cloud_budget_remaining_usd": round(self._cloud_budget_remaining(), 4),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_client(self, timeout: float):
        """Create a fresh AsyncOpenAI-compatible client for the active provider.

        When `_active_tier == 'cloud'`, force the configured cloud fallback
        provider (overriding `default_llm_provider`).  Otherwise, follow the
        normal provider preference for local/cloud routing.

        Provider selection (settings.default_llm_provider):
          - "openai":   api.openai.com using OPENAI_API_KEY
          - "anthropic": Anthropic API via the openai-compatible shim if
                        ANTHROPIC_API_KEY is set; falls back to local Hermes.
          - "hermes" / "ollama" / anything else: local Ollama at
                        HERMES_ENDPOINT_URL using HERMES_API_KEY.

        Returns None when the chosen provider has no usable credentials or
        when the openai SDK is unavailable.
        """
        try:
            from openai import AsyncOpenAI

            if self._active_tier == "cloud":
                cloud_provider = (settings.llm_cloud_fallback_provider or "openai").lower()
                if cloud_provider == "anthropic" and settings.anthropic_api_key:
                    return AsyncOpenAI(
                        base_url=getattr(settings, "anthropic_base_url", None) or "https://api.anthropic.com/v1",
                        api_key=settings.anthropic_api_key,
                        timeout=timeout,
                    )
                if cloud_provider == "openai" and settings.openai_api_key:
                    return AsyncOpenAI(
                        base_url="https://api.openai.com/v1",
                        api_key=settings.openai_api_key,
                        timeout=timeout,
                    )
                return None  # cloud tier requested but no key — caller handles

            provider = (settings.default_llm_provider or "hermes").lower()

            if provider == "openai" and settings.openai_api_key:
                return AsyncOpenAI(
                    base_url="https://api.openai.com/v1",
                    api_key=settings.openai_api_key,
                    timeout=timeout,
                )

            if provider == "anthropic" and settings.anthropic_api_key:
                base_url = (
                    getattr(settings, "anthropic_base_url", None)
                    or "https://api.anthropic.com/v1"
                )
                return AsyncOpenAI(
                    base_url=base_url,
                    api_key=settings.anthropic_api_key,
                    timeout=timeout,
                )

            return AsyncOpenAI(
                base_url=settings.hermes_endpoint_url,
                api_key=settings.hermes_api_key,
                timeout=timeout,
            )
        except ImportError:
            logger.warning("openai package not installed — LLM features disabled")
            self._available = False
            return None

    @property
    def _classify_timeout(self) -> float:
        return max(1.0, float(settings.llm_classify_timeout))

    @property
    def _response_timeout(self) -> float:
        return max(1.0, float(settings.llm_timeout))

    @property
    def _active_model(self) -> str:
        """Pick the model string appropriate for the active tier/provider."""
        if self._active_tier == "cloud":
            return settings.llm_cloud_fallback_model
        provider = (settings.default_llm_provider or "hermes").lower()
        if provider == "openai" and settings.openai_api_key:
            return settings.default_llm_model
        if provider == "anthropic" and settings.anthropic_api_key:
            return settings.default_llm_model
        if self._active_tier == "secondary":
            return settings.llm_secondary_model
        return settings.llm_primary_model

    def _is_blocked(self) -> bool:
        if self._available is not False:
            return False
        if self._last_failure_at is not None:
            elapsed = time.monotonic() - self._last_failure_at
            if elapsed >= _CIRCUIT_RESET_SECONDS:
                logger.info(
                    "LLM circuit breaker resetting — retrying primary model",
                    elapsed_s=round(elapsed, 1),
                    model=settings.llm_primary_model,
                )
                self._available = None
                self._last_failure_at = None
                self._active_tier = "primary"
                return False
        return True

    def _mark_unavailable(self, error: str) -> None:
        """
        Tier escalation on connection/timeout failures:
          primary  → secondary
          secondary → cloud (if enabled, has key, and budget remains)
          cloud    → fully circuit-break (keyword-only fallback)
        """
        if self._active_tier == "primary":
            logger.warning(
                "Primary LLM unavailable — falling back to secondary model",
                primary=settings.llm_primary_model,
                secondary=settings.llm_secondary_model,
                error=error,
            )
            self._active_tier = "secondary"
            self._available = None
            self._last_failure_at = None
        elif self._active_tier == "secondary":
            cloud_ok = (
                settings.llm_cloud_fallback_enabled
                and self._cloud_budget_remaining() > 0
                and (
                    (settings.llm_cloud_fallback_provider == "openai" and settings.openai_api_key)
                    or (settings.llm_cloud_fallback_provider == "anthropic" and settings.anthropic_api_key)
                )
            )
            if cloud_ok:
                logger.warning(
                    "Both local LLMs unavailable — escalating to cloud fallback",
                    cloud_provider=settings.llm_cloud_fallback_provider,
                    cloud_model=settings.llm_cloud_fallback_model,
                    budget_remaining_usd=round(self._cloud_budget_remaining(), 4),
                    error=error,
                )
                self._active_tier = "cloud"
                self._available = None
                self._last_failure_at = None
            else:
                logger.warning(
                    "Both local LLMs unavailable and no cloud fallback — keyword-only mode",
                    error=error,
                )
                self._available = False
                self._last_failure_at = time.monotonic()
        else:
            logger.warning(
                "Cloud LLM also unavailable — using keyword classifier only",
                model=settings.llm_cloud_fallback_model,
                error=error,
            )
            self._available = False
            self._last_failure_at = time.monotonic()

    # ── Public API ────────────────────────────────────────────────────────────

    async def classify(self, message: str, history: list[dict] | None = None) -> Optional[dict]:
        """
        Extract structured intent from a natural-language plumbing request.
        Tries primary model first; falls back to secondary on failure.
        Returns None if both models are unavailable.
        """
        if self._is_blocked():
            return None

        client = self._make_client(timeout=self._classify_timeout)
        if client is None:
            return None

        try:
            messages: list[dict] = [{"role": "system", "content": _build_classify_system_prompt()}]
            if history:
                for turn in history[-6:]:  # last 3 exchanges max
                    role = turn.get("role", "user")
                    content = turn.get("content", "")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": message})

            model = self._active_model
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=320,
            )

            raw = (response.choices[0].message.content or "{}").strip()
            data = json.loads(raw)

            county = str(data.get("county") or "Dallas").strip().title()
            if county not in {"Dallas", "Tarrant", "Collin", "Denton", "Rockwall", "Parker", "Kaufman"}:
                county = "Dallas"

            from app.services.pricing_defaults import CITY_ZONE_MULTIPLIERS
            raw_city = (data.get("city") or "").strip().lower()
            city = raw_city if raw_city in CITY_ZONE_MULTIPLIERS else None
            raw_task_code = str(data.get("task_code") or "").strip().upper()
            task_code = raw_task_code if raw_task_code in _VALID_TASK_CODES else None

            result = {
                "task_code":          task_code,
                "access_type":        data.get("access_type", "first_floor"),
                "urgency":            data.get("urgency", "standard"),
                "county":             county,
                "city":               city,
                "quantity":           max(1, min(20, int(data.get("quantity") or 1))),
                "preferred_supplier": data.get("preferred_supplier") or None,
                "confidence":         max(0.0, min(1.0, float(data.get("confidence") or 0.85))),
            }

            self._available = True
            if self._active_tier == "cloud":
                try:
                    usage = getattr(response, "usage", None)
                    self._record_cloud_usage(int(getattr(usage, "total_tokens", 0)) if usage else 0)
                except Exception:
                    pass
            logger.info(
                "LLM classification",
                task_code=result["task_code"],
                confidence=result["confidence"],
                city=city,
                model=model,
                tier=self._active_tier,
            )
            return result

        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            if "Connection" in err_type or "Timeout" in err_type or "ReadTimeout" in err_type:
                self._mark_unavailable(str(e))
                # Retry immediately on next tier if we just promoted (secondary or cloud)
                if self._active_tier in ("secondary", "cloud") and self._available is None:
                    return await self.classify(message, history)
            else:
                logger.warning("LLM classify parse error", error=str(e), error_type=err_type)
            return None

    async def generate_response(
        self,
        message: str,
        grand_total: float,
        labor_total: float,
        materials_total: float,
        tax_total: float,
        template_name: str,
        county: str,
        quantity: int = 1,
        history: list[dict] | None = None,
        context: str | None = None,
    ) -> Optional[str]:
        """
        Generate a conversational, contractor-style opener for the pricing response.
        Returns None if both models are unavailable.
        """
        if self._is_blocked():
            return None

        client = self._make_client(timeout=self._response_timeout)
        if client is None:
            return None

        qty_note = f" (×{quantity} units — ${grand_total / quantity:,.0f} each)" if quantity > 1 else ""
        context_note = f"\n\nSupporting technical context:\n{context}" if context else ""

        user_prompt = (
            f'Customer question: "{message}"\n\n'
            f"Estimate: {template_name} — {county} County, TX{qty_note}\n"
            f"  Grand total: ${grand_total:,.0f}\n"
            f"  Labor: ${labor_total:,.0f}  |  Materials: ${materials_total:,.0f}  |  Tax: ${tax_total:,.2f}"
            f"{context_note}\n\n"
            "Write your 2-3 sentence response:"
        )

        messages: list[dict] = [{"role": "system", "content": _RESPONSE_SYSTEM}]
        if history:
            for turn in history[-4:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        try:
            model = self._active_model
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.35,
                max_tokens=200,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                logger.debug("LLM response generated", chars=len(text), model=model, tier=self._active_tier)
            if self._active_tier == "cloud":
                try:
                    usage = getattr(response, "usage", None)
                    self._record_cloud_usage(int(getattr(usage, "total_tokens", 0)) if usage else 0)
                except Exception:
                    pass
            return text or None

        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            if "Connection" in err_type or "Timeout" in err_type or "ReadTimeout" in err_type:
                self._mark_unavailable(str(e))
            else:
                logger.debug("LLM response generation skipped", error=str(e))
            return None

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 400,
        temperature: float = 0.4,
    ) -> Optional[str]:
        """Generic single-shot completion. Returns None when LLM is unavailable."""
        if self._is_blocked():
            return None
        client = self._make_client(timeout=self._response_timeout)
        if client is None:
            return None
        try:
            model = self._active_model
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = (response.choices[0].message.content or "").strip()
            if self._active_tier == "cloud":
                try:
                    usage = getattr(response, "usage", None)
                    self._record_cloud_usage(int(getattr(usage, "total_tokens", 0)) if usage else 0)
                except Exception:
                    pass
            return text or None
        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            if "Connection" in err_type or "Timeout" in err_type or "ReadTimeout" in err_type:
                self._mark_unavailable(str(e))
            else:
                logger.debug("LLM completion skipped", error=str(e))
            return None

    @staticmethod
    def make_static_narrative(
        template_name: str,
        grand_total: float,
        labor_total: float,
        materials_total: float,
        county: str,
        quantity: int = 1,
    ) -> str:
        qty_note = f" (×{quantity})" if quantity > 1 else ""
        return (
            f"For **{template_name}**{qty_note} in {county} County, TX, "
            f"you're looking at **${grand_total:,.0f}** total — "
            f"${labor_total:,.0f} labor and ${materials_total:,.0f} materials. "
            f"See the full breakdown below."
        )

    async def generate_response_stream(
        self,
        message: str,
        grand_total: float,
        labor_total: float,
        materials_total: float,
        tax_total: float,
        template_name: str,
        county: str,
        quantity: int = 1,
        history: list[dict] | None = None,
        context: str | None = None,
    ):
        """
        Async generator that yields text chunks for SSE streaming.
        Yields a static fallback narrative when the LLM is blocked/unavailable.
        """
        if self._is_blocked():
            yield self.make_static_narrative(
                template_name, grand_total, labor_total, materials_total, county, quantity
            )
            return

        client = self._make_client(timeout=self._response_timeout)
        if client is None:
            yield self.make_static_narrative(
                template_name, grand_total, labor_total, materials_total, county, quantity
            )
            return

        qty_note = f" (×{quantity} units — ${grand_total / quantity:,.0f} each)" if quantity > 1 else ""
        context_note = f"\n\nSupporting technical context:\n{context}" if context else ""

        user_prompt = (
            f'Customer question: "{message}"\n\n'
            f"Estimate: {template_name} — {county} County, TX{qty_note}\n"
            f"  Grand total: ${grand_total:,.0f}\n"
            f"  Labor: ${labor_total:,.0f}  |  Materials: ${materials_total:,.0f}  |  Tax: ${tax_total:,.2f}"
            f"{context_note}\n\n"
            "Write your 2-3 sentence response:"
        )

        messages: list[dict] = [{"role": "system", "content": _RESPONSE_SYSTEM}]
        if history:
            for turn in history[-4:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        try:
            model = self._active_model
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.35,
                max_tokens=200,
                stream=True,
            )
            yielded_any = False
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yielded_any = True
                    yield delta
            if not yielded_any:
                self._mark_unavailable("Model returned empty response")
                yield self.make_static_narrative(
                    template_name, grand_total, labor_total, materials_total, county, quantity
                )
        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            if any(k in err_type for k in ("Timeout", "ReadTimeout", "Connection", "Connect")):
                self._mark_unavailable(str(e))
            logger.debug("LLM stream generation skipped", error=str(e))
            yield self.make_static_narrative(
                template_name, grand_total, labor_total, materials_total, county, quantity
            )

    async def check_available(self) -> bool:
        """
        Probe the Ollama endpoint with the primary model.
        Returns True if reachable. Logs the active model tier.
        """
        client = self._make_client(timeout=max(10.0, self._classify_timeout))
        if client is None:
            return False
        try:
            await client.models.list()
            self._available = True
            logger.info(
                "LLM reachable",
                endpoint=settings.hermes_endpoint_url,
                primary=settings.llm_primary_model,
                secondary=settings.llm_secondary_model,
                active_tier=self._active_tier,
                active_model=self._active_model,
            )
            return True
        except Exception as e:  # noqa: BLE001
            self._mark_unavailable(str(e))
            return False


# Module-level singleton
llm_service = LLMService()
