"""Shared rate limiter singleton.

Lives outside app.main to avoid circular imports — routers can `from
app.core.limiter import limiter` without re-importing the FastAPI app.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
