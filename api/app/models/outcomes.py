from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class EstimateOutcome(Base):
    __tablename__ = "estimate_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, unique=True, index=True)
    outcome = Column(String(20), nullable=False)  # won | lost | pending | no_bid
    final_price = Column(Float, nullable=True)    # actual price charged / competitor price
    notes = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    # v4.1 — actual cost capture (E2.1)
    actual_materials_cost = Column(Float, nullable=True)
    actual_labor_hours = Column(Float, nullable=True)
    actual_labor_cost = Column(Float, nullable=True)
    actual_total = Column(Float, nullable=True)
    variance_pct = Column(Float, nullable=True)  # (actual_total - estimated_total) / estimated_total * 100
    closed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    estimate = relationship("Estimate")

    __table_args__ = (
        Index("ix_outcomes_org_outcome", "organization_id", "outcome"),
    )
