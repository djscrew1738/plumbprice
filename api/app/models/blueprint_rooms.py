from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BlueprintRoom(Base):
    """A room detected within a blueprint page by the v3 vision pipeline.

    Provides spatial context for the estimator — e.g. "Master Bath" with area 120 sqft.
    """
    __tablename__ = "blueprint_rooms"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_job_id = Column(Integer, ForeignKey("blueprint_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    room_type = Column(String(50), nullable=False)  # bathroom | kitchen | utility | bedroom | garage | other
    room_name = Column(String(100), nullable=True)  # e.g. "Master Bath"
    bounding_box = Column(JSON, nullable=True)  # {x, y, w, h}
    area_sqft = Column(Float, nullable=True)
    fixture_count = Column(Integer, nullable=True)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("BlueprintJob", back_populates="rooms")
