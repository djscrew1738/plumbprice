"""Billing provider abstraction (e3): QuickBooks invoice + Stripe deposit.

When a proposal is accepted:
  - Push an invoice to QuickBooks Online.
  - Generate a Stripe payment-intent / deposit link for the customer.

Live integrations gated on QB_REFRESH_TOKEN, QB_REALM_ID, STRIPE_SECRET_KEY.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog

from . import ProviderHealth, ProviderMode

logger = structlog.get_logger()


@dataclass
class Invoice:
    invoice_id: str
    estimate_id: int
    amount: float
    deposit_amount: float
    deposit_link: str
    qb_invoice_url: Optional[str] = None
    status: str = "draft"  # draft | sent | paid | void


@dataclass
class _BillingStore:
    invoices: List[Invoice] = field(default_factory=list)


class BaseBillingProvider(ABC):
    name: str = "billing"

    @abstractmethod
    async def create_invoice(
        self, *, estimate_id: int, amount: float, deposit_pct: float = 0.5
    ) -> Invoice: ...

    @abstractmethod
    async def get_invoice(self, invoice_id: str) -> Invoice: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...


class MockBillingProvider(BaseBillingProvider):
    def __init__(self) -> None:
        self._store = _BillingStore()
        self._index: Dict[str, Invoice] = {}

    async def create_invoice(
        self, *, estimate_id: int, amount: float, deposit_pct: float = 0.5
    ) -> Invoice:
        if not (0 <= deposit_pct <= 1):
            raise ValueError("deposit_pct must be in [0, 1]")
        iid = f"inv-mock-{uuid.uuid4().hex[:10]}"
        deposit = round(amount * deposit_pct, 2)
        inv = Invoice(
            invoice_id=iid,
            estimate_id=estimate_id,
            amount=round(amount, 2),
            deposit_amount=deposit,
            deposit_link=f"https://mock.stripe.local/pay/{iid}",
            qb_invoice_url=f"https://mock.qb.local/invoice/{iid}",
            status="sent",
        )
        self._store.invoices.append(inv)
        self._index[iid] = inv
        logger.info("billing.mock.invoice_created", invoice_id=iid, amount=amount, deposit=deposit)
        return inv

    async def get_invoice(self, invoice_id: str) -> Invoice:
        if invoice_id not in self._index:
            raise KeyError(invoice_id)
        return self._index[invoice_id]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, mode=ProviderMode.MOCK, ok=True,
            detail=f"{len(self._store.invoices)} mock invoices",
        )


_provider: Optional[BaseBillingProvider] = None


def get_billing_provider() -> BaseBillingProvider:
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("STRIPE_SECRET_KEY") and os.getenv("QB_REFRESH_TOKEN"):
        # TODO(billing-live): wire QbStripeProvider when creds land.
        logger.warning("billing.live_provider_pending")
    _provider = MockBillingProvider()
    return _provider
