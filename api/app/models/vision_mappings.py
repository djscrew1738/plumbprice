"""
Phase 3.5 — Vision-item to task-code overrides.

Lets non-engineers edit the photo→labor mapping live, without redeploying.
The static `_ITEM_TO_TASK` dictionary in services/photo_quote.py is the
fallback; this table overrides any entries by `item_type`.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class VisionItemMapping(Base):
    __tablename__ = "vision_item_mappings"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(80), unique=True, nullable=False, index=True)
    default_task_code = Column(String(120), nullable=False)
    problem_task_code = Column(String(120), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    note = Column(String(500), nullable=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
