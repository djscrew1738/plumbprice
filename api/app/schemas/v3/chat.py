from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ChatMessageV3(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None


class CustomerInfoV3(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ChatPriceRequestV3(BaseModel):
    message: str = Field(..., min_length=3, max_length=5000)
    job_type: Optional[str] = None
    location: Optional[str] = None
    county: Optional[str] = None
    preferred_supplier: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[int] = None
    history: Optional[list[ChatMessageV3]] = []
    project_id: Optional[int] = None
    customer: Optional[CustomerInfoV3] = None
    blueprint_job_id: Optional[int] = None


class ToolCallInfo(BaseModel):
    tool_name: str
    latency_ms: int
    error: Optional[str] = None


class MarketAdjustmentInfo(BaseModel):
    name: str
    category: str
    factor: float


class EstimateBreakdownV3(BaseModel):
    labor_total: float
    materials_total: float
    tax_total: float
    markup_total: float
    misc_total: float
    subtotal: float
    grand_total: float
    line_items: list[dict]
    market_adjustment_applied: float = 1.0
    confidence_components: dict = {}


class ChatPriceResponseV3(BaseModel):
    answer: str
    estimate: Optional[EstimateBreakdownV3] = None
    estimate_id: Optional[int] = None
    session_id: Optional[int] = None
    confidence: float = 0.85
    confidence_label: str = "HIGH"
    assumptions: list[str] = []
    sources: list[str] = []
    conversation_id: Optional[str] = None
    job_type_detected: Optional[str] = None
    template_used: Optional[str] = None
    classified_by: Optional[str] = None
    clarification_questions: Optional[list[str]] = None
    tool_calls: list[ToolCallInfo] = []
    market_adjustments: list[MarketAdjustmentInfo] = []
    agent_trace: dict = {}
