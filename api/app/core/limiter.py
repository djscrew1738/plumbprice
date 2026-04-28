"""Shared rate limiter singleton.

Lives outside app.main to avoid circular imports — routers can `from
app.core.limiter import limiter` without re-importing the FastAPI app.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Disable per-IP slowapi limits during tests so suites that exercise auth
# flows back-to-back from the same loopback IP don't bleed into each other.
# Per-account brute-force counters in app.core.rate_limit still apply.
_env = settings.environment.lower()
_enabled = _env not in {"test", "testing"}

# print(f"DEBUG: limiter environment={_env}, enabled={_enabled}")

limiter = Limiter(key_func=get_remote_address, enabled=_enabled)
