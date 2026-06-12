from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from app.database import Base


class SupplierPriceAlert(Base):
    """Records when a supplier product's price changes by more than the alert threshold (E1.3)."""

    __tablename__ = "supplier_price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    canonical_item = Column(String(200), nullable=False)
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    delta_pct = Column(Float, nullable=False)
    alerted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged = Column(Boolean, server_default="false", nullable=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_price_alerts_supplier_id", "supplier_id"),
        Index("ix_price_alerts_unacknowledged", "acknowledged", "alerted_at"),
    )


class PricingRecommendation(Base):
    """Auto-generated recommendations to correct systematic estimate variance (E2.3)."""

    __tablename__ = "pricing_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    task_code = Column(String(100), nullable=False)
    recommendation_type = Column(String(50), nullable=False)  # adjust_labor_hours | adjust_material_markup | adjust_overhead
    avg_variance_pct = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    suggested_adjustment = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="pending")  # pending | approved | rejected
    source = Column(String(20), nullable=False, server_default="outcome")  # outcome | feedback
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_pricing_recs_org_status", "organization_id", "status"),
        Index("ix_pricing_recs_task_code", "task_code"),
        Index("ix_pricing_recs_source_status", "source", "status"),
    )


class PricingAdjustment(Base):
    """Admin-approved pricing corrections applied to the pricing engine (E2.4)."""

    __tablename__ = "pricing_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    adjustment_type = Column(String(50), nullable=False)  # labor_hours_multiplier | material_markup_override | overhead_adder
    target_type = Column(String(50), nullable=False)  # task_code | canonical_item | job_type
    target_key = Column(String(200), nullable=False)
    adjustment_value = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    source_recommendation_id = Column(Integer, ForeignKey("pricing_recommendations.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_pricing_adjustments_org_active", "organization_id", "is_active"),
        Index("ix_pricing_adjustments_target", "target_type", "target_key", "is_active"),
    )


class PushSubscription(Base):
    """Web Push subscription endpoint stored per user (E6.5)."""

    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)
    keys_json = Column(JSON, nullable=False)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    last_push_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_push_subscriptions_user_id", "user_id", "is_active"),
    )
