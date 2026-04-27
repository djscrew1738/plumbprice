"""
External provider scaffolding for PlumbPrice 2.1.1 integrations.

Each integration (e-sign, comms, billing, calendar, permits) follows the same
pattern:

  - A `BaseProvider` defines the public contract (e.g., `send_for_signature`).
  - A `MockProvider` ships always-on, deterministic, stateful behavior so the
    rest of the app can be developed and tested end-to-end without vendor
    credentials.
  - A live provider class is added when API keys are configured (e.g.,
    `DropboxSignProvider`, `TwilioSmsProvider`, `StripeBillingProvider`).
  - A factory (`get_<X>_provider()`) reads `app.config.settings` and returns
    the live provider when configured, else the mock.
  - A health probe at `/api/v1/health/<X>` reports the active mode and
    last error (if any).

This keeps the surface area stable: routers, agents, and the worker call
the abstract interface. Flipping from mock → live is just an env var.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class ProviderMode(str, Enum):
    MOCK = "mock"
    LIVE = "live"
    DISABLED = "disabled"


@dataclass
class ProviderHealth:
    name: str
    mode: ProviderMode
    ok: bool
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode.value,
            "ok": self.ok,
            "detail": self.detail,
        }
