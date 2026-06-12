"""
Intake Agent — v6.6.0

Infers job facts from a user's first message so the estimator can produce a
quote with fewer clarifying questions. Uses fast regex/heuristics by default
and falls back to a lightweight structured LLM call only when confidence is low.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger()


# Common fixture names mapped to canonical-ish keys used by the pricing engine.
_FIXTURE_ALIASES: dict[str, list[str]] = {
    "toilet": ["toilet", "commode", "water closet", "wc"],
    "sink": ["sink", "lavatory", "lav", "basin", "vanity"],
    "faucet": ["faucet", "tap", "spigot"],
    "shower": ["shower", "shower valve", "shower head"],
    "bathtub": ["bathtub", "tub", "bath"],
    "water_heater": ["water heater", "hot water heater", "tankless", "wh "],
    "garbage_disposal": ["garbage disposal", "disposal"],
    "dishwasher": ["dishwasher", "dish washer"],
    "hose_bib": ["hose bib", "hosebib", "spigot", "outdoor faucet"],
    "angle_stop": ["angle stop", "shutoff valve", "shut off valve"],
    "prv": ["prv", "pressure reducing valve", "pressure regulator"],
    "backflow": ["backflow", "back flow"],
    "whole_house_filter": ["whole house filter", "water filter", "filtration system"],
}

_URGENCY_ALIASES: dict[str, list[str]] = {
    "emergency": ["emergency", "asap", "urgent", "flooding", "burst", "leaking badly", "no water"],
    "same_day": ["same day", "today", "now", "right away"],
    "standard": [],
}

_TIER_ALIASES: dict[str, list[str]] = {
    "budget": ["cheap", "budget", "low cost", "affordable", "basic"],
    "premium": ["premium", "high end", "top of the line", "best", "luxury", "upscale"],
    "standard": [],
}

_DFW_CITIES: set[str] = {
    "dallas", "plano", "frisco", "mckinney", "allen", "richardson", "garland",
    "irving", "arlington", "fort worth", "fortworth", "denton", "lewisville",
    "flower mound", "carrollton", "farmers branch", "addison", "mesquite",
    "rockwall", "rowlett", "sachse", "wylie", "murphy", "parker",
}

_DFW_COUNTIES: set[str] = {
    "dallas", "tarrant", "collin", "denton", "rockwall", "kaufman", "ellis",
}


@dataclass
class IntakeResult:
    intent: str = ""
    fixture_counts: dict[str, int] = field(default_factory=dict)
    location: Optional[str] = None
    urgency: Optional[str] = None
    preferred_tier: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "fixture_counts": self.fixture_counts,
            "location": self.location,
            "urgency": self.urgency,
            "preferred_tier": self.preferred_tier,
            "confidence": self.confidence,
        }


def _extract_fixture_counts(text: str) -> dict[str, int]:
    """Extract fixture counts from phrases like '3 toilets', 'two sinks'."""
    counts: dict[str, int] = {}
    lowered = text.lower()

    # Word/number to int map
    word_nums = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "both": 2, "pair": 2,
    }

    # 1) Look for explicit counts: "3 toilets", "two sinks"
    pattern = re.compile(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|both|pair)\s+"
        r"([\w\s]+?)(?:,|\.|\band\b|$)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(lowered):
        raw_qty = match.group(1).lower()
        qty = int(raw_qty) if raw_qty.isdigit() else word_nums.get(raw_qty, 1)
        phrase = match.group(2).strip().lower()
        for key, aliases in _FIXTURE_ALIASES.items():
            if any(alias in phrase for alias in aliases):
                counts[key] = counts.get(key, 0) + qty
                break

    # 2) Detect bare plural nouns without numbers (assume count = 1 each)
    for key, aliases in _FIXTURE_ALIASES.items():
        for alias in aliases:
            # Use word boundaries for short aliases, substring for longer phrases
            if len(alias.split()) > 1:
                if alias in lowered:
                    counts.setdefault(key, 1)
            else:
                if re.search(rf"\b{re.escape(alias)}s?\b", lowered):
                    counts.setdefault(key, 1)

    return counts


def _extract_location(text: str) -> Optional[str]:
    """Extract DFW city or county names."""
    lowered = text.lower()
    for city in sorted(_DFW_CITIES, key=len, reverse=True):
        if city in lowered:
            return city.title()
    for county in sorted(_DFW_COUNTIES, key=len, reverse=True):
        if county in lowered:
            return county.title()
    return None


def _extract_urgency(text: str) -> Optional[str]:
    lowered = text.lower()
    for tier, aliases in [("emergency", _URGENCY_ALIASES["emergency"]),
                          ("same_day", _URGENCY_ALIASES["same_day"])]:
        if any(alias in lowered for alias in aliases):
            return tier
    return None


def _extract_tier(text: str) -> Optional[str]:
    lowered = text.lower()
    for tier, aliases in [("budget", _TIER_ALIASES["budget"]),
                          ("premium", _TIER_ALIASES["premium"])]:
        if any(alias in lowered for alias in aliases):
            return tier
    return None


def _derive_intent(fixture_counts: dict[str, int]) -> str:
    if not fixture_counts:
        return "general_plumbing"
    # Pick the most-mentioned fixture as the dominant intent
    dominant = max(fixture_counts, key=lambda k: fixture_counts[k])
    return f"{dominant}_work"


def _heuristic_intake(message: str) -> IntakeResult:
    """Fast rule-based intake inference."""
    fixture_counts = _extract_fixture_counts(message)
    location = _extract_location(message)
    urgency = _extract_urgency(message)
    tier = _extract_tier(message)
    intent = _derive_intent(fixture_counts)

    # Confidence is a simple function of how many distinct signals we extracted.
    signals = sum([
        bool(fixture_counts),
        location is not None,
        urgency is not None,
        tier is not None,
    ])
    confidence = min(0.95, 0.4 + signals * 0.18)

    return IntakeResult(
        intent=intent,
        fixture_counts=fixture_counts,
        location=location,
        urgency=urgency,
        preferred_tier=tier,
        confidence=confidence,
    )


def _has_intake_signal(message: str) -> bool:
    """Quick pre-check: does the message look like it contains job details?"""
    lowered = message.lower()
    if any(alias in lowered for aliases in _FIXTURE_ALIASES.values() for alias in aliases):
        return True
    if any(city in lowered for city in _DFW_CITIES):
        return True
    if any(alias in lowered for aliases in _URGENCY_ALIASES.values() for alias in aliases):
        return True
    if any(alias in lowered for aliases in _TIER_ALIASES.values() for alias in aliases):
        return True
    return False


async def infer_intake(message: str, county: Optional[str] = None) -> IntakeResult:
    """Infer job facts from a first message.

    Returns an IntakeResult. Uses fast heuristics; optionally falls back to a
    lightweight LLM call if the heuristic confidence is below threshold and the
    feature flag is enabled.
    """
    if not _has_intake_signal(message):
        return IntakeResult(confidence=0.0)

    heuristic = _heuristic_intake(message)

    # If we have a county hint but no extracted location, use the county.
    if county and not heuristic.location:
        heuristic.location = county.title()
        heuristic.confidence = min(0.98, heuristic.confidence + 0.05)

    if heuristic.confidence >= 0.7:
        logger.info("intake_agent.heuristic", confidence=heuristic.confidence, intent=heuristic.intent)
        return heuristic

    # LLM fallback only when enabled.
    if not getattr(settings, "intake_llm_fallback_enabled", True):
        return heuristic

    try:
        from app.services.llm_structured import llm_structured
        llm_result = await llm_structured.infer_intake(message, county=county)
        if llm_result is not None:
            logger.info("intake_agent.llm_fallback", confidence=llm_result.confidence)
            return IntakeResult(
                intent=llm_result.intent,
                fixture_counts=llm_result.fixture_counts,
                location=llm_result.location,
                urgency=llm_result.urgency,
                preferred_tier=llm_result.preferred_tier,
                confidence=llm_result.confidence,
            )
    except Exception as exc:
        logger.warning("intake_agent.llm_fallback_failed", error=str(exc))

    return heuristic
