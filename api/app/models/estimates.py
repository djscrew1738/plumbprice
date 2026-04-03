from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False, index=True)  # service, construction, commercial
    status = Column(String(50), default="draft", index=True)  # draft, sent, accepted, rejected, expired

    # Pricing summary
    labor_total = Column(Float, default=0.0)
    materials_total = Column(Float, default=0.0)
    tax_total = Column(Float, default=0.0)
    markup_total = Column(Float, default=0.0)
    misc_total = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)

    # Confidence and context
    confidence_score = Column(Float, default=0.85)  # 0.0-1.0
    confidence_label = Column(String(50), default="HIGH")  # HIGH, MEDIUM, LOW
    assumptions = Column(JSON, default=list)
    sources = Column(JSON, default=list)
    chat_context = Column(Text, nullable=True)

    # Location
    county = Column(String(100), default="Dallas")
    tax_rate = Column(Float, default=0.0825)

    # Preferred supplier
    preferred_supplier = Column(String(100), nullable=True)

    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="estimates")
    line_items = relationship("EstimateLineItem", back_populates="estimate", cascade="all, delete-orphan")
    versions = relationship("EstimateVersion", back_populates="estimate", cascade="all, delete-orphan")


class EstimateLineItem(Base):
    __tablename__ = "estimate_line_items"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    line_type = Column(String(50), nullable=False)  # labor, material, tax, markup, misc
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="ea")
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    supplier = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True)
    canonical_item = Column(String(200), nullable=True)
    sort_order = Column(Integer, default=0)
    # Full pricing trace - every dollar traceable
    trace_json = Column(JSON, nullable=True)

    estimate = relationship("Estimate", back_populates="line_items")


class EstimateVersion(Base):
    __tablename__ = "estimate_versions"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    estimate = relationship("Estimate", back_populates="versions")
