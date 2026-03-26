from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BlueprintJob(Base):
    __tablename__ = "blueprint_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=True)
    status = Column(String(50), default="uploaded")  # uploaded, processing, complete, error
    page_count = Column(Integer, nullable=True)
    processing_error = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pages = relationship("BlueprintPage", back_populates="job")


class BlueprintPage(Base):
    __tablename__ = "blueprint_pages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("blueprint_jobs.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    sheet_type = Column(String(100), nullable=True)  # plumbing, mechanical, architectural, site
    sheet_number = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    storage_path = Column(String(1000), nullable=True)
    thumbnail_path = Column(String(1000), nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("BlueprintJob", back_populates="pages")
    detections = relationship("BlueprintDetection", back_populates="page")


class BlueprintDetection(Base):
    __tablename__ = "blueprint_detections"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("blueprint_pages.id"), nullable=False)
    fixture_type = Column(String(100), nullable=False)  # toilet, lavatory, sink, water_heater
    canonical_item = Column(String(200), nullable=True)
    count = Column(Integer, default=1)
    confidence = Column(Float, default=0.0)
    bounding_box = Column(JSON, nullable=True)  # {x, y, w, h}
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("BlueprintPage", back_populates="detections")
