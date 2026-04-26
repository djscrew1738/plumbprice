"""
Phase 3.5 — Photo model.

Persists field-tech photos used by the quick-quote workflow so they can be
attached to a project and referenced from an estimate.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    storage_bucket = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_type = Column(String(80), nullable=True)
    size_bytes = Column(Integer, nullable=True)

    note = Column(String(1000), nullable=True)
    county = Column(String(100), nullable=True)
    urgency = Column(String(40), nullable=True)
    access = Column(String(40), nullable=True)

    vision = Column(JSON, nullable=True)   # raw vision_service.describe_photo output
    quote = Column(JSON, nullable=True)    # quick-quote totals + lines snapshot

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
