"""
Phase 4 — Speech-to-text service.

Uses OpenAI Whisper API for transcription, gated by a separate daily USD cap
(`voice_stt_daily_cap_usd`) so STT spend can't drain the LLM budget.

If `openai_api_key` is unset the service returns a structured "unavailable"
result rather than raising — callers (the voice router) should surface this
to the UI so the user gets a useful error instead of a 500.
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from app.config import settings

logger = structlog.get_logger()


class STTService:
    """Singleton wrapper around OpenAI Whisper with a daily cost cap."""

    def __init__(self) -> None:
        self._cost_day: Optional[str] = None
        self._cost_usd: float = 0.0
        self._calls_today: int = 0

    # ── Budget bookkeeping ────────────────────────────────────────────────
    def _reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._cost_day != today:
            self._cost_day = today
            self._cost_usd = 0.0
            self._calls_today = 0

    def _budget_remaining_usd(self) -> float:
        self._reset_if_new_day()
        return max(0.0, settings.voice_stt_daily_cap_usd - self._cost_usd)

    def _record_call(self, seconds: float) -> None:
        self._reset_if_new_day()
        minutes = max(seconds, 1.0) / 60.0
        cost = minutes * settings.voice_stt_cost_per_minute_usd
        self._cost_usd += cost
        self._calls_today += 1

    # ── Public ────────────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        self._reset_if_new_day()
        return {
            "enabled": settings.voice_stt_enabled,
            "model": settings.voice_stt_model,
            "has_api_key": bool(settings.openai_api_key),
            "calls_today": self._calls_today,
            "cost_today_usd": round(self._cost_usd, 4),
            "cap_usd": settings.voice_stt_daily_cap_usd,
            "budget_remaining_usd": round(self._budget_remaining_usd(), 4),
        }

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "audio.webm",
        approx_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe a single short audio clip.

        Returns:
            {"status": "ok"|"error"|"disabled"|"budget_exhausted",
             "text": str, "duration_s": float, "error": str|None}
        """
        if not settings.voice_stt_enabled:
            return {"status": "disabled", "text": "", "duration_s": 0.0,
                    "error": "voice STT is disabled in config"}
        if not settings.openai_api_key:
            return {"status": "disabled", "text": "", "duration_s": 0.0,
                    "error": "OPENAI_API_KEY not configured"}
        if self._budget_remaining_usd() <= 0:
            return {"status": "budget_exhausted", "text": "", "duration_s": 0.0,
                    "error": f"daily STT cap of ${settings.voice_stt_daily_cap_usd} reached"}

        # Lazy import — service file shouldn't blow up at boot if openai is missing.
        try:
            from openai import AsyncOpenAI
        except Exception as e:  # pragma: no cover
            return {"status": "error", "text": "", "duration_s": 0.0,
                    "error": f"openai sdk unavailable: {e}"}

        started = time.monotonic()
        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            buf = io.BytesIO(audio_bytes)
            buf.name = filename  # OpenAI sniffs format from filename
            resp = await client.audio.transcriptions.create(
                model=settings.voice_stt_model,
                file=buf,
            )
            text = (getattr(resp, "text", None) or "").strip()
            wall_s = time.monotonic() - started
            self._record_call(approx_seconds or wall_s)
            logger.info("stt.transcribe_ok",
                        bytes=len(audio_bytes),
                        seconds=round(wall_s, 2),
                        chars=len(text))
            return {"status": "ok", "text": text,
                    "duration_s": round(wall_s, 2), "error": None}
        except Exception as e:
            logger.error("stt.transcribe_error", error=str(e))
            return {"status": "error", "text": "", "duration_s": 0.0, "error": str(e)}


stt_service = STTService()
