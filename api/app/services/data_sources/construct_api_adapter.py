"""
ConstructDataAPI adapter (github.com/ojmarte/construction_api).

Connects to a self-hosted ConstructDataAPI instance when CONSTRUCT_API_URL is set.
Queries /api/materials and maps plumbing materials to canonical IDs.

ConstructDataAPI material schema:
  {
    "material_name": "string",
    "category": "string",
    "unit": {"measurement": "ea", "currency": "USD"},
    "prices": [{"price": 8.42, "date": "2025-01-01"}]
  }
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
import structlog

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

logger = structlog.get_logger()


@dataclass
class ConstructAPIPrice:
    canonical_id: str
    source: str = "construct_api"
    name: str = ""
    unit_cost: float = 0.0
    unit: str = "ea"
    category: str = ""
    currency: str = "USD"


# ─── Material name → canonical ID mapping ─────────────────────────────────────
# Maps keywords in ConstructDataAPI material names to our canonical IDs.
# Case-insensitive partial match; first match wins.
_NAME_TO_CANONICAL: list[tuple[str, str]] = [
    ("wax ring",            "toilet.wax_ring"),
    ("closet bolt",         "toilet.closet_bolts"),
    ("toilet supply",       "toilet.supply_line_12"),
    ("angle stop",          "toilet.angle_stop"),
    ("50.*gal.*gas.*water", "wh.50g_gas_unit"),
    ("40.*gal.*gas.*water", "wh.40g_gas_unit"),
    ("50.*gal.*elec.*water","wh.50g_electric_unit"),
    ("gas flex",            "wh.gas_flex_connector_18"),
    ("expansion tank",      "wh.expansion_tank_2g"),
    ("relief valve",        "wh.tp_valve_075"),
    ("dielectric union",    "wh.dielectric_union_pair"),
    ("drain pan",           "wh.drain_pan_26"),
    ("kitchen faucet",      "kitchen.faucet_single"),
    ("basket strainer",     "kitchen.basket_strainer"),
    ("p.trap",              "kitchen.pvc_trap_15"),
    ("garbage disposal|disposal.*1/2|disposal.*hp", "disposal.half_hp"),
    ("pressure reduc",      "prv.valve_075"),
    ("pressure gauge",      "prv.pressure_gauge"),
    ("shower valve",        "shower.valve_body"),
    ("shower trim",         "shower.trim_kit"),
    ("shower head",         "shower.head_standard"),
    ("shower arm",          "shower.arm_flange"),
    ("ball valve.*3/4|3/4.*ball valve", "valve.ball_075"),
    ("ball valve.*1/2|1/2.*ball valve", "valve.ball_050"),
    ("ball valve.*1\"|1\".*ball valve", "valve.ball_100"),
    ("gate valve",          "valve.gate_075"),
    ("pex.*3/4|3/4.*pex",  "misc.pex_crimp_075_10ft"),
    ("copper.*3/4|3/4.*copper", "misc.copper_075_10ft"),
    ("teflon|thread seal tape", "misc.teflon_tape"),
    ("pipe dope|joint compound", "misc.pipe_dope"),
]


def _match_canonical(name: str) -> Optional[str]:
    lower = name.lower()
    for pattern, canonical_id in _NAME_TO_CANONICAL:
        if re.search(pattern, lower):
            return canonical_id
    return None


def _latest_price(prices: list[dict]) -> Optional[float]:
    """Return the most recent price from ConstructDataAPI prices array."""
    if not prices:
        return None
    sorted_prices = sorted(
        prices,
        key=lambda p: p.get("date", ""),
        reverse=True,
    )
    val = sorted_prices[0].get("price")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


async def fetch_prices(base_url: str) -> list[ConstructAPIPrice]:
    """
    Fetch all materials from a self-hosted ConstructDataAPI instance and
    return those that match a canonical plumbing item.

    Args:
        base_url: Base URL of the ConstructDataAPI server (e.g. http://localhost:3000)
    """
    if not _HTTPX_AVAILABLE:
        logger.warning("construct_api.httpx_missing")
        return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/materials")
            resp.raise_for_status()
            materials: list[dict] = resp.json()
    except Exception as exc:
        logger.warning("construct_api.fetch_error", base_url=base_url, error=str(exc))
        return []

    results: list[ConstructAPIPrice] = []
    for mat in materials:
        name = mat.get("material_name", "")
        canonical_id = _match_canonical(name)
        if not canonical_id:
            continue
        price = _latest_price(mat.get("prices", []))
        if price is None or price <= 0:
            continue
        unit_obj = mat.get("unit", {})
        results.append(ConstructAPIPrice(
            canonical_id=canonical_id,
            name=name,
            unit_cost=price,
            unit=unit_obj.get("measurement", "ea"),
            category=mat.get("category", ""),
            currency=unit_obj.get("currency", "USD"),
        ))

    logger.info("construct_api.fetch_complete", base_url=base_url, matched=len(results))
    return results


async def post_material(base_url: str, canonical_id: str, name: str, category: str,
                        unit: str, price: float) -> bool:
    """
    Push a new material (or price update) to a ConstructDataAPI instance.
    Useful for seeding it with our DFW plumbing data.
    Returns True on success.
    """
    if not _HTTPX_AVAILABLE:
        return False
    import datetime
    body = {
        "material_name": name,
        "category": category,
        "unit": {"measurement": unit, "currency": "USD"},
        "prices": [{"price": price, "date": datetime.date.today().isoformat()}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/api/material", json=body)
            return resp.status_code in (200, 201)
    except Exception:
        return False
