from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str
    timestamp: Optional[datetime] = None


class ChatPriceRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    job_type: Optional[str] = None  # service, construction, commercial
    location: Optional[str] = None  # city or county
    county: Optional[str] = "Dallas"
    preferred_supplier: Optional[str] = None
    conversation_id: Optional[str] = None
    history: Optional[list[ChatMessage]] = []


class EstimateBreakdown(BaseModel):
    labor_total: float
    materials_total: float
    tax_total: float
    markup_total: float
    misc_total: float
    subtotal: float
    grand_total: float
    line_items: list[dict]


class ChatPriceResponse(BaseModel):
    answer: str
    estimate: Optional[EstimateBreakdown] = None
    estimate_id: Optional[int] = None
    confidence: float = 0.85
    confidence_label: str = "HIGH"
    assumptions: list[str] = []
    sources: list[str] = []
    conversation_id: Optional[str] = None
    job_type_detected: Optional[str] = None
    template_used: Optional[str] = None
    classified_by: Optional[str] = None  # "keyword" | "llm"
