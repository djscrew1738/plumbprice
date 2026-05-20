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

    model_config = ConfigDict(from_attributes=True)
