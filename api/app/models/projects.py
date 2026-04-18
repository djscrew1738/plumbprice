from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class JobType(str, enum.Enum):
    SERVICE = "service"
    NEW_CONSTRUCTION = "new_construction"
    COMMERCIAL = "commercial"
    REMODEL = "remodel"


class JobStatus(str, enum.Enum):
    LEAD = "lead"
    ESTIMATE_SENT = "estimate_sent"
    WON = "won"
    LOST = "lost"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False, default="service", index=True)
    status = Column(String(50), default="lead", index=True)
    customer_name = Column(String(255))
    customer_phone = Column(String(20))
    customer_email = Column(String(255))
    address = Column(Text)
    city = Column(String(100), default="Dallas")
    county = Column(String(100), default="Dallas")
    state = Column(String(10), default="TX")
    zip_code = Column(String(10))
    notes = Column(Text)
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    estimates = relationship("Estimate", back_populates="project")
    activities = relationship(
        "ProjectActivity",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectActivity(Base):
    __tablename__ = "project_activities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind = Column(String(40), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    project = relationship("Project", back_populates="activities")
    actor = relationship("User", foreign_keys=[actor_user_id])
