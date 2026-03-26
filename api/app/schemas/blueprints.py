from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BlueprintJobResponse(BaseModel):
    id: int
    filename: str
    status: str
    page_count: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class FixtureDetectionResult(BaseModel):
    fixture_type: str
    canonical_item: Optional[str]
    count: int
    confidence: float
    page_number: int


class TakeoffResult(BaseModel):
    job_id: int
    filename: str
    fixtures: list[FixtureDetectionResult]
    estimated_fixture_count: int
    suggested_assemblies: list[str]
    notes: list[str]
