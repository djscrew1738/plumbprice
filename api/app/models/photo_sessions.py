from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from app.database import Base


class PhotoSession(Base):
    """Groups multiple on-site photos into a single multi-photo estimate session (E4.1)."""

    __tablename__ = "photo_sessions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    county = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, server_default="open")  # open | processing | complete | failed
    photo_count = Column(Integer, server_default="0", nullable=False)
    estimate_id = Column(Integer, ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    detection_results = Column(JSON, nullable=True)  # aggregated detections from all photos
    job_notes = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_photo_sessions_org", "organization_id"),
        Index("ix_photo_sessions_status", "status", "created_at"),
    )
