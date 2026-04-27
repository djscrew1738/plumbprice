"""SMS + email comms provider abstraction (e2).

Default vendor targets: Twilio (SMS) + SendGrid (email). Trigger semantics:
- proposal_sent
- proposal_viewed
- proposal_accepted
- proposal_expiring
- schedule_set / schedule_changed
- payment_received

The mock just records what would have been sent; live providers ship when
TWILIO_AUTH_TOKEN / SENDGRID_API_KEY are configured.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Literal, Optional

import structlog

from . import ProviderHealth, ProviderMode

logger = structlog.get_logger()

TriggerKind = Literal[
    "proposal_sent",
    "proposal_viewed",
    "proposal_accepted",
    "proposal_expiring",
    "schedule_set",
    "schedule_changed",
    "payment_received",
]


@dataclass
class CommsMessage:
    channel: Literal["sms", "email"]
    to: str
    subject: str
    body: str
    trigger: TriggerKind
    suppressed: bool = False


@dataclass
class _Outbox:
    messages: List[CommsMessage] = field(default_factory=list)
    opt_outs: set = field(default_factory=set)


class BaseCommsProvider(ABC):
    name: str = "comms"

    @abstractmethod
    async def send_sms(self, *, to: str, body: str, trigger: TriggerKind) -> CommsMessage: ...

    @abstractmethod
    async def send_email(self, *, to: str, subject: str, body: str, trigger: TriggerKind) -> CommsMessage: ...

    @abstractmethod
    async def opt_out(self, address: str) -> None: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...


class MockCommsProvider(BaseCommsProvider):
    def __init__(self) -> None:
        self._box = _Outbox()

    async def send_sms(self, *, to: str, body: str, trigger: TriggerKind) -> CommsMessage:
        suppressed = to in self._box.opt_outs
        msg = CommsMessage(channel="sms", to=to, subject="", body=body, trigger=trigger, suppressed=suppressed)
        self._box.messages.append(msg)
        logger.info("comms.mock.sms", to=to, trigger=trigger, suppressed=suppressed)
        return msg

    async def send_email(self, *, to: str, subject: str, body: str, trigger: TriggerKind) -> CommsMessage:
        suppressed = to in self._box.opt_outs
        msg = CommsMessage(channel="email", to=to, subject=subject, body=body, trigger=trigger, suppressed=suppressed)
        self._box.messages.append(msg)
        logger.info("comms.mock.email", to=to, trigger=trigger, suppressed=suppressed)
        return msg

    async def opt_out(self, address: str) -> None:
        self._box.opt_outs.add(address)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, mode=ProviderMode.MOCK, ok=True,
            detail=f"{len(self._box.messages)} mock messages, {len(self._box.opt_outs)} opt-outs",
        )


_provider: Optional[BaseCommsProvider] = None


def get_comms_provider() -> BaseCommsProvider:
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("TWILIO_AUTH_TOKEN") and os.getenv("SENDGRID_API_KEY"):
        # TODO(comms-live): wire TwilioSendgridProvider when keys land.
        logger.warning("comms.live_provider_pending")
    _provider = MockCommsProvider()
    return _provider
