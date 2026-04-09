from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class LineItemCreate(BaseModel):
    line_type: str
    description: str
    quantity: float = 1.0
    unit: str = "ea"
    unit_cost: float
    supplier: Optional[str] = None
    sku: Optional[str] = None
    canonical_item: Optional[str] = None


class ServiceEstimateRequest(BaseModel):
    task_code: str = Field(..., description="Labor template code, e.g. TOILET_REPLACE_STANDARD")
    assembly_code: Optional[str] = None
    access_type: str = Field(default="first_floor", description="first_floor, second_floor, attic, crawlspace, slab")
    urgency: str = Field(default="standard", description="standard, same_day, emergency")
    county: str = Field(default="Dallas")
    city: Optional[str] = Field(default=None, description="DFW city name for zone premium (e.g. 'highland park')")
    include_trip_charge: bool = Field(default=True, description="Include per-visit service call fee")
    preferred_supplier: Optional[str] = None
    project_id: Optional[int] = None
    notes: Optional[str] = None


class ConstructionEstimateRequest(BaseModel):
    bath_groups: int = Field(default=1, ge=1, le=20)
    fixture_count: int = Field(default=5, ge=1, le=100)
    underground_lf: float = Field(default=0.0, ge=0)
    has_commercial: bool = False
    county: str = Field(default="Dallas")
    preferred_supplier: Optional[str] = None
    project_id: Optional[int] = None


class EstimateResponse(BaseModel):
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
    created_at: datetime

    class Config:
        from_attributes = True


class EstimateListItem(BaseModel):
    id: int
    title: str
    job_type: str
    status: str
    grand_total: float
    confidence_label: str
    county: str
    created_at: datetime

    class Config:
        from_attributes = True


class EstimateVersionItem(BaseModel):
    id: int
    version_number: int
    snapshot: dict
    change_summary: Optional[str] = None
    created_at: datetime


class EstimateVersionListResponse(BaseModel):
    estimate_id: int
    versions: list[EstimateVersionItem]
