"""Proposal Service — email delivery via Resend, PDF rendering, and public accept tokens."""

import asyncio
import base64
import html
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.estimates import Estimate, Proposal

logger = structlog.get_logger()


PUBLIC_TOKEN_TTL_DAYS = 30


def _build_estimate_html(
    estimate: Estimate,
    recipient_name: Optional[str],
    message: Optional[str],
    accept_url: Optional[str] = None,
    *,
    for_pdf: bool = False,
) -> str:
    """Build a clean HTML document from an estimate.

    When ``for_pdf`` is True, the markup includes a print-optimised stylesheet
    and omits the Accept/Decline call-to-action button (clients go through the
    web page for that).
    """
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

    cta = ""
    if accept_url and not for_pdf:
        safe_url = html.escape(accept_url, quote=True)
        cta = (
            f'<p style="margin:24px 0 8px"><a href="{safe_url}" '
            f'style="display:inline-block;background:#1a73e8;color:#fff;'
            f'padding:12px 24px;border-radius:6px;text-decoration:none;'
            f'font-weight:600">Review &amp; Accept Proposal</a></p>'
            f'<p style="font-size:0.8em;color:#666;margin-top:4px">'
            f'Or open this link: <a href="{safe_url}">{safe_url}</a></p>'
        )
    elif accept_url and for_pdf:
        safe_url = html.escape(accept_url, quote=True)
        cta = (
            f'<p style="margin:24px 0 8px;font-size:0.9em">'
            f'To review and accept this proposal online, visit: '
            f'<a href="{safe_url}">{safe_url}</a></p>'
        )

    print_styles = (
        "@page { size: letter; margin: 0.6in; }"
        "@media print { body { -webkit-print-color-adjust: exact; } }"
        if for_pdf else ""
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{print_styles}</style>
</head>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:640px;margin:0 auto;padding:24px">
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

  {cta}

  <p style="margin-top:32px;font-size:0.85em;color:#666">
    Questions? Reply to this email or call us at (817) 555-0100.<br>
    Estimate #{estimate.id} &bull; {estimate.county} County, TX
  </p>
</body>
</html>"""


def render_pdf(estimate: Estimate, *, accept_url: Optional[str] = None,
               recipient_name: Optional[str] = None,
               message: Optional[str] = None) -> bytes:
    """Render an estimate proposal as a PDF byte string.

    Uses WeasyPrint. Raises ImportError if the library is unavailable so
    callers can surface a clear error.
    """
    from weasyprint import HTML  # imported lazily to avoid import cost on boot

    html_body = _build_estimate_html(
        estimate,
        recipient_name=recipient_name,
        message=message,
        accept_url=accept_url,
        for_pdf=True,
    )
    return HTML(string=html_body).write_pdf()


async def send_proposal_email(
    db: AsyncSession,
    estimate_id: int,
    recipient_email: str,
    recipient_name: Optional[str],
    message: Optional[str],
    sent_by_user_id: Optional[int],
    organization_id: Optional[int],
) -> dict:
    """Send proposal email via Resend, attach PDF, record in proposals table."""
    result = await db.execute(
        select(Estimate).where(Estimate.id == estimate_id)
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        return {"success": False, "error": "Estimate not found"}

    public_token = secrets.token_urlsafe(32)
    token_expires_at = datetime.now(timezone.utc) + timedelta(days=PUBLIC_TOKEN_TTL_DAYS)
    accept_url = f"{settings.frontend_url.rstrip('/')}/p/{public_token}"

    html_body = _build_estimate_html(estimate, recipient_name, message, accept_url=accept_url)

    # Run WeasyPrint in a thread pool — it's synchronous and blocks ~100-500ms
    pdf_bytes: Optional[bytes] = None
    try:
        pdf_bytes = await asyncio.to_thread(
            render_pdf,
            estimate,
            accept_url=accept_url,
            recipient_name=recipient_name,
            message=message,
        )
    except Exception as e:  # pragma: no cover - environmental
        logger.warning("proposal.pdf_render_failed", estimate_id=estimate_id, error=str(e))

    resend_id: Optional[str] = None

    if settings.resend_api_key:
        try:
            import resend as _resend
            _resend.api_key = settings.resend_api_key
            payload: dict = {
                "from": settings.email_from,
                "to": [recipient_email],
                "subject": f"Your Plumbing Estimate – ${estimate.grand_total:,.0f}",
                "html": html_body,
            }
            if pdf_bytes is not None:
                payload["attachments"] = [{
                    "filename": f"estimate-{estimate.id}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode("ascii"),
                }]
            response = await asyncio.to_thread(_resend.Emails.send, payload)
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
        sent_at=datetime.now(timezone.utc),
        resend_message_id=resend_id,
        created_by=sent_by_user_id,
        organization_id=organization_id,
        public_token=public_token,
        token_expires_at=token_expires_at,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    return {
        "success": True,
        "proposal_id": proposal.id,
        "sent": settings.resend_api_key is not None,
        "recipient": recipient_email,
        "public_token": public_token,
        "accept_url": accept_url,
    }


async def send_notification_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """Best-effort notification email (used when customer accepts/declines).

    Swallows errors — the primary operation (accept/decline) must succeed.
    """
    if not settings.resend_api_key:
        logger.info("proposal.notification_skipped", reason="RESEND_API_KEY not configured", to=to_email)
        return
    try:
        import resend as _resend
        _resend.api_key = settings.resend_api_key
        _resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("proposal.notification_failed", error=str(e), to=to_email)


def proposal_status(proposal: Proposal, *, now: Optional[datetime] = None) -> str:
    """Return the public-facing status of a proposal send."""
    now = now or datetime.now(timezone.utc)
    if proposal.accepted_at is not None:
        return "accepted"
    if proposal.declined_at is not None:
        return "declined"
    exp = proposal.token_expires_at
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            return "expired"
    if proposal.opened_at is not None:
        return "opened"
    return "sent"
