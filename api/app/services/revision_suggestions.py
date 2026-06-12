"""
Revision Suggestions — v6.6.0

Generates proactive, context-aware revision suggestions after an estimate is
produced. Rules are intentionally simple and auditable; no LLM required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.services.pricing_engine import EstimateResult

logger = structlog.get_logger()


@dataclass
class RevisionSuggestion:
    id: str
    label: str
    action: str
    delta: dict = field(default_factory=dict)
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "action": self.action,
            "delta": self.delta,
            "confidence": self.confidence,
        }


def _has_canonical(estimate: EstimateResult, canonical_items: set[str]) -> bool:
    return any((item.canonical_item or "").upper() in canonical_items for item in estimate.line_items)


def _count_distinct_fixtures(estimate: EstimateResult, fixture_keys: set[str]) -> int:
    """Count distinct fixture types present in the estimate.

    A single line item like TUB_SHOWER_COMBO_REPLACE should contribute 1,
    not 2, to avoid double-counting combo fixtures.
    """
    count = 0
    for item in estimate.line_items:
        if not item.canonical_item:
            continue
        canonical = item.canonical_item.lower()
        if any(key in canonical for key in fixture_keys):
            count += 1
    return count


_WATER_HEATER_CODES = {
    "WH_40G_GAS_STANDARD", "WH_50G_GAS_STANDARD", "WH_40G_ELEC_STANDARD",
    "WH_50G_ELEC_STANDARD", "WH_50G_GAS_ATTIC",
}

_TANKLESS_CODES = {"WH_TANKLESS_GAS", "WH_TANKLESS_ELEC"}

_TOILET_CODES = {"TOILET_REPLACE_STANDARD", "TOILET_COMFORT_HEIGHT", "TOILET_INSTALL_NEW"}

_SINK_FAUCET_CODES = {
    "LAV_SINK_REPLACE", "KITCHEN_FAUCET_REPLACE", "LAV_FAUCET_REPLACE",
    "SHOWER_VALVE_REPLACE", "TUB_SHOWER_COMBO_REPLACE",
}


_RULES = []


def _rule_water_heater_to_tankless(estimate: EstimateResult) -> Optional[RevisionSuggestion]:
    if not _has_canonical(estimate, _WATER_HEATER_CODES):
        return None
    return RevisionSuggestion(
        id=str(uuid.uuid4())[:8],
        label="Upgrade to tankless water heater",
        action="upgrade",
        delta={"target": "water_heater", "to": "tankless"},
        confidence=0.85,
    )


def _rule_add_permit(estimate: EstimateResult) -> Optional[RevisionSuggestion]:
    # Permit line items are usually line_type == "permit" or description contains "permit"
    has_permit = any(
        item.line_type == "permit" or "permit" in item.description.lower()
        for item in estimate.line_items
    )
    if has_permit:
        return None
    # Only suggest permit for bigger jobs
    big_job_codes = _WATER_HEATER_CODES | _TOILET_CODES | _SINK_FAUCET_CODES | {"WHOLE_HOUSE_REPIPING"}
    if not _has_canonical(estimate, big_job_codes):
        return None
    return RevisionSuggestion(
        id=str(uuid.uuid4())[:8],
        label="Add permit & inspection",
        action="add",
        delta={"target": "permit"},
        confidence=0.7,
    )


def _rule_premium_fixtures(estimate: EstimateResult) -> Optional[RevisionSuggestion]:
    if not (_has_canonical(estimate, _TOILET_CODES) or _has_canonical(estimate, _SINK_FAUCET_CODES)):
        return None
    return RevisionSuggestion(
        id=str(uuid.uuid4())[:8],
        label="Upgrade to premium fixtures",
        action="upgrade",
        delta={"target": "fixtures", "to": "premium"},
        confidence=0.75,
    )


def _rule_multiple_bathrooms_repipe(estimate: EstimateResult) -> Optional[RevisionSuggestion]:
    # Count distinct bathroom fixtures (toilet/shower/tub). Require 2+ distinct
    # fixtures before suggesting a whole-house repipe to avoid noisy suggestions.
    fixture_count = _count_distinct_fixtures(estimate, {"toilet", "shower", "tub"})
    if fixture_count < 2:
        return None
    return RevisionSuggestion(
        id=str(uuid.uuid4())[:8],
        label="Get a whole-house repipe quote",
        action="add",
        delta={"target": "whole_house_repipe"},
        confidence=0.6,
    )


_RULES = [
    _rule_water_heater_to_tankless,
    _rule_add_permit,
    _rule_premium_fixtures,
    _rule_multiple_bathrooms_repipe,
]


def suggest_revisions(estimate: EstimateResult) -> list[RevisionSuggestion]:
    """Return up to 3 proactive revision suggestions for the given estimate."""
    suggestions: list[RevisionSuggestion] = []
    for rule in _RULES:
        try:
            suggestion = rule(estimate)
            if suggestion is not None:
                suggestions.append(suggestion)
        except Exception as exc:
            logger.warning("revision_suggestions.rule_failed", rule=rule.__name__, error=str(exc))

    # Sort by confidence descending, cap at 3
    suggestions.sort(key=lambda s: s.confidence, reverse=True)
    return suggestions[:3]
