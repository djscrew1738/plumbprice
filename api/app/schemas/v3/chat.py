from pydantic import BaseModel, Field
from typing import Optional
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


class PreviousEstimateContext(BaseModel):
    """Previous estimate breakdown for revision requests."""
    estimate_id: int = 0
    template_code: str = ""
    line_items: list[dict] = []
    grand_total: float = 0.0
    labor_total: float = 0.0
    materials_total: float = 0.0


class IntakeResultV3(BaseModel):
    """Inferred job facts from the user's first message."""
    intent: str = ""
    fixture_counts: dict[str, int] = Field(default_factory=dict)
    location: Optional[str] = None
    urgency: Optional[str] = None
    preferred_tier: Optional[str] = None
    confidence: float = 0.0


class RevisionSuggestionV3(BaseModel):
    """Proactive revision suggestion shown after an estimate."""
    id: str
    label: str
    action: str
    delta: dict = Field(default_factory=dict)
    confidence: float = 0.8


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
    previous_estimate: Optional[PreviousEstimateContext] = None
    confirmed_intake: Optional[IntakeResultV3] = None


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


class SuggestedContextV3(BaseModel):
    """Proactive suggestion for missing context based on user memories."""
    field: str
    value: str
    reason: str
    confidence: float = 0.8


class EstimateDiffV3(BaseModel):
    """Diff between previous and current estimate for revision display."""
    previous_total: float
    new_total: float
    total_delta: float
    added_line_items: list[dict] = []
    removed_line_items: list[dict] = []
    modified_line_items: list[dict] = []


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
    suggested_context: list[SuggestedContextV3] = []
    tool_calls: list[ToolCallInfo] = []
    market_adjustments: list[MarketAdjustmentInfo] = []
    agent_trace: dict = {}
    estimate_diff: Optional[EstimateDiffV3] = None
    blueprint_seeded: bool = False
    variant_label: Optional[str] = None
    intake_result: Optional[IntakeResultV3] = None
    revision_suggestions: list[RevisionSuggestionV3] = Field(default_factory=list)


class ChatCompareRequestV3(ChatPriceRequestV3):
    """Request to generate multiple estimate variants for side-by-side comparison."""
    variant_tiers: list[str] = ["budget", "standard", "premium"]


class VariantInfoV3(BaseModel):
    """Single variant within a comparison response."""
    variant_label: str
    response: ChatPriceResponseV3


class ChatCompareResponseV3(BaseModel):
    """Multi-variant comparison response."""
    variant_group_id: str
    classification: dict = {}
    variants: list[ChatPriceResponseV3] = []
    assumptions: list[str] = []
    session_id: Optional[int] = None
