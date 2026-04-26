"""Anomaly scoring for public-agent traffic.

Heuristics (fast, deterministic, no LLM dependency). Each fires
independently and contributes a weight; the final score is clipped to
[0, 1]. Flags are short codes consumed by the admin review UI.

Triggers:
  * very_long       — message > 2000 chars (DoS / prompt-stuffing)
  * very_short      — message <= 2 chars (probe / accidental)
  * prompt_injection — known injection phrases
  * profanity        — abusive language (basic list, deliberately small)
  * very_high_total  — quote total > $50k (sanity check on widget output)
  * uncertain_status — status != "ok" (no estimate produced)
  * burst_from_ip    — ≥ 5 audits from same IP within last 60s
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_agent_audit import PublicAgentAudit


_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |the )?(previous|prior|above) (instructions|prompts?)", re.I),
    re.compile(r"you are (now |actually )?(a |an )?(?:dan|developer mode|jailbroken)", re.I),
    re.compile(r"system\s*[:>]\s*", re.I),
    re.compile(r"```\s*system", re.I),
    re.compile(r"reveal (your |the )?(system )?(prompt|instructions?)", re.I),
    re.compile(r"\bprintenv\b|\benv\s+\|\s*", re.I),
]

_PROFANITY = {
    "fuck", "shit", "bitch", "asshole", "cunt", "dick", "bastard",
}

_BURST_WINDOW_SECONDS = 60
_BURST_THRESHOLD = 5

_HIGH_TOTAL = 50_000.0


def _word_set(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z]+", text)}


async def score_request(
    db: AsyncSession,
    *,
    message: str,
    client_ip: Optional[str],
    status: str,
    grand_total: Optional[float],
) -> tuple[float, list[str]]:
    """Returns (score in [0,1], list of flag codes). Async only because of burst lookup."""
    flags: list[str] = []
    score = 0.0

    msg = message or ""

    if len(msg) > 2000:
        flags.append("very_long")
        score += 0.4
    elif len(msg.strip()) <= 2:
        flags.append("very_short")
        score += 0.15

    for pat in _INJECTION_PATTERNS:
        if pat.search(msg):
            flags.append("prompt_injection")
            score += 0.6
            break

    words = _word_set(msg)
    if words & _PROFANITY:
        flags.append("profanity")
        score += 0.2

    if grand_total is not None and grand_total > _HIGH_TOTAL:
        flags.append("very_high_total")
        score += 0.4

    if status != "ok":
        flags.append("uncertain_status")
        score += 0.05

    if client_ip:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=_BURST_WINDOW_SECONDS)
        res = await db.execute(
            select(func.count(PublicAgentAudit.id))
            .where(PublicAgentAudit.client_ip == client_ip)
            .where(PublicAgentAudit.created_at >= cutoff)
        )
        recent = int(res.scalar() or 0)
        if recent >= _BURST_THRESHOLD:
            flags.append("burst_from_ip")
            score += 0.3

    return min(score, 1.0), flags


async def record_audit(
    db: AsyncSession,
    *,
    client_ip: Optional[str],
    user_agent: Optional[str],
    message: str,
    county: Optional[str],
    customer_email: Optional[str],
    status: str,
    task_code: Optional[str],
    grand_total: Optional[float],
    lead_id: Optional[int],
) -> PublicAgentAudit:
    score, flags = await score_request(
        db,
        message=message,
        client_ip=client_ip,
        status=status,
        grand_total=grand_total,
    )
    audit = PublicAgentAudit(
        client_ip=client_ip,
        user_agent=(user_agent or "")[:500] or None,
        message=message,
        county=county,
        customer_email=customer_email,
        status=status,
        task_code=task_code,
        grand_total=grand_total,
        lead_id=lead_id,
        anomaly_score=score,
        anomaly_flags=flags or None,
    )
    db.add(audit)
    await db.flush()
    return audit
