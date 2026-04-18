"""Proposal Service — email delivery via Resend."""

import html
from datetime import datetime, timezone
from typing import Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.estimates import Estimate, EstimateLineItem, Proposal

logger = structlog.get_logger()


def _build_estimate_html(estimate: Estimate, recipient_name: Optional[str], message: Optional[str]) -> str:
    """Build a clean HTML email from an estimate."""
    safe_name = html.escape(recipient_name) if recipient_name else None
    safe_msg = html.escape(message) if message else None

    greeting = f"Hi {safe_name}," if safe_name else "Hello,"
    custom_msg = f"<p>{safe_msg}</p>" if safe_msg else ""

    rows = ""
    for item in estimate.line_items:
        desc = html.escape(str(item.description)) if item.description else ""
        rows += (
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0'>{desc}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0;text-align:center'>{item.quantity}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0;text-align:right'>${item.total_cost:,.2f}</td>"
            f"</tr>"
        )

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:24px">
  <img src="https://app.ctlplumbingllc.com/logo.png" alt="CTL Plumbing" width="120" style="margin-bottom:24px">
  <h2 style="margin-top:0">Your Plumbing Estimate</h2>
  <p>{greeting}</p>
  {custom_msg}
  <p>Please find your estimate summary below. This estimate is valid for 30 days from the date issued.</p>

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:24px 0">
    <thead>
      <tr style="background:#f8f8f8">
        <th style="padding:8px 12px;text-align:left">Description</th>
        <th style="padding:8px 12px;text-align:center">Qty</th>
        <th style="padding:8px 12px;text-align:right">Total</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <table width="100%" style="max-width:300px;margin-left:auto">
    <tr>
      <td style="padding:4px 12px">Labor</td>
      <td style="padding:4px 12px;text-align:right">${estimate.labor_total:,.2f}</td>
    </tr>
    <tr>
      <td style="padding:4px 12px">Materials</td>
      <td style="padding:4px 12px;text-align:right">${estimate.materials_total:,.2f}</td>
    </tr>
    <tr>
      <td style="padding:4px 12px">Tax ({estimate.tax_rate*100:.2f}%)</td>
      <td style="padding:4px 12px;text-align:right">${estimate.tax_total:,.2f}</td>
    </tr>
    <tr style="font-weight:bold;font-size:1.1em;border-top:2px solid #1a1a1a">
      <td style="padding:8px 12px">TOTAL</td>
      <td style="padding:8px 12px;text-align:right">${estimate.grand_total:,.2f}</td>
    </tr>
  </table>

  <p style="margin-top:32px;font-size:0.85em;color:#666">
    Questions? Reply to this email or call us at (817) 555-0100.<br>
    Estimate #{estimate.id} &bull; {estimate.county} County, TX
  </p>
</body>
</html>"""


async def send_proposal_email(
    db: AsyncSession,
    estimate_id: int,
    recipient_email: str,
    recipient_name: Optional[str],
    message: Optional[str],
    sent_by_user_id: Optional[int],
    organization_id: Optional[int],
) -> dict:
    """Send proposal email via Resend and record in proposals table."""
    result = await db.execute(
        select(Estimate).where(Estimate.id == estimate_id)
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        return {"success": False, "error": "Estimate not found"}

    html_body = _build_estimate_html(estimate, recipient_name, message)
    resend_id: Optional[str] = None

    if settings.resend_api_key:
        try:
            import resend as _resend
            _resend.api_key = settings.resend_api_key
            response = _resend.Emails.send({
                "from": settings.email_from,
                "to": [recipient_email],
                "subject": f"Your Plumbing Estimate – ${estimate.grand_total:,.0f}",
                "html": html_body,
            })
            resend_id = response.get("id")
            logger.info("proposal.email_sent", estimate_id=estimate_id, to=recipient_email, resend_id=resend_id)
        except Exception as e:
            logger.error("proposal.email_failed", estimate_id=estimate_id, error=str(e))
            return {"success": False, "error": str(e)}
    else:
        logger.warning("proposal.email_skipped", reason="RESEND_API_KEY not configured")

    proposal = Proposal(
        estimate_id=estimate_id,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        message=message,
        sent_at=datetime.now(timezone.utc) if settings.resend_api_key else None,
        resend_message_id=resend_id,
        created_by=sent_by_user_id,
        organization_id=organization_id,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    return {
        "success": True,
        "proposal_id": proposal.id,
        "sent": settings.resend_api_key is not None,
        "recipient": recipient_email,
    }
