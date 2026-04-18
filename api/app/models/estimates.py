from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="draft", index=True)

    # Pricing summary
    labor_total = Column(Float, default=0.0)
    materials_total = Column(Float, default=0.0)
    tax_total = Column(Float, default=0.0)
    markup_total = Column(Float, default=0.0)
    misc_total = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)

    # Confidence and context
    confidence_score = Column(Float, default=0.85)
    confidence_label = Column(String(50), default="HIGH")
    assumptions = Column(JSON, default=list)
    sources = Column(JSON, default=list)
    chat_context = Column(Text, nullable=True)

    # Location
    county = Column(String(100), default="Dallas")
    tax_rate = Column(Float, default=0.0825)

    # Preferred supplier
    preferred_supplier = Column(String(100), nullable=True)

    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    blueprint_job_id = Column(
        Integer,
        ForeignKey("blueprint_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="estimates")
    line_items = relationship("EstimateLineItem", back_populates="estimate",
                              cascade="all, delete-orphan",
                              lazy="selectin")   # avoids N+1 on estimate fetch
    versions = relationship("EstimateVersion", back_populates="estimate",
                            cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_estimates_org_status", "organization_id", "status"),
        Index("ix_estimates_org_created", "organization_id", "created_at"),
    )


class EstimateLineItem(Base):
    __tablename__ = "estimate_line_items"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    line_type = Column(String(50), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="ea")
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    supplier = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    canonical_item = Column(String(200), nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    trace_json = Column(JSON, nullable=True)

    estimate = relationship("Estimate", back_populates="line_items")

    __table_args__ = (
        Index("ix_line_items_estimate_sort_order", "estimate_id", "sort_order"),
    )


class EstimateVersion(Base):
    __tablename__ = "estimate_versions"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    estimate = relationship("Estimate", back_populates="versions")


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    resend_message_id = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Public acceptance loop
    public_token = Column(String(64), unique=True, index=True, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    decline_reason = Column(Text, nullable=True)
    client_signature = Column(String(200), nullable=True)
    client_ip = Column(String(45), nullable=True)
    client_user_agent = Column(String(500), nullable=True)

    estimate = relationship("Estimate")
