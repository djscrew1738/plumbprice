from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WebhookEvent(BaseModel):
    type: str = Field(..., pattern=r"^(price_change|stock_update)$")
    sku: str
    supplier: str
    canonical_item: Optional[str] = None
    new_cost: Optional[float] = None
    old_cost: Optional[float] = None
    in_stock: Optional[bool] = None
    timestamp: Optional[datetime] = None


class SupplierWebhookCreate(BaseModel):
    event_type: str = Field(..., pattern=r"^(price_change|stock_update)$")
    endpoint_url: str = Field(..., max_length=1000)
    is_active: bool = True


class SupplierWebhookResponse(BaseModel):
    id: int
    supplier_id: int
    event_type: str
    endpoint_url: str
    is_active: bool
    last_delivered_at: Optional[datetime]
    failure_count: int
    created_at: datetime
