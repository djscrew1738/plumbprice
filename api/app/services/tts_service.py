"""
Phase 4.5 — Text-to-speech service.

Mirrors `stt_service` patterns: singleton + per-day USD cap, structured
status responses (no raise on misconfig), lazy openai import.

Used by `/voice/speak` and optionally by `/voice/quote?tts=true` to return
a synthesized audio reply alongside the priced quote.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from app.config import settings

logger = structlog.get_logger()


class TTSService:
    def __init__(self) -> None:
        self._cost_day: Optional[str] = None
        self._cost_usd: float = 0.0
        self._calls_today: int = 0

    def _reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._cost_day != today:
            self._cost_day = today
            self._cost_usd = 0.0
            self._calls_today = 0

    def _budget_remaining_usd(self) -> float:
        self._reset_if_new_day()
        return max(0.0, settings.voice_tts_daily_cap_usd - self._cost_usd)

    def _record_call(self, chars: int) -> None:
        self._reset_if_new_day()
        self._cost_usd += (chars / 1000.0) * settings.voice_tts_cost_per_1k_chars_usd
        self._calls_today += 1

    def status(self) -> Dict[str, Any]:
        self._reset_if_new_day()
        return {
            "enabled": settings.voice_tts_enabled,
            "model": settings.voice_tts_model,
            "voice": settings.voice_tts_voice,
            "format": settings.voice_tts_format,
            "has_api_key": bool(settings.openai_api_key),
            "calls_today": self._calls_today,
            "cost_today_usd": round(self._cost_usd, 4),
            "cap_usd": settings.voice_tts_daily_cap_usd,
            "budget_remaining_usd": round(self._budget_remaining_usd(), 4),
        }

    async def synthesize(self, text: str) -> Dict[str, Any]:
        """
        Returns {"status": "ok"|"disabled"|"budget_exhausted"|"error",
                 "audio": bytes|None, "format": str, "chars": int, "error": str|None}
        """
        text = (text or "").strip()
        if not text:
            return {"status": "error", "audio": None, "format": "",
                    "chars": 0, "error": "empty text"}
        if len(text) > settings.voice_tts_max_chars:
            text = text[: settings.voice_tts_max_chars]

        if not settings.voice_tts_enabled:
            return {"status": "disabled", "audio": None, "format": "",
                    "chars": 0, "error": "voice TTS disabled in config"}
        if not settings.openai_api_key:
            return {"status": "disabled", "audio": None, "format": "",
                    "chars": 0, "error": "OPENAI_API_KEY not configured"}
        if self._budget_remaining_usd() <= 0:
            return {"status": "budget_exhausted", "audio": None, "format": "",
                    "chars": 0,
                    "error": f"daily TTS cap of ${settings.voice_tts_daily_cap_usd} reached"}

        try:
            from openai import AsyncOpenAI
        except Exception as e:
            return {"status": "error", "audio": None, "format": "",
                    "chars": 0, "error": f"openai sdk unavailable: {e}"}

        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.audio.speech.create(
                model=settings.voice_tts_model,
                voice=settings.voice_tts_voice,
                input=text,
                response_format=settings.voice_tts_format,
            )
            audio_bytes = await resp.aread() if hasattr(resp, "aread") else resp.read()
            self._record_call(len(text))
            logger.info("tts.synthesize_ok", chars=len(text), bytes=len(audio_bytes))
            return {"status": "ok", "audio": audio_bytes,
                    "format": settings.voice_tts_format, "chars": len(text), "error": None}
        except Exception as e:
            logger.error("tts.synthesize_error", error=str(e))
            return {"status": "error", "audio": None, "format": "",
                    "chars": 0, "error": str(e)}


tts_service = TTSService()
