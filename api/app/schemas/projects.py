from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    job_type: str = Field(default="service")
    status: str = Field(default="lead")
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    address: Optional[str] = None
    city: str = Field(default="Dallas")
    county: str = Field(default="Dallas")
    state: str = Field(default="TX")
    zip_code: Optional[str] = None
    notes: Optional[str] = None


class ProjectListItem(BaseModel):
    id: int
    name: str
    job_type: str
    status: str
    customer_name: Optional[str] = None
    county: str
    city: str
    estimate_count: int = 0
    latest_estimate_total: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectListItem]
    summary: dict[str, int]
