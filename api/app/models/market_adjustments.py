from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MarketAdjustment(Base):
    """Dynamic pricing adjustment applied to estimates based on market conditions.

    Examples: copper price surge (+3.2%), seasonal demand (+5%), fuel surcharge (+1.5%).
    Adjustments are transparent — the UI shows each factor and its rationale.
    """
    __tablename__ = "market_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Copper Surge Q2 2026"
    factor = Column(Float, nullable=False)  # 1.032 = +3.2%
    category = Column(String(50), nullable=False)  # commodity | seasonal | demand | fuel
    applies_to = Column(JSON, nullable=False, default=list)  # ["materials"], ["labor", "materials"], etc.
    counties = Column(JSON, nullable=True)  # NULL = all counties (list of strings)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_until = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), default="admin")  # admin | ferguson_webhook | manual
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_market_adjustments_active_dates", "is_active", "effective_from", "effective_until"),
        Index("ix_market_adjustments_category", "category", "is_active"),
    )
