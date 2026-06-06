from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BlueprintPipeRun(Base):
    """A detected pipe run (linear segment) within a blueprint page.

    Enables automated linear takeoff for piping estimates in v3.
    """
    __tablename__ = "blueprint_pipe_runs"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_job_id = Column(Integer, ForeignKey("blueprint_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    pipe_type = Column(String(50), nullable=False)  # copper_3_4 | pvc_4 | pex_1 | etc.
    length_ft = Column(Float, nullable=False)
    start_point = Column(JSON, nullable=True)  # {x, y}
    end_point = Column(JSON, nullable=True)  # {x, y}
    bounding_box = Column(JSON, nullable=True)  # {x, y, w, h}
    confidence = Column(Float, default=0.0)
    # v4.1 columns: fixture connectivity and material tracking
    from_fixture = Column(String(100), nullable=True)
    to_fixture = Column(String(100), nullable=True)
    material_type = Column(String(50), nullable=True)
    routing_json = Column(JSON, nullable=True)
    needs_review = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("BlueprintJob", back_populates="pipe_runs")
