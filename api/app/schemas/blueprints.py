from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class BlueprintJobResponse(BaseModel):
    id: int
    filename: str
    status: str
    page_count: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
