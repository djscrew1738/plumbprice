"""Permits provider abstraction (e5): DFW-area city APIs.

Coverage roadmap:
  - Dallas       — Accela API (key-gated)
  - Fort Worth   — Accela API
  - Plano        — eTRAKiT (no public API; track manually with reminders)
  - Frisco       — eTRAKiT (manual)

Mock returns deterministic permit numbers and a fake portal URL so the
estimator can show a "permit pending" badge end-to-end without keys.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

import structlog

from . import ProviderHealth, ProviderMode

logger = structlog.get_logger()

PermitStatus = Literal["draft", "applied", "approved", "issued", "rejected", "manual_tracking"]
City = Literal["Dallas", "Fort Worth", "Plano", "Frisco"]


@dataclass
class Permit:
    permit_id: str
    city: City
    permit_type: str
    estimate_id: int
    status: PermitStatus
    portal_url: str
    applied_at: datetime
    note: Optional[str] = None


class BasePermitsProvider(ABC):
    name: str = "permits"

    @abstractmethod
    async def submit(
        self, *, city: City, permit_type: str, estimate_id: int, note: Optional[str] = None
    ) -> Permit: ...

    @abstractmethod
    async def get_status(self, permit_id: str) -> Permit: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...


class MockPermitsProvider(BasePermitsProvider):
    """Deterministic mock — Plano/Frisco return manual_tracking, others 'applied'."""

    _MANUAL_CITIES: set = {"Plano", "Frisco"}

    def __init__(self) -> None:
        self._store: Dict[str, Permit] = {}

    async def submit(
        self, *, city: City, permit_type: str, estimate_id: int, note: Optional[str] = None
    ) -> Permit:
        pid = f"prm-mock-{uuid.uuid4().hex[:10]}"
        manual = city in self._MANUAL_CITIES
        permit = Permit(
            permit_id=pid,
            city=city,
            permit_type=permit_type,
            estimate_id=estimate_id,
            status="manual_tracking" if manual else "applied",
            portal_url=f"https://mock.permits.local/{city.lower().replace(' ', '_')}/{pid}",
            applied_at=datetime.now(timezone.utc),
            note=note or ("Reminder set — track manually." if manual else None),
        )
        self._store[pid] = permit
        return permit

    async def get_status(self, permit_id: str) -> Permit:
        if permit_id not in self._store:
            raise KeyError(permit_id)
        return self._store[permit_id]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, mode=ProviderMode.MOCK, ok=True,
            detail=f"{len(self._store)} mock permits — Plano/Frisco manual",
        )


_provider: Optional[BasePermitsProvider] = None


def get_permits_provider() -> BasePermitsProvider:
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("ACCELA_API_KEY"):
        logger.warning("permits.live_provider_pending")
    _provider = MockPermitsProvider()
    return _provider
