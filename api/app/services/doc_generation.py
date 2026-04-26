"""Doc generation: cover letter, scope of work, change order narratives.

LLM-first with deterministic static fallbacks so the endpoint never 500s
when Ollama / cloud is offline. All generators take an Estimate ORM
instance with line_items eager-loaded.
"""
from __future__ import annotations

from typing import Optional

from app.models.estimates import Estimate
from app.services.llm_service import llm_service

COMPANY_NAME = "CTL Plumbing"
OWNER_NAME = "Cory Nichols"

_COVER_SYSTEM = (
    f"You are writing a brief, professional proposal cover letter on behalf of "
    f"{OWNER_NAME} of {COMPANY_NAME}, a licensed plumbing contractor in DFW, Texas. "
    "Tone: confident, plain-spoken contractor — not corporate. 3-5 short sentences. "
    "Mention the customer is getting a written, code-compliant scope and a fixed price. "
    "Do not invent specifics that aren't in the estimate. Sign off as the company name."
)

_SOW_SYSTEM = (
    "You are writing a clear scope-of-work narrative for a residential plumbing job in Texas. "
    "Use bullets grouped under short headers (Work to be performed, Materials, Code & inspection, "
    "Exclusions). Be specific about what the customer is buying. Reference Texas plumbing code "
    "(IPC adopted statewide) when relevant. No fluff."
)

_CO_SYSTEM = (
    "You are drafting a plumbing change-order narrative. State plainly what changed, "
    "why, and what the customer is approving (added or removed scope, dollar delta). "
    "Keep it 4-6 sentences. Tone: matter-of-fact contractor."
)


def _line_summary(est: Estimate, *, limit: int = 25) -> str:
    items = sorted(est.line_items or [], key=lambda li: li.sort_order or 0)[:limit]
    if not items:
        return "(no line items recorded)"
    parts = []
    for li in items:
        qty = li.quantity or 1
        parts.append(f"- {li.description} (qty {qty:g}, ${li.total_cost or 0:,.0f})")
    if len(est.line_items or []) > limit:
        parts.append(f"- … plus {len(est.line_items) - limit} more line(s)")
    return "\n".join(parts)


def _facts(est: Estimate) -> str:
    return (
        f"Estimate title: {est.title}\n"
        f"Job type: {est.job_type}\n"
        f"County: {est.county or 'Dallas'}, TX\n"
        f"Grand total: ${est.grand_total or 0:,.2f}\n"
        f"  Labor: ${est.labor_total or 0:,.2f}\n"
        f"  Materials: ${est.materials_total or 0:,.2f}\n"
        f"  Tax: ${est.tax_total or 0:,.2f}\n"
        f"Line items:\n{_line_summary(est)}"
    )


# ---------- Cover letter ----------

async def generate_cover_letter(est: Estimate, customer_name: Optional[str] = None) -> dict:
    greeting = f"Dear {customer_name}," if customer_name else "Hello,"
    user = (
        f"{greeting}\n\n"
        f"Draft a cover letter for this estimate.\n\n{_facts(est)}\n\n"
        "Output only the letter body, no subject line, no signature block."
    )
    text = await llm_service.complete(_COVER_SYSTEM, user, max_tokens=350, temperature=0.5)
    if text:
        return {"text": text.strip(), "source": "llm"}
    return {"text": _static_cover(est, customer_name), "source": "static"}


def _static_cover(est: Estimate, customer_name: Optional[str]) -> str:
    greeting = f"Dear {customer_name}," if customer_name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"Thanks for reaching out to {COMPANY_NAME}. Attached is your fixed-price proposal "
        f"for {est.title} in {est.county or 'Dallas'} County, TX, totaling "
        f"${est.grand_total or 0:,.2f}. Every line is broken out so you can see exactly "
        f"what the work and materials cost — no surprises.\n\n"
        f"Pricing is good for 30 days. Reply or call when you're ready and we'll "
        f"get on the schedule.\n\n"
        f"— {COMPANY_NAME}"
    )


# ---------- Scope of work ----------

async def generate_scope_of_work(est: Estimate) -> dict:
    user = (
        f"Write the scope-of-work narrative for this estimate.\n\n{_facts(est)}\n\n"
        "Output markdown with headers: ### Work to be performed, ### Materials, "
        "### Code & inspection, ### Exclusions."
    )
    text = await llm_service.complete(_SOW_SYSTEM, user, max_tokens=600, temperature=0.3)
    if text:
        return {"text": text.strip(), "source": "llm"}
    return {"text": _static_sow(est), "source": "static"}


def _static_sow(est: Estimate) -> str:
    items = sorted(est.line_items or [], key=lambda li: li.sort_order or 0)
    work_lines = "\n".join(f"- {li.description}" for li in items if (li.line_type or "") == "labor") or "- See line items in attached estimate."
    mat_lines = "\n".join(f"- {li.description}" for li in items if (li.line_type or "") == "material") or "- All materials per attached estimate."
    return (
        f"### Work to be performed\n{work_lines}\n\n"
        f"### Materials\n{mat_lines}\n\n"
        f"### Code & inspection\n"
        f"- All work performed to the Texas-adopted International Plumbing Code (IPC).\n"
        f"- Permits and inspections pulled where required by {est.county or 'Dallas'} County / municipality.\n"
        f"- Pressure / leak testing performed per code prior to closing walls.\n\n"
        f"### Exclusions\n"
        f"- Wall, ceiling, or finish patching unless explicitly listed.\n"
        f"- Repairs to pre-existing code violations discovered during the work (priced as change order).\n"
        f"- Items not listed on the attached estimate."
    )


# ---------- Change order ----------

async def generate_change_order(
    original: Estimate,
    revised: Estimate,
    reason: Optional[str] = None,
) -> dict:
    delta = (revised.grand_total or 0) - (original.grand_total or 0)
    user = (
        f"Original estimate total: ${original.grand_total or 0:,.2f}\n"
        f"Revised estimate total: ${revised.grand_total or 0:,.2f}\n"
        f"Delta: ${delta:+,.2f}\n"
        f"Job: {original.title} — {original.county or 'Dallas'} County, TX\n"
        f"Reason given: {reason or '(not specified)'}\n\n"
        f"Original line items:\n{_line_summary(original, limit=15)}\n\n"
        f"Revised line items:\n{_line_summary(revised, limit=15)}\n\n"
        "Draft the change-order narrative. Output prose only."
    )
    text = await llm_service.complete(_CO_SYSTEM, user, max_tokens=350, temperature=0.3)
    if text:
        return {"text": text.strip(), "delta": round(delta, 2), "source": "llm"}
    return {"text": _static_co(original, revised, reason, delta), "delta": round(delta, 2), "source": "static"}


def _static_co(original: Estimate, revised: Estimate, reason: Optional[str], delta: float) -> str:
    direction = "increase" if delta > 0 else ("decrease" if delta < 0 else "no-cost change")
    return (
        f"Change order for {original.title} ({original.county or 'Dallas'} County, TX). "
        f"Original price: ${original.grand_total or 0:,.2f}. Revised price: "
        f"${revised.grand_total or 0:,.2f} — a ${abs(delta):,.2f} {direction}. "
        f"Reason: {reason or 'Scope adjusted at customer request or due to discovered conditions.'} "
        f"By signing below, the customer authorizes the revised scope and price. "
        f"All other terms of the original proposal remain in force."
    )
