from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SupplierResponse(BaseModel):
    id: int
    name: str
    slug: str
    type: str
    website: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class SupplierProductUpdate(BaseModel):
    cost: float = Field(..., gt=0)
    notes: Optional[str] = None


class SupplierCompareRequest(BaseModel):
    canonical_items: list[str]
    county: str = "Dallas"


class SupplierCompareItem(BaseModel):
    canonical_item: str
    suppliers: dict[str, Optional[dict]]  # slug -> {sku, name, cost, confidence}


class SupplierCompareResponse(BaseModel):
    items: list[SupplierCompareItem]
    best_value_supplier: Optional[str]
    total_by_supplier: dict[str, float]


class BulkPriceUpload(BaseModel):
    products: list[dict]  # [{canonical_item, sku, name, cost}]
