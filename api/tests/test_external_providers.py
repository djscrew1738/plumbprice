"""Tests for vendor-blocked external provider scaffolds (e1-e5)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.external import ProviderMode
from app.services.external.billing import get_billing_provider, MockBillingProvider
from app.services.external.calendar import get_calendar_provider, MockCalendarProvider
from app.services.external.comms import get_comms_provider, MockCommsProvider
from app.services.external.esign import get_esign_provider, MockEsignProvider
from app.services.external.permits import get_permits_provider, MockPermitsProvider


@pytest.mark.asyncio
async def test_esign_mock_create_and_status():
    p = MockEsignProvider()
    req = await p.create_request(
        proposal_token="tok-abc", signer_email="cory@ctlplumbing.com", signer_name="Cory N",
    )
    assert req.request_id.startswith("mock-")
    assert req.status == "awaiting_signature"
    again = await p.get_status(req.request_id)
    assert again.request_id == req.request_id
    h = await p.health()
    assert h.ok and h.mode == ProviderMode.MOCK


@pytest.mark.asyncio
async def test_comms_mock_send_and_optout():
    p = MockCommsProvider()
    msg = await p.send_sms(to="+15551234567", body="quote ready", trigger="proposal_sent")
    assert msg.suppressed is False
    await p.opt_out("+15551234567")
    msg2 = await p.send_sms(to="+15551234567", body="follow up", trigger="proposal_expiring")
    assert msg2.suppressed is True
    h = await p.health()
    assert h.ok


@pytest.mark.asyncio
async def test_billing_mock_invoice():
    p = MockBillingProvider()
    inv = await p.create_invoice(estimate_id=99, amount=1500.00, deposit_pct=0.5)
    assert inv.amount == 1500.00
    assert inv.deposit_amount == 750.00
    assert inv.deposit_link.startswith("https://")
    with pytest.raises(ValueError):
        await p.create_invoice(estimate_id=1, amount=100, deposit_pct=1.5)


@pytest.mark.asyncio
async def test_calendar_mock_tentative_then_confirm():
    p = MockCalendarProvider()
    when = datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc)
    evt = await p.create_tentative(estimate_id=7, starts_at=when, duration_minutes=90)
    assert evt.status == "tentative"
    confirmed = await p.confirm(evt.event_id)
    assert confirmed.status == "confirmed"
    cancelled = await p.cancel(evt.event_id)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_permits_mock_dallas_vs_plano():
    p = MockPermitsProvider()
    dallas = await p.submit(city="Dallas", permit_type="repipe", estimate_id=1)
    assert dallas.status == "applied"
    plano = await p.submit(city="Plano", permit_type="water_heater", estimate_id=2)
    assert plano.status == "manual_tracking"
    assert plano.note and "manual" in plano.note.lower()


@pytest.mark.asyncio
async def test_factories_return_mock_when_no_keys(monkeypatch):
    """Without env keys, factories should hand back mock implementations."""
    for env_var in (
        "DROPBOX_SIGN_API_KEY", "TWILIO_AUTH_TOKEN", "SENDGRID_API_KEY",
        "STRIPE_SECRET_KEY", "QB_REFRESH_TOKEN",
        "GOOGLE_CALENDAR_OAUTH_REFRESH_TOKEN", "ACCELA_API_KEY",
    ):
        monkeypatch.delenv(env_var, raising=False)

    # Reset module-level singletons so the factory re-evaluates env.
    import app.services.external.esign as esign_mod
    import app.services.external.comms as comms_mod
    import app.services.external.billing as billing_mod
    import app.services.external.calendar as calendar_mod
    import app.services.external.permits as permits_mod
    for m in (esign_mod, comms_mod, billing_mod, calendar_mod, permits_mod):
        m._provider = None  # type: ignore[attr-defined]

    assert isinstance(get_esign_provider(), MockEsignProvider)
    assert isinstance(get_comms_provider(), MockCommsProvider)
    assert isinstance(get_billing_provider(), MockBillingProvider)
    assert isinstance(get_calendar_provider(), MockCalendarProvider)
    assert isinstance(get_permits_provider(), MockPermitsProvider)
