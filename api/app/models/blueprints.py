from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BlueprintJob(Base):
    __tablename__ = "blueprint_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=True)
    storage_path = Column(String(1000), nullable=True)
    status = Column(String(50), default="uploaded")  # uploaded, processing, complete, error
    page_count = Column(Integer, nullable=True)
    processing_error = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Privacy / retention
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    retention_until = Column(DateTime(timezone=True), nullable=True, index=True)

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
    # Phase 2 enrichment: native PDF text + detected drawing scale
    ocr_text = Column(Text, nullable=True)
    scale_text = Column(String(100), nullable=True)  # e.g. "1/4\" = 1'-0\""
    # Phase 2.5 — pixel calibration. `px_per_ft` = pixels per real-world foot
    # for this rendered page. Either parsed from `scale_text` + render DPI
    # (source="text"), or set by the user clicking two points on a known
    # dimension (source="manual"). Used by takeoff to convert pixel runs
    # into linear feet for piping/ductwork.
    px_per_ft = Column(Float, nullable=True)
    scale_calibrated = Column(Boolean, default=False, nullable=False)
    scale_source = Column(String(20), nullable=True)  # text | manual | auto
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("BlueprintJob", back_populates="pages")
    detections = relationship("BlueprintDetection", back_populates="page")

    __table_args__ = (
        UniqueConstraint("job_id", "page_number", name="uq_blueprint_pages_job_page"),
    )


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
    needs_review = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    page = relationship("BlueprintPage", back_populates="detections")
    feedback = relationship("BlueprintDetectionFeedback", back_populates="detection", cascade="all, delete-orphan")


class BlueprintDetectionFeedback(Base):
    """User feedback on a vision detection (correct / wrong / edited).

    Powers the side-by-side review UI and serves as the training-data substrate
    for future classifier improvements.
    """
    __tablename__ = "blueprint_detection_feedback"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("blueprint_detections.id", ondelete="CASCADE"), nullable=False)
    verdict = Column(String(20), nullable=False)  # "correct" | "wrong" | "edited"
    corrected_fixture_type = Column(String(100), nullable=True)
    corrected_count = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    detection = relationship("BlueprintDetection", back_populates="feedback")
