from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)


class SupplierProductUpdate(BaseModel):
    cost: float = Field(..., gt=0)
    notes: Optional[str] = None
    in_stock: Optional[bool] = None
    lead_time: Optional[str] = None
    manufacturer: Optional[str] = None
    msrp: Optional[float] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    tags: Optional[list[str]] = None


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


class SupplierProductResponse(BaseModel):
    id: int
    supplier_id: int
    canonical_item: str
    sku: Optional[str]
    name: str
    description: Optional[str]
    brand: Optional[str]
    unit: str
    cost: float
    list_price: Optional[float]
    msrp: Optional[float]
    manufacturer: Optional[str]
    in_stock: bool
    lead_time: Optional[str]
    category: Optional[str]
    sub_category: Optional[str]
    tags: Optional[list[str]]
    confidence_score: float
    is_active: bool
    last_verified: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BulkPriceUpload(BaseModel):
    products: list[dict]  # [{canonical_item, sku, name, cost}]
