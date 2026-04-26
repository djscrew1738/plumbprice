"""
Phase 4 — Voice quoting.

Two endpoints:

* `POST /api/v1/voice/transcribe` — raw STT. Returns just the transcript.
  Useful if the front-end wants to show the transcript and let the user
  confirm before pricing.

* `POST /api/v1/voice/quote` — speech-to-quote. Transcribes, then runs the
  result through the existing chat pricing pipeline so the response includes
  a priced draft.
"""

from __future__ import annotations

import base64
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.limiter import limiter
from app.database import get_db
from app.models.sessions import ChatMessage as ChatMessageModel, ChatSession
from app.models.users import User
from app.services.agent import process_chat_message
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service

logger = structlog.get_logger()
router = APIRouter()


def _validate_audio(file: UploadFile, audio_bytes: bytes) -> None:
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio")
    if len(audio_bytes) > settings.voice_stt_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large (max {settings.voice_stt_max_bytes // (1024 * 1024)} MB)",
        )
    ctype = (file.content_type or "").lower()
    name = (file.filename or "").lower()
    if ctype and not (ctype.startswith("audio/") or ctype.startswith("video/")):
        # iOS sends `video/mp4` for some recordings; we permit it.
        # But anything else (image/, application/json) is rejected.
        if not name.endswith((".webm", ".ogg", ".mp3", ".m4a", ".wav", ".mp4", ".flac")):
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {ctype}")


@router.get("/status")
async def voice_status(current_user: User = Depends(get_current_user)):
    """Lightweight status for the UI to know if voice is available."""
    return {
        "stt": stt_service.status(),
        "tts": tts_service.status(),
    }


@router.post("/transcribe")
@limiter.limit("30/minute")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe a short audio clip → plain text."""
    audio = await file.read()
    _validate_audio(file, audio)
    result = await stt_service.transcribe(
        audio,
        filename=file.filename or "audio.webm",
    )
    if result["status"] != "ok":
        # Use 503 for "service down / unconfigured / over budget" so the UI
        # can show a clear retry-later message.
        if result["status"] in {"disabled", "budget_exhausted"}:
            raise HTTPException(status_code=503, detail=result["error"])
        raise HTTPException(status_code=502, detail=result["error"] or "transcription failed")
    return {"status": "ok", "text": result["text"], "duration_s": result["duration_s"]}


@router.post("/quote")
@limiter.limit("15/minute")
async def voice_quote(
    request: Request,
    file: UploadFile = File(...),
    county: Optional[str] = Form(None),
    preferred_supplier: Optional[str] = Form(None),
    job_type: Optional[str] = Form(None),
    session_id: Optional[int] = Form(None),
    tts: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transcribe, then run through the chat agent to return a priced draft.

    Multi-turn (Phase 4.5): when `session_id` is provided, prior ChatMessages
    are loaded as `history` so the agent has full conversation context.
    Both the user transcript and assistant answer are persisted as
    ChatMessage rows on the session, mirroring the text /chat/price flow.

    Optional: when `tts=true` and TTS is enabled, the response includes a
    base64 MP3 of the spoken answer (`audio_base64`, `audio_format`).
    """
    audio = await file.read()
    _validate_audio(file, audio)

    stt = await stt_service.transcribe(audio, filename=file.filename or "audio.webm")
    if stt["status"] != "ok":
        if stt["status"] in {"disabled", "budget_exhausted"}:
            raise HTTPException(status_code=503, detail=stt["error"])
        raise HTTPException(status_code=502, detail=stt["error"] or "transcription failed")

    transcript = stt["text"]
    if not transcript:
        return {
            "status": "no_speech",
            "transcript": "",
            "answer": "I couldn't hear any speech in that clip. Try again in a quiet spot.",
            "estimate": None,
            "session_id": session_id,
        }

    # Multi-turn: load prior history if a session was passed in.
    history: list[dict] | None = None
    session: ChatSession | None = None
    if session_id:
        session = (
            await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        rows = (
            await db.execute(
                select(ChatMessageModel)
                .where(ChatMessageModel.session_id == session_id)
                .order_by(ChatMessageModel.created_at)
                .limit(20)
            )
        ).scalars().all()
        history = [{"role": r.role, "content": r.content} for r in rows]

    logger.info("voice.quote", user_id=current_user.id,
                transcript_chars=len(transcript), county=county,
                session_id=session_id, turns=len(history or []))

    result = await process_chat_message(
        message=transcript,
        county=county or None,
        preferred_supplier=preferred_supplier,
        job_type=job_type,
        history=history,
        db=db,
        user_id=current_user.id,
    )
    estimate_result = result.pop("_estimate_result", None)
    estimate_summary = None
    if estimate_result is not None:
        estimate_summary = {
            "task_code": getattr(estimate_result, "template_code", None),
            "county": getattr(estimate_result, "county", None),
            "grand_total": float(getattr(estimate_result, "grand_total", 0.0) or 0.0),
            "labor_total": float(getattr(estimate_result, "labor_total", 0.0) or 0.0),
            "materials_total": float(getattr(estimate_result, "materials_total", 0.0) or 0.0),
            "tax_total": float(getattr(estimate_result, "tax_total", 0.0) or 0.0),
            "confidence_label": getattr(estimate_result, "confidence_label", None),
        }

    answer = result.get("answer", "")

    # Persist this turn as part of a ChatSession (creates one if needed).
    if session is None:
        session = ChatSession(
            user_id=current_user.id,
            organization_id=getattr(current_user, "organization_id", None),
            title=transcript[:80],
            county=county,
        )
        db.add(session)
        await db.flush()
    db.add(ChatMessageModel(session_id=session.id, role="user", content=transcript))
    db.add(ChatMessageModel(session_id=session.id, role="assistant", content=answer))
    await db.commit()

    # Optional spoken reply.
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    tts_status: Optional[str] = None
    if tts:
        synth = await tts_service.synthesize(answer)
        tts_status = synth["status"]
        if synth["status"] == "ok" and synth["audio"]:
            audio_base64 = base64.b64encode(synth["audio"]).decode("ascii")
            audio_format = synth["format"]

    return {
        "status": "ok",
        "transcript": transcript,
        "answer": answer,
        "task_code": result.get("task_code"),
        "county": result.get("county"),
        "estimate": estimate_summary,
        "stt_duration_s": stt["duration_s"],
        "session_id": session.id,
        "audio_base64": audio_base64,
        "audio_format": audio_format,
        "tts_status": tts_status,
    }


# ─── Phase 4.5 — standalone TTS endpoint ──────────────────────────────────────


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/speak")
@limiter.limit("30/minute")
async def voice_speak(
    request: Request,
    body: SpeakRequest,
    current_user: User = Depends(get_current_user),
):
    """Synthesize text → audio bytes. Returns audio/mpeg (or whatever the
    configured `voice_tts_format` is). 503 on disabled / over-budget."""
    result = await tts_service.synthesize(body.text)
    if result["status"] != "ok":
        if result["status"] in {"disabled", "budget_exhausted"}:
            raise HTTPException(status_code=503, detail=result["error"])
        raise HTTPException(status_code=502, detail=result["error"] or "tts failed")
    media = "audio/mpeg" if result["format"] == "mp3" else f"audio/{result['format']}"
    return Response(content=result["audio"], media_type=media)
