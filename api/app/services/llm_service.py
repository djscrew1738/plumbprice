"""
LLM Service — Hermes 3 via Ollama (OpenAI-compatible API).

Responsibilities:
  1. Intent classification  — structured JSON extraction from natural language
  2. Response generation    — contractor-style conversational answer

Architecture:
  - Uses the openai SDK with a custom base_url pointing at Ollama
  - Circuit-breaker: after the first connection failure, skips LLM for the
    remainder of the process lifetime to avoid blocking request latency
  - Zero hard dependency: if Ollama/Hermes is not running, the agent falls
    back cleanly to the keyword-only classifier and template formatter

Ollama setup:
  ollama pull hermes3          # or: nous-hermes2, hermes3:8b, etc.
  ollama serve                 # listens on localhost:11434 by default
"""

from __future__ import annotations

import json
from typing import Optional
import structlog

from app.config import settings

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
  GAS_LINE_REPAIR_MINOR, GAS_LINE_NEW_RUN

Return ONLY valid JSON with these exact keys:
{
  "task_code": string | null,
  "access_type": "first_floor" | "second_floor" | "attic" | "crawlspace" | "slab" | "basement",
  "urgency": "standard" | "same_day" | "emergency",
  "county": "Dallas" | "Tarrant" | "Collin" | "Denton" | "Rockwall" | "Parker",
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
    """Hermes 3 via Ollama — OpenAI-compatible local LLM inference."""

    def __init__(self) -> None:
        self._client = None
        # None = untested | True = known good | False = known unavailable
        self._available: Optional[bool] = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _client_or_none(self):
        """Lazily create the OpenAI-compat client on first use."""
        if self._client is not None:
            return self._client
        if not settings.hermes_endpoint_url:
            return None
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url=settings.hermes_endpoint_url,
                api_key=settings.hermes_api_key,
                timeout=settings.llm_timeout,
            )
            return self._client
        except ImportError:
            logger.warning("openai package not installed — LLM features disabled")
            self._available = False
            return None

    def _is_blocked(self) -> bool:
        return self._available is False

    def _mark_unavailable(self, error: str) -> None:
        if self._available is None:
            logger.warning(
                "Hermes LLM unavailable — using keyword classifier only",
                endpoint=settings.hermes_endpoint_url,
                model=settings.hermes_model,
                error=error,
            )
        self._available = False

    # ── Public API ────────────────────────────────────────────────────────────

    async def classify(self, message: str) -> Optional[dict]:
        """
        Extract structured intent from a natural-language plumbing request.

        Returns a dict with keys matching the keyword classifier output format,
        or None if the LLM is unavailable / the parse fails.
        """
        if self._is_blocked():
            return None

        client = self._client_or_none()
        if client is None:
            return None

        try:
            from openai import APIConnectionError, APITimeoutError

            response = await client.chat.completions.create(
                model=settings.hermes_model,
                messages=[
                    {"role": "system", "content": _CLASSIFY_SYSTEM},
                    {"role": "user",   "content": message},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=300,
            )

            raw = (response.choices[0].message.content or "{}").strip()
            data = json.loads(raw)

            # Normalise
            county = str(data.get("county") or "Dallas").strip().title()
            if county not in {"Dallas", "Tarrant", "Collin", "Denton", "Rockwall", "Parker"}:
                county = "Dallas"

            result = {
                "task_code":          data.get("task_code") or None,
                "access_type":        data.get("access_type", "first_floor"),
                "urgency":            data.get("urgency", "standard"),
                "county":             county,
                "quantity":           max(1, min(20, int(data.get("quantity") or 1))),
                "preferred_supplier": data.get("preferred_supplier") or None,
                "confidence":         max(0.0, min(1.0, float(data.get("confidence") or 0.85))),
            }

            self._available = True
            logger.info(
                "LLM classification",
                task_code=result["task_code"],
                confidence=result["confidence"],
                model=settings.hermes_model,
            )
            return result

        except Exception as e:  # noqa: BLE001
            # Connection errors → mark unavailable; parse errors → log + return None
            err_type = type(e).__name__
            if "Connection" in err_type or "Timeout" in err_type:
                self._mark_unavailable(str(e))
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
    ) -> Optional[str]:
        """
        Generate a conversational, contractor-style opener for the pricing response.

        Returns None if the LLM is unavailable — the caller falls back to the
        template-based formatter.
        """
        if self._is_blocked():
            return None

        client = self._client_or_none()
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

        try:
            response = await self._client_or_none().chat.completions.create(  # type: ignore[union-attr]
                model=settings.hermes_model,
                messages=[
                    {"role": "system", "content": _RESPONSE_SYSTEM},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.35,
                max_tokens=200,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                logger.debug("LLM response generated", chars=len(text))
            return text or None

        except Exception as e:  # noqa: BLE001
            logger.debug("LLM response generation skipped", error=str(e))
            return None

    async def check_available(self) -> bool:
        """
        Probe the Ollama endpoint. Returns True if reachable.
        Caches the result — call once at startup.
        """
        client = self._client_or_none()
        if client is None:
            return False
        try:
            await client.models.list()
            self._available = True
            logger.info("Hermes LLM reachable", endpoint=settings.hermes_endpoint_url, model=settings.hermes_model)
            return True
        except Exception as e:  # noqa: BLE001
            self._mark_unavailable(str(e))
            return False


# Module-level singleton
llm_service = LLMService()
