"""Public-agent audit log + anomaly review (Track D5).

One row per /public-agent/quote request. anomaly_score in [0, 1] +
anomaly_flags (list of short codes) let admins triage abuse, prompt
injection, and pricing-edge cases without grepping logs.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Index, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class PublicAgentAudit(Base):
    __tablename__ = "public_agent_audits"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    client_ip = Column(String(45), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)

    # Request
    message = Column(Text, nullable=False)
    county = Column(String(100), nullable=True)
    customer_email = Column(String(255), nullable=True)

    # Outcome
    status = Column(String(32), nullable=False, default="ok", index=True)  # ok / too_large / out_of_scope / uncertain
    task_code = Column(String(64), nullable=True)
    grand_total = Column(Float, nullable=True)
    lead_id = Column(Integer, nullable=True)

    # Anomaly review
    anomaly_score = Column(Float, nullable=False, default=0.0, index=True)
    anomaly_flags = Column(JSON, nullable=True)  # list[str]
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_pa_audits_score_created", "anomaly_score", "created_at"),
        Index("ix_pa_audits_unreviewed", "reviewed_at", "anomaly_score"),
    )
