from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SupplierWebhook(Base):
    """Subscription for receiving supplier push updates via webhooks.

    Each supplier can have multiple webhook subscriptions for different event types.
    HMAC secrets are used to verify webhook authenticity.
    """
    __tablename__ = "supplier_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # price_change | stock_update
    secret = Column(String(255), nullable=False)  # HMAC verification key
    endpoint_url = Column(String(1000), nullable=False)  # our receiving endpoint path
    is_active = Column(Boolean, default=True, nullable=False)
    last_delivered_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier")
