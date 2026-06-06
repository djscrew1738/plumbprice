from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(255), nullable=False, unique=True, index=True)
    base_model = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False, server_default="openai")
    training_samples = Column(Integer, nullable=True)
    eval_score = Column(Float, nullable=True)
    baseline_score = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, server_default="shadow")
    shadow_calls = Column(Integer, server_default="0", nullable=False)
    shadow_match_rate = Column(Float, nullable=True)
    openai_job_id = Column(String(255), nullable=True)
    promoted_at = Column(DateTime(timezone=True), nullable=True)
    promoted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_ml_models_status", "status"),
    )
