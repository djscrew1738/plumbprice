from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class MarketAdjustmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    factor: float = Field(..., gt=0.0)
    category: str = Field(..., pattern=r"^(commodity|seasonal|demand|fuel)$")
    applies_to: list[str] = Field(default_factory=lambda: ["materials"])
    counties: Optional[list[str]] = None
    effective_from: datetime
    effective_until: datetime
    source: str = "admin"


class MarketAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    factor: float
    category: str
    applies_to: list[str]
    counties: Optional[list[str]]
    effective_from: datetime
    effective_until: datetime
    source: str
    is_active: bool
    created_at: datetime


class MarketAdjustmentPreviewRequest(BaseModel):
    county: str = "Dallas"
    base_labor: float = 500.0
    base_materials: float = 800.0
    base_markup: float = 200.0
    base_misc: float = 50.0
    base_trip: float = 115.0
    tax_rate: float = 0.0825
