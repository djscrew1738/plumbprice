"""Outcomes context service - injects similar past job outcomes into the agent."""
from __future__ import annotations
import re
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.estimates import Estimate
from app.models.outcomes import EstimateOutcome

logger = structlog.get_logger()


def _extract_keywords(text: str) -> list[str]:
    """Pull useful nouns/keywords from a message for ILIKE matching."""
    if not text:
        return []
    stop = {
        "the", "a", "an", "to", "for", "of", "in", "on", "at", "is", "are",
        "and", "or", "i", "we", "my", "our", "with", "how", "much", "what",
        "would", "should", "could", "do", "does", "this", "that", "it",
        "price", "quote", "estimate", "cost", "need", "want", "please",
    }
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
    return [w for w in words if w not in stop][:6]


async def get_similar_outcomes_context(
    db: AsyncSession,
    *,
    user_id: Optional[int],
    organization_id: Optional[int],
    message: str,
    job_type: Optional[str] = None,
    task_code: Optional[str] = None,
    limit: int = 5,
) -> tuple[str, list[dict]]:
    """
    Find similar past jobs (by keyword match in title + same user/org) and
    return both an LLM-context string and a structured payload.

    Returns: (context_text, hits)
      - context_text: human-readable summary for the LLM, "" if no hits
      - hits: list of {estimate_id, title, outcome, final_price, grand_total}
    """
    if user_id is None and organization_id is None:
        return "", []

    keywords = _extract_keywords(message)
    if task_code:
        keywords = [task_code.lower().replace("_", " ")] + keywords

    stmt = (
        select(Estimate, EstimateOutcome)
        .join(EstimateOutcome, EstimateOutcome.estimate_id == Estimate.id)
        .where(Estimate.deleted_at.is_(None))
        .order_by(EstimateOutcome.updated_at.desc())
        .limit(limit * 4)
    )
    if organization_id is not None:
        stmt = stmt.where(Estimate.organization_id == organization_id)
    elif user_id is not None:
        stmt = stmt.where(Estimate.created_by == user_id)
    if job_type:
        stmt = stmt.where(Estimate.job_type == job_type)

    try:
        rows = (await db.execute(stmt)).all()
    except Exception as e:
        logger.warning("outcomes.query_failed", error=str(e))
        return "", []

    if not rows:
        return "", []

    scored: list[tuple[float, Estimate, EstimateOutcome]] = []
    for est, oc in rows:
        title_lc = (est.title or "").lower()
        score = sum(1 for kw in keywords if kw in title_lc)
        if score > 0 or job_type:
            scored.append((score, est, oc))

    scored.sort(key=lambda t: (t[0], t[2].updated_at or t[2].created_at), reverse=True)
    top = scored[:limit]
    if not top:
        return "", []

    hits: list[dict] = []
    won_prices: list[float] = []
    won = lost = pending = 0
    for _score, est, oc in top:
        hit = {
            "estimate_id": est.id,
            "title": est.title,
            "outcome": oc.outcome,
            "final_price": oc.final_price,
            "grand_total": est.grand_total,
        }
        hits.append(hit)
        if oc.outcome == "won":
            won += 1
            if oc.final_price:
                won_prices.append(oc.final_price)
            elif est.grand_total:
                won_prices.append(est.grand_total)
        elif oc.outcome == "lost":
            lost += 1
        elif oc.outcome == "pending":
            pending += 1

    lines = [f"Similar past jobs ({len(hits)} found):"]
    if won_prices:
        avg_won = sum(won_prices) / len(won_prices)
        lines.append(
            f"- Win rate: {won}/{won + lost} closed; avg won price ${avg_won:,.0f}"
        )
    elif won + lost > 0:
        lines.append(f"- Win rate: {won}/{won + lost} closed")
    for h in hits[:3]:
        price = h["final_price"] or h["grand_total"] or 0
        lines.append(f'- "{h["title"]}" → {h["outcome"]} at ${price:,.0f}')

    return "\n".join(lines), hits
