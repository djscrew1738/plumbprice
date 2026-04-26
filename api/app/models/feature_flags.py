"""Feature flags — simple key/bool/description table.

Single-tenant, so we don't bother with per-user overrides yet. The admin UI
toggles enabled, the frontend reads the bag at boot via /api/v1/flags.
"""
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    key = Column(String(80), primary_key=True)
    enabled = Column(Boolean, nullable=False, server_default="false")
    description = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
