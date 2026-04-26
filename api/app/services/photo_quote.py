"""
Phase 3 — Photo-based on-site pricing.

Takes a structured vision result from `vision_service.describe_photo` and turns
it into a priced draft estimate using the existing `PricingEngine.quick_estimate`.

Design notes
------------
* This is intentionally rule-based, not LLM-based: every (item, condition) →
  task_code mapping is auditable and stable.  The LLM only does the seeing.
* Phase 3.5 adds a DB override layer (`vision_item_mappings`) so non-engineers
  can edit mappings live; the static `_ITEM_TO_TASK` dict is the fallback.
* If we cannot map an item, we still surface it in the response as `unmapped`
  so the user (or admin) can extend the table.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vision_mappings import VisionItemMapping
from app.services.pricing_engine import PricingEngine
from app.services.labor_engine import list_template_codes

logger = structlog.get_logger()

# Vision item type → (default task_code, default task_code when "leaking"/"broken")
# When the second slot is None, the same code is used regardless of condition.
_ITEM_TO_TASK: Dict[str, Tuple[str, Optional[str]]] = {
    "toilet": ("TOILET_REPLACE", "TOILET_REPLACE"),
    "lavatory": ("LAV_SINK_REPLACE", "LAV_SINK_REPLACE"),
    "kitchen_sink": ("KITCHEN_SINK_REPLACE", "KITCHEN_SINK_REPLACE"),
    "faucet_kitchen": ("KITCHEN_FAUCET_REPLACE", "KITCHEN_FAUCET_REPLACE"),
    "faucet_lavatory": ("LAV_FAUCET_REPLACE", "LAV_FAUCET_REPLACE"),
    "shower_valve": ("SHOWER_VALVE_REPLACE", "SHOWER_VALVE_REPLACE"),
    "tub_spout": ("TUB_SPOUT_REPLACE", None),
    "shower_head": ("SHOWER_HEAD_REPLACE", None),
    "water_heater": ("WATER_HEATER_REPLACE_50G_GAS", "WATER_HEATER_REPLACE_50G_GAS"),
    "tankless_water_heater": ("TANKLESS_WATER_HEATER_INSTALL", "TANKLESS_WATER_HEATER_INSTALL"),
    "garbage_disposal": ("DISPOSAL_REPLACE", "DISPOSAL_REPLACE"),
    "disposal": ("DISPOSAL_REPLACE", "DISPOSAL_REPLACE"),
    "dishwasher": ("DISHWASHER_HOOKUP", "DISHWASHER_HOOKUP"),
    "washing_machine": ("WASHER_BOX_REPLACE", None),
    "ice_maker_line": ("ICE_MAKER_LINE_INSTALL", None),
    "hose_bib": ("HOSE_BIB_REPLACE", "HOSE_BIB_REPLACE"),
    "angle_stop": ("ANGLE_STOP_REPLACE", "ANGLE_STOP_REPLACE"),
    "supply_line": ("SUPPLY_LINE_REPLACE", "SUPPLY_LINE_REPLACE"),
    "p_trap": ("P_TRAP_REPLACE", "P_TRAP_REPLACE"),
    "s_trap": ("P_TRAP_REPLACE", "P_TRAP_REPLACE"),
    "prv": ("PRV_REPLACE", "PRV_REPLACE"),
    "water_softener": ("WATER_SOFTENER_INSTALL", None),
    "backflow_preventer": ("BACKFLOW_PREVENTER_INSTALL", "BACKFLOW_PREVENTER_REPAIR"),
    "floor_drain": ("DRAIN_CLEAN_FLOOR", "DRAIN_CLEAN_FLOOR"),
    "cleanout": ("CLEAN_OUT_INSTALL", None),
    "ejector_pump": ("EJECTOR_PUMP_INSTALL", "EJECTOR_PUMP_INSTALL"),
    # Pipe issues — leaks always go to a repair code regardless of material
    "leak": ("WATER_LEAK_REPAIR", "WATER_LEAK_REPAIR"),
    "pipe_pvc": ("PVC_PIPE_REPAIR", "PVC_PIPE_REPAIR"),
    "pipe_copper": ("COPPER_PINHOLE_REPAIR", "COPPER_PINHOLE_REPAIR"),
    "pipe_pex": ("PEX_PIPE_REPAIR", "PEX_PIPE_REPAIR"),
    "pipe_galvanized": ("GALVANIZED_PIPE_REPAIR", "GALVANIZED_PIPE_REPAIR"),
    "pipe_cast_iron": ("CAST_IRON_PIPE_REPAIR", "CAST_IRON_PIPE_REPAIR"),
    "gas_valve": ("GAS_SHUTOFF_VALVE_REPLACE", "GAS_SHUTOFF_VALVE_REPLACE"),
    "gas_appliance": ("GAS_LINE_INSTALL", None),
}

_LEAK_CONDITIONS = {"leaking", "broken", "corroded"}


def _resolve_task_code(
    item_type: str,
    condition: Optional[str],
    overrides: Optional[Dict[str, Tuple[str, Optional[str]]]] = None,
) -> Optional[str]:
    """Pick the task code for a (type, condition) pair, or None if unmapped.

    `overrides` (optional) is a {item_type → (default_code, problem_code)}
    mapping pulled from the DB; it wins over the static dict.
    """
    key = (item_type or "").lower().strip()
    mapping = (overrides or {}).get(key) or _ITEM_TO_TASK.get(key)
    if not mapping:
        return None
    primary, when_problem = mapping
    if condition and condition.lower() in _LEAK_CONDITIONS and when_problem:
        candidate = when_problem
    else:
        candidate = primary
    if not candidate:
        return None
    valid = {code.upper() for code in list_template_codes()}
    return candidate if candidate.upper() in valid else None


async def load_db_overrides(db: AsyncSession) -> Dict[str, Tuple[str, Optional[str]]]:
    """Load active vision-item overrides from the database.

    Cheap to call per-request (small table). If the table doesn't exist or
    the query fails, we just fall back to the static dict.
    """
    try:
        rows = (
            await db.execute(
                select(VisionItemMapping).where(VisionItemMapping.enabled.is_(True))
            )
        ).scalars().all()
        return {
            (r.item_type or "").lower().strip(): (r.default_task_code, r.problem_task_code)
            for r in rows
            if r.item_type and r.default_task_code
        }
    except Exception as e:
        logger.warning("photo_quote.overrides_load_failed", error=str(e))
        return {}


def build_quick_quote(
    vision: Dict[str, Any],
    *,
    county: str = "Dallas",
    city: Optional[str] = None,
    urgency: str = "standard",
    access: str = "first_floor",
    overrides: Optional[Dict[str, Tuple[str, Optional[str]]]] = None,
) -> Dict[str, Any]:
    """
    Convert a `vision_service.describe_photo` result into a priced draft.

    Returns:
        {
          "scene": str,
          "summary": str,
          "lines": [{
              "task_code": str, "description": str, "quantity": int,
              "confidence": float, "subtotal_low": float, "subtotal_high": float,
              "source_item": {...the original vision item...}
          }],
          "totals": {"low": float, "high": float, "expected": float},
          "unmapped": [{"type": str, "count": int, "confidence": float, "reason": str}]
        }
    """
    engine = PricingEngine()
    items: List[Dict[str, Any]] = vision.get("items", []) or []

    lines: List[Dict[str, Any]] = []
    unmapped: List[Dict[str, Any]] = []
    total_low = 0.0
    total_high = 0.0
    total_expected = 0.0

    for it in items:
        item_type = (it.get("type") or "").lower().strip()
        if not item_type:
            continue
        count = max(1, int(it.get("count") or 1))
        confidence = float(it.get("confidence") or 0.0)
        condition = (it.get("condition") or None)

        task_code = _resolve_task_code(item_type, condition, overrides=overrides)
        if not task_code:
            unmapped.append({
                "type": item_type,
                "count": count,
                "confidence": confidence,
                "condition": condition,
                "reason": "no template mapping",
            })
            continue

        try:
            est = engine.quick_estimate(
                task_code=task_code,
                county=county,
                city=city,
                urgency=urgency,
                access=access,
                quantity=count,
                include_trip_charge=(len(lines) == 0),  # only first line gets the trip charge
            )
        except Exception as e:
            logger.warning("photo_quote.estimate_failed",
                           task_code=task_code, error=str(e))
            unmapped.append({
                "type": item_type,
                "count": count,
                "confidence": confidence,
                "condition": condition,
                "reason": f"pricing failed: {e}",
            })
            continue

        low = float(getattr(est, "grand_total", 0.0) or 0.0) * 0.9
        high = float(getattr(est, "grand_total", 0.0) or 0.0) * 1.1
        expected = float(getattr(est, "grand_total", 0.0) or 0.0)
        total_low += low
        total_high += high
        total_expected += expected

        lines.append({
            "task_code": task_code,
            "description": getattr(est, "template_code", None) or task_code,
            "quantity": count,
            "confidence": round(confidence, 3),
            "condition": condition,
            "subtotal_low": round(low, 2),
            "subtotal_high": round(high, 2),
            "subtotal_expected": round(expected, 2),
            "source_item": it,
        })

    return {
        "scene": vision.get("scene", "unknown"),
        "summary": vision.get("summary", ""),
        "lines": lines,
        "totals": {
            "low": round(total_low, 2),
            "high": round(total_high, 2),
            "expected": round(total_expected, 2),
        },
        "unmapped": unmapped,
        "county": county,
        "city": city,
    }
