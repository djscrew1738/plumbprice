"""
LLM Service — dual-model Ollama backend (OpenAI-compatible API).

Model strategy
--------------
  Primary   : qwen2.5:7b-instruct  (better reasoning, richer JSON)
  Secondary : hermes3:3b            (fast fallback, ~3 s)

The service tracks which model is active.  When the primary model fails
(connection error or timeout) it circuit-breaks down to the secondary.
After _CIRCUIT_RESET_SECONDS of silence it retries the primary.
Both models fall through to the keyword-only classifier and template
formatter if neither is available.
"""

from __future__ import annotations

import json
import time
from typing import Optional
import structlog

from app.config import settings

_CIRCUIT_RESET_SECONDS = 120   # retry primary after this many seconds
_CLASSIFY_TIMEOUT      = 20.0  # budget for intent classification
_RESPONSE_TIMEOUT      = 30.0  # budget for conversational generation

logger = structlog.get_logger()

# ── Prompts ───────────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You are a plumbing estimator AI for DFW (Dallas-Fort Worth) Texas contractors.
Classify the user's natural-language plumbing request into structured JSON.

Valid task_code values (pick the single best match, or null if unknown):
  TOILET_REPLACE_STANDARD, TOILET_COMFORT_HEIGHT,
  WH_50G_GAS_STANDARD, WH_50G_GAS_ATTIC, WH_40G_GAS_STANDARD,
  WH_50G_ELECTRIC_STANDARD, WH_TANKLESS_GAS,
  PRV_REPLACE, HOSE_BIB_REPLACE, SHOWER_VALVE_REPLACE,
  KITCHEN_FAUCET_REPLACE, GARBAGE_DISPOSAL_INSTALL,
  LAV_FAUCET_REPLACE, ANGLE_STOP_REPLACE, PTRAP_REPLACE,
  DRAIN_CLEAN_STANDARD, MAIN_LINE_CLEAN, HYDROJETTING,
  SLAB_LEAK_REPAIR, LEAK_DETECTION, WATER_SOFTENER_INSTALL,
  TUB_SHOWER_COMBO_REPLACE, EXPANSION_TANK_ONLY,
  GAS_LINE_REPAIR_MINOR, GAS_LINE_NEW_RUN,
  WHOLE_HOUSE_REPIPE_PEX, SEWER_SPOT_REPAIR,
  RECIRC_PUMP_INSTALL, DISHWASHER_HOOKUP, WATER_MAIN_REPAIR,
  CAMERA_INSPECTION, BACKFLOW_PREVENTER_INSTALL,
  CLEAN_OUT_INSTALL, WATER_FILTER_WHOLE_HOUSE

Return ONLY valid JSON with these exact keys:
{
  "task_code": string | null,
  "access_type": "first_floor" | "second_floor" | "attic" | "crawlspace" | "slab" | "basement",
  "urgency": "standard" | "same_day" | "emergency",
  "county": "Dallas" | "Tarrant" | "Collin" | "Denton" | "Rockwall" | "Parker" | "Kaufman",
  "city": string | null,
  "quantity": integer (1–20),
  "preferred_supplier": "ferguson" | "moore_supply" | "apex" | null,
  "confidence": float (0.0–1.0)
}
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
        # Which model tier is currently active: "primary" or "secondary"
        self._active_tier: str = "primary"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def _active_model(self) -> str:
        if self._active_tier == "secondary":
            return settings.llm_secondary_model
        return settings.llm_primary_model

    def _make_client(self, timeout: float):
        """Create a fresh AsyncOpenAI client with the given timeout."""
        try:
            from openai import AsyncOpenAI
            return AsyncOpenAI(
                base_url=settings.hermes_endpoint_url,
                api_key=settings.hermes_api_key,
                timeout=timeout,
            )
        except ImportError:
            logger.warning("openai package not installed — LLM features disabled")
            self._available = False
            return None

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
        On first failure of the primary, promote secondary.
        On second failure (secondary already active), fully circuit-break.
        """
        if self._active_tier == "primary":
            logger.warning(
                "Primary LLM unavailable — falling back to secondary model",
                primary=settings.llm_primary_model,
                secondary=settings.llm_secondary_model,
                error=error,
            )
            self._active_tier = "secondary"
            self._available = None          # allow immediate retry on secondary
            self._last_failure_at = None
        else:
            logger.warning(
                "Secondary LLM also unavailable — using keyword classifier only",
                model=settings.llm_secondary_model,
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

        client = self._make_client(timeout=_CLASSIFY_TIMEOUT)
        if client is None:
            return None

        try:
            messages: list[dict] = [{"role": "system", "content": _CLASSIFY_SYSTEM}]
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

            from app.services.pricing_engine import CITY_ZONE_MULTIPLIERS
            raw_city = (data.get("city") or "").strip().lower()
            city = raw_city if raw_city in CITY_ZONE_MULTIPLIERS else None

            result = {
                "task_code":          data.get("task_code") or None,
                "access_type":        data.get("access_type", "first_floor"),
                "urgency":            data.get("urgency", "standard"),
                "county":             county,
                "city":               city,
                "quantity":           max(1, min(20, int(data.get("quantity") or 1))),
                "preferred_supplier": data.get("preferred_supplier") or None,
                "confidence":         max(0.0, min(1.0, float(data.get("confidence") or 0.85))),
            }

            self._available = True
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
                # Retry immediately on the secondary if we just promoted it
                if self._active_tier == "secondary" and self._available is None:
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
    ) -> Optional[str]:
        """
        Generate a conversational, contractor-style opener for the pricing response.
        Returns None if both models are unavailable.
        """
        if self._is_blocked():
            return None

        client = self._make_client(timeout=_RESPONSE_TIMEOUT)
        if client is None:
            return None

        qty_note = f" (×{quantity} units — ${grand_total / quantity:,.0f} each)" if quantity > 1 else ""
        user_prompt = (
            f'Customer question: "{message}"\n\n'
            f"Estimate: {template_name} — {county} County, TX{qty_note}\n"
            f"  Grand total: ${grand_total:,.0f}\n"
            f"  Labor: ${labor_total:,.0f}  |  Materials: ${materials_total:,.0f}  |  Tax: ${tax_total:,.2f}\n\n"
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
            return text or None

        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            if "Connection" in err_type or "Timeout" in err_type or "ReadTimeout" in err_type:
                self._mark_unavailable(str(e))
            else:
                logger.debug("LLM response generation skipped", error=str(e))
            return None

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
    ):
        """
        Async generator that yields text chunks for SSE streaming.
        Yields nothing on failure so the caller can close the stream cleanly.
        """
        if self._is_blocked():
            return

        client = self._make_client(timeout=_RESPONSE_TIMEOUT)
        if client is None:
            return

        qty_note = f" (×{quantity} units — ${grand_total / quantity:,.0f} each)" if quantity > 1 else ""
        user_prompt = (
            f'Customer question: "{message}"\n\n'
            f"Estimate: {template_name} — {county} County, TX{qty_note}\n"
            f"  Grand total: ${grand_total:,.0f}\n"
            f"  Labor: ${labor_total:,.0f}  |  Materials: ${materials_total:,.0f}  |  Tax: ${tax_total:,.2f}\n\n"
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
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as e:  # noqa: BLE001
            logger.debug("LLM stream generation skipped", error=str(e))

    async def check_available(self) -> bool:
        """
        Probe the Ollama endpoint with the primary model.
        Returns True if reachable. Logs the active model tier.
        """
        client = self._make_client(timeout=10.0)
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
