"""Proactive add-on suggestions router (Track D2).

POST /api/v1/estimates/suggest-addons
    Body: {"task_codes": ["TOILET_REPLACE_STANDARD", ...]}
    Returns: [{"task_code": "...", "rationale": "...", "severity": "..."}, ...]

The endpoint is read-only and stateless — it does not mutate the estimate. The
UI is responsible for letting the user accept/reject each suggestion and adding
the corresponding line via the normal estimate edit path.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.services.addon_suggestions import suggest_addons


router = APIRouter()


class SuggestRequest(BaseModel):
    task_codes: List[str] = Field(default_factory=list, max_length=200)
    max_suggestions: int = Field(default=8, ge=1, le=50)


class SuggestionOut(BaseModel):
    task_code: str
    rationale: str
    severity: str


@router.post("/suggest-addons", response_model=List[SuggestionOut])
async def suggest_estimate_addons(
    body: SuggestRequest,
    _user=Depends(get_current_user),
):
    """Return missing-line-item suggestions for an in-progress estimate."""
    suggestions = suggest_addons(
        body.task_codes,
        max_suggestions=body.max_suggestions,
    )
    return [
        SuggestionOut(
            task_code=s.task_code,
            rationale=s.rationale,
            severity=s.severity,
        )
        for s in suggestions
    ]
