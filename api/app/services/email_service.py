"""Email service — generic Resend delivery helpers.

Used for transactional emails like password reset. Proposals use their own
pathway in `proposal_service.py`.
"""

from __future__ import annotations

from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger()


async def send_password_reset_email(
    recipient_email: str,
    reset_url: str,
) -> bool:
    """Send a password-reset email via Resend.

    Returns True if delivery succeeded, False if skipped (no API key) or failed.
    """
    if not settings.resend_api_key:
        logger.warning(
            "password_reset.email_skipped",
            reason="RESEND_API_KEY not configured",
            to=recipient_email,
        )
        return False

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
  <h2>Reset your PlumbPrice password</h2>
  <p>We received a request to reset the password for your PlumbPrice account.</p>
  <p>
    <a href="{reset_url}"
       style="display:inline-block;padding:12px 20px;background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold">
      Reset password
    </a>
  </p>
  <p style="color:#666;font-size:0.9em">
    Or paste this link into your browser:<br>
    <span style="word-break:break-all">{reset_url}</span>
  </p>
  <p style="color:#666;font-size:0.85em;margin-top:24px">
    This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
  </p>
</body>
</html>
"""

    try:
        import resend as _resend
        _resend.api_key = settings.resend_api_key
        response = _resend.Emails.send({
            "from": settings.email_from,
            "to": [recipient_email],
            "subject": "Reset your PlumbPrice password",
            "html": html_body,
        })
        logger.info(
            "password_reset.email_sent",
            to=recipient_email,
            resend_id=response.get("id") if isinstance(response, dict) else None,
        )
        return True
    except Exception as e:
        logger.error("password_reset.email_failed", to=recipient_email, error=str(e))
        return False
