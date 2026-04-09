"""
pricing_table.py -- Generate LLM-readable markdown tables from the pricing engine.

Called by llm_service.py to embed a compact pricing reference in system prompts.
Keeps prompt data always in sync with LABOR_TEMPLATES -- no manual updates needed.
"""

from __future__ import annotations

_MARKET_RANGES: dict[str, str] = {
    # Water heater replace
    "WH_50G_GAS_STANDARD":      "$950-$1,850",
    "WH_50G_GAS_ATTIC":         "$1,100-$2,100",
    "WH_40G_GAS_STANDARD":      "$850-$1,650",
    "WH_50G_ELECTRIC_STANDARD": "$900-$1,750",
    "WH_TANKLESS_GAS":          "$1,500-$3,500",
    # Water heater repair/maintenance
    "WH_REPAIR_GAS":            "$200-$500",
    "WH_ELEMENT_REPLACE":       "$150-$350",
    "WH_FLUSH_MAINTENANCE":     "$100-$200",
    "WH_ANODE_REPLACE":         "$80-$175",
    "TANKLESS_WH_DESCALE":      "$175-$325",
    "EXPANSION_TANK_INSTALL":   "$150-$300",
    # Toilets
    "TOILET_REPLACE_STANDARD":  "$300-$800",
    "TOILET_COMFORT_HEIGHT":    "$375-$900",
    "TOILET_TANK_REBUILD":      "$175-$350",
    "TOILET_SEAT_REPLACE":      "$85-$150",
    "TOILET_WAX_RING_ONLY":     "$175-$295",
    "TOILET_AUGER_SERVICE":     "$115-$225",
    # Drains
    "DRAIN_CLEAN_STANDARD":     "$125-$250",
    "DRAIN_CLEAN_KITCHEN":      "$125-$250",
    "DRAIN_CLEAN_BATHTUB":      "$100-$200",
    "DRAIN_CLEAN_SHOWER":       "$100-$200",
    "MAIN_LINE_CLEAN":          "$350-$500",
    "HYDROJETTING":             "$500-$900",
    "CAMERA_INSPECTION":        "$200-$300",
    # Faucets
    "LAV_FAUCET_REPLACE":       "$200-$450",
    "KITCHEN_FAUCET_REPLACE":   "$250-$550",
    "FAUCET_CARTRIDGE_REPAIR":  "$150-$275",
    "SHOWER_VALVE_REPLACE":     "$350-$700",
    "SHOWER_VALVE_CARTRIDGE":   "$175-$350",
    "HOSE_BIB_REPLACE":         "$175-$325",
    "HOSE_BIB_FREEZE_REPAIR":   "$200-$375",
    # Fixtures
    "GARBAGE_DISPOSAL_INSTALL": "$250-$500",
    "GARBAGE_DISPOSAL_REPAIR":  "$100-$200",
    "ANGLE_STOP_REPLACE":       "$100-$200",
    "PTRAP_REPLACE":            "$115-$225",
    "SINK_REPLACE_KITCHEN":     "$400-$850",
    "SINK_REPLACE_BATH":        "$275-$600",
    "TUB_SHOWER_COMBO_REPLACE": "$900-$2,500",
    "BATHTUB_DRAIN_REPAIR":     "$150-$300",
    # Slab / water main / leak
    "SLAB_LEAK_REPAIR":         "$1,300-$5,000",
    "SLAB_LEAK_REROUTE":        "$1,500-$4,500",
    "LEAK_DETECTION":           "$175-$450",
    "WATER_MAIN_REPAIR":        "$400-$1,200",
    "WATER_LINE_REPAIR_MINOR":  "$250-$600",
    "PRESSURE_TEST_SYSTEM":     "$125-$225",
    # Gas
    "GAS_LINE_NEW_RUN":         "$500-$1,500",
    "GAS_LINE_REPAIR_MINOR":    "$250-$700",
    "GAS_SHUTOFF_REPLACE":      "$175-$350",
    "GAS_PRESSURE_TEST":        "$100-$175",
    # Sewer / drain / main
    "SEWER_SPOT_REPAIR":        "$2,500-$6,000",
    "CLEAN_OUT_INSTALL":        "$500-$1,200",
    # Repipe
    "WHOLE_HOUSE_REPIPE_PEX":   "$4,000-$8,000",
    # Fixtures & misc
    "PRV_REPLACE":              "$275-$550",
    "WATER_SOFTENER_INSTALL":   "$800-$2,000",
    "WATER_FILTER_WHOLE_HOUSE": "$500-$1,500",
    "RECIRC_PUMP_INSTALL":      "$450-$900",
    "DISHWASHER_HOOKUP":        "$150-$325",
    "EXPANSION_TANK_ONLY":      "$150-$300",
    "WATER_HAMMER_ARRESTER":    "$125-$275",
    "LAUNDRY_BOX_REPLACE":      "$200-$425",
    "ICE_MAKER_LINE_INSTALL":   "$125-$250",
    "MIXING_VALVE_REPLACE":     "$275-$550",
    "LAUNDRY_DRAIN_INSTALL":    "$250-$500",
    "BACKFLOW_PREVENTER_INSTALL": "$400-$900",
    "BACKFLOW_TEST_ANNUAL":     "$75-$175",
    "OUTDOOR_DRAIN_INSTALL":    "$450-$850/10ft",
    "SHOWER_PAN_REPLACE":       "$900-$2,200",
    "SUMP_PUMP_INSTALL":        "$700-$1,800",
    # Construction
    "ROUGH_IN_FULL_BATH":       "$2,500-$5,500",
    "ROUGH_IN_HALF_BATH":       "$1,200-$2,800",
    "ROUGH_IN_KITCHEN":         "$1,500-$3,500",
    "TOP_OUT_FULL_BATH":        "$800-$1,800",
    "FINAL_SET_FULL_BATH":      "$600-$1,500",
}

_CATEGORY_ORDER = ["service", "construction", "commercial"]


def build_pricing_table(max_rows: int = 999) -> str:
    """
    Return a compact markdown table of all labor templates for LLM system prompts.
    Sorted by category then template name. Market ranges from DFW 2025-2026 data.
    """
    from app.services.labor_engine import LABOR_TEMPLATES

    lines = [
        "## DFW Plumbing Price Reference (2025-2026)",
        "",
        "| Task Code | Service | Market Range (DFW) |",
        "|---|---|---|",
    ]

    # Group by category
    by_cat: dict[str, list] = {}
    for code, tpl in LABOR_TEMPLATES.items():
        by_cat.setdefault(tpl.category, []).append((code, tpl))

    count = 0
    for cat in _CATEGORY_ORDER:
        templates = sorted(by_cat.get(cat, []), key=lambda x: x[1].name)
        if templates:
            lines.append(f"| **{cat.upper()}** | | |")
        for code, tpl in templates:
            if count >= max_rows:
                break
            market = _MARKET_RANGES.get(code, "--")
            lines.append(f"| `{code}` | {tpl.name} | {market} |")
            count += 1

    return "\n".join(lines)


def build_task_code_list() -> str:
    """Return a compact comma-separated list of all task codes for the classify prompt."""
    from app.services.labor_engine import LABOR_TEMPLATES
    codes = sorted(LABOR_TEMPLATES.keys())
    return ",\n  ".join(codes)


def build_county_list() -> str:
    """Return the valid county list for the classify prompt."""
    from app.services.pricing_engine import County
    return " | ".join(f'"{c.value}"' for c in County)
