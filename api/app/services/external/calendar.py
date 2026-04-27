"""Calendar provider abstraction (e4): Google Calendar tentative-then-confirmed flow.

Proposal accepted → tentative slot. Tech accepts → confirmed.
Live: GOOGLE_CALENDAR_OAUTH_REFRESH_TOKEN.
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


@dataclass
class CalendarEvent:
    event_id: str
    estimate_id: int
    starts_at: datetime
    duration_minutes: int
    status: Literal["tentative", "confirmed", "cancelled"] = "tentative"
    tech_email: Optional[str] = None


class BaseCalendarProvider(ABC):
    name: str = "calendar"

    @abstractmethod
    async def create_tentative(
        self, *, estimate_id: int, starts_at: datetime, duration_minutes: int = 120,
        tech_email: Optional[str] = None,
    ) -> CalendarEvent: ...

    @abstractmethod
    async def confirm(self, event_id: str) -> CalendarEvent: ...

    @abstractmethod
    async def cancel(self, event_id: str) -> CalendarEvent: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...


class MockCalendarProvider(BaseCalendarProvider):
    def __init__(self) -> None:
        self._events: Dict[str, CalendarEvent] = {}

    async def create_tentative(
        self, *, estimate_id: int, starts_at: datetime, duration_minutes: int = 120,
        tech_email: Optional[str] = None,
    ) -> CalendarEvent:
        eid = f"evt-mock-{uuid.uuid4().hex[:10]}"
        evt = CalendarEvent(
            event_id=eid, estimate_id=estimate_id, starts_at=starts_at,
            duration_minutes=duration_minutes, status="tentative",
            tech_email=tech_email,
        )
        self._events[eid] = evt
        return evt

    async def confirm(self, event_id: str) -> CalendarEvent:
        if event_id not in self._events:
            raise KeyError(event_id)
        self._events[event_id].status = "confirmed"
        return self._events[event_id]

    async def cancel(self, event_id: str) -> CalendarEvent:
        if event_id not in self._events:
            raise KeyError(event_id)
        self._events[event_id].status = "cancelled"
        return self._events[event_id]

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name, mode=ProviderMode.MOCK, ok=True,
            detail=f"{len(self._events)} mock events",
        )


_provider: Optional[BaseCalendarProvider] = None


def get_calendar_provider() -> BaseCalendarProvider:
    global _provider
    if _provider is not None:
        return _provider
    if os.getenv("GOOGLE_CALENDAR_OAUTH_REFRESH_TOKEN"):
        logger.warning("calendar.live_provider_pending")
    _provider = MockCalendarProvider()
    return _provider
