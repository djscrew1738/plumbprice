"""Job cost actuals — track what the job *actually* cost vs. what was estimated.

Closes the feedback loop between estimating and field operations:
* Estimator quotes labor + materials.
* Crew records actual hours and material spend (this table).
* `c5-jobcost-recon` exposes variance per estimate / task code, so
  `winrate_service` and the LLM can use *real* outcomes instead of
  optimistic budgeting.
"""
from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class EstimateActuals(Base):
    """One row per estimate. Updated as the job progresses; final on close."""

    __tablename__ = "estimate_actuals"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(
        Integer,
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=True, index=True
    )

    actual_labor_hours = Column(Float, nullable=True)
    actual_labor_cost = Column(Float, nullable=True)
    actual_materials_cost = Column(Float, nullable=True)
    actual_subcontractor_cost = Column(Float, nullable=True)
    actual_other_cost = Column(Float, nullable=True)
    actual_revenue = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    estimate = relationship("Estimate")

    __table_args__ = (
        Index("ix_actuals_org_closed", "organization_id", "closed_at"),
    )


class JobCostEntry(Base):
    """Optional fine-grained line entries (timecards, receipts) feeding actuals.

    Not every shop will use this — the rollup on `EstimateActuals` is the
    source of truth for variance reporting. This table is here so apps that
    push timecards or material receipts can append entries without re-summing
    on the client.
    """

    __tablename__ = "job_cost_entries"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(
        Integer,
        ForeignKey("estimates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=True, index=True
    )

    # 'labor' | 'material' | 'subcontractor' | 'other'
    kind = Column(String(20), nullable=False, index=True)
    task_code = Column(String(80), nullable=True, index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="ea")
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
