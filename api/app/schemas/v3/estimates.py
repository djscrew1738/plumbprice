from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any
from datetime import datetime


class EstimateResponseV3(BaseModel):
    id: int
    title: str
    job_type: str
    status: str
    labor_total: float
    materials_total: float
    tax_total: float
    markup_total: float
    misc_total: float
    subtotal: float
    grand_total: float
    confidence_score: float
    confidence_label: str
    assumptions: list[str]
    county: str
    tax_rate: float
    preferred_supplier: Optional[str]
    line_items: list[dict]
    blueprint_job_id: Optional[int] = None
    blueprint_room_count: Optional[int] = None
    blueprint_pipe_run_ft: Optional[float] = None
    market_adjustment_applied: float = 1.0
    confidence_components: dict = {}
    agent_trace: dict = {}
    created_at: datetime

    variant_group_id: Optional[str] = None
    variant_label: Optional[str] = None
    branch_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EstimateVersionItem(BaseModel):
    """A single version snapshot in the estimate history."""
    id: int
    version_number: int
    change_summary: Optional[str] = None
    created_at: datetime
    created_by: Optional[int] = None


class EstimateVersionDiff(BaseModel):
    """Diff between two estimate versions."""
    from_version: int
    to_version: int
    from_total: float
    to_total: float
    total_delta: float
    added_line_items: list[dict] = []
    removed_line_items: list[dict] = []
    modified_line_items: list[dict] = []


class BranchEstimateRequest(BaseModel):
    """Request to fork an estimate into a new branch."""
    title: Optional[str] = None
    notes: Optional[str] = None
