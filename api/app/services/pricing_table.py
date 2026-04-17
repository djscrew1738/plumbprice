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
    # ── Expanded DFW Templates (2025-2026 additions) ─────────────────────────
    # Water Heater additions
    "WH_50G_ELECTRIC_ATTIC":    "$1,000-$2,000",
    "WH_TANKLESS_ELECTRIC":     "$1,200-$2,800",
    "WH_HYBRID_HEAT_PUMP":      "$2,500-$4,500",
    "WH_RECIRCULATION_LINE_NEW":"$1,200-$2,500",
    "WH_PAN_DRAIN_OVERFLOW_ONLY":"$125-$275",
    # Drain & Sewer additions
    "DRAIN_CLEAN_FLOOR":        "$100-$200",
    "DRAIN_CLEAN_MAIN_HYDRO_COMBO":"$600-$1,100",
    "SEWER_CAMERA_LOCATOR":     "$250-$450",
    "SEWER_LINER_CIPP":         "$3,500-$8,000/50ft",
    "SEWER_BELLY_REPAIR":       "$2,500-$6,500",
    "DRAIN_POP_UP_REPLACE":     "$85-$175",
    "CONDENSATE_DRAIN_INSTALL": "$175-$350",
    # Fixture additions
    "BIDET_STANDALONE_INSTALL": "$400-$900",
    "PEDESTAL_SINK_INSTALL":    "$300-$650",
    "UNDERMOUNT_SINK_INSTALL":  "$450-$950",
    "FREESTANDING_TUB_INSTALL": "$800-$2,000",
    "WALK_IN_SHOWER_VALVE_INSTALL":"$1,200-$3,000",
    "WET_BAR_SINK_INSTALL":     "$350-$750",
    "UTILITY_SINK_INSTALL":     "$275-$550",
    "POT_FILLER_INSTALL":       "$350-$800",
    # Pipe repair additions
    "COPPER_PINHOLE_REPAIR":    "$200-$450",
    "POLYBUTYLENE_SECTION_REPLACE":"$275-$600",
    "PIPE_BURST_EMERGENCY":     "$400-$1,200",
    "FREEZE_DAMAGE_THAW_REPAIR":"$500-$1,500",
    "PIPE_INSULATION_INSTALL":  "$150-$350/50ft",
    # Gas line additions
    "GAS_LINE_DRYER":           "$200-$400",
    "GAS_LINE_RANGE_OVEN":      "$200-$425",
    "GAS_LINE_FIREPLACE":       "$500-$1,200",
    "GAS_LINE_GRILL_OUTDOOR":   "$450-$1,100",
    "GAS_LEAK_DETECTION":       "$100-$200",
    # Commercial additions
    "COMMERCIAL_GREASE_TRAP_CLEAN":"$250-$500",
    "COMMERCIAL_GREASE_TRAP_INSTALL":"$2,000-$5,500",
    "COMMERCIAL_FLOOR_DRAIN_INSTALL":"$800-$2,000",
    "FLUSHOMETER_REPLACE":      "$300-$600",
    "COMMERCIAL_WATER_HEATER_INSTALL":"$2,500-$5,000",
    # Outdoor/Irrigation additions
    "IRRIGATION_BACKFLOW_INSTALL":"$350-$800",
    "IRRIGATION_VALVE_REPAIR":  "$100-$225",
    "CATCH_BASIN_INSTALL":      "$450-$900",
    "YARD_HYDRANT_INSTALL":     "$400-$850",
    # Specialty additions
    "ADA_GRAB_BAR_INSTALL":     "$125-$275",
    "WATER_HEATER_TIMER_INSTALL":"$125-$250",
    "EMERGENCY_SHUTOFF_VALVE_INSTALL":"$500-$1,200",

    # ── Sync: existing templates that were missing market ranges ──────────────
    "ADA_RESTROOM_ROUGH_IN":    "$3,500-$7,000",
    "ANGLE_STOP_REPLACE_PAIR":  "$150-$300",
    "BIDET_SEAT_INSTALL":       "$200-$450",
    "COMMERCIAL_SINK_INSTALL":  "$350-$750",
    "FILTRATION_WHOLE_HOUSE":   "$500-$1,500",
    "FINAL_SET_PER_FIXTURE":    "$85-$200/fixture",
    "HOSE_BIB_ADD_NEW":         "$250-$500",
    "LAV_SINK_REPLACE":         "$250-$550",
    "METER_SET":                "$250-$600",
    "PRV_INSTALL_NEW":          "$350-$700",
    "ROUGH_IN_PER_BATH_GROUP":  "$2,000-$4,500/group",
    "RO_SYSTEM_INSTALL":        "$350-$800",
    "SEWER_LINE_REPLACE_FULL":  "$3,500-$8,000",
    "SHOWER_HEAD_REPLACE":      "$75-$175",
    "SUPPLY_LINE_REPLACE":      "$125-$275",
    "TOILET_FILL_VALVE_REPLACE":"$95-$195",
    "TOILET_FLANGE_REPAIR":     "$175-$375",
    "TOILET_FLAPPER_REPLACE":   "$75-$150",
    "TOILET_INSTALL_NEW":       "$275-$550",
    "TOP_OUT_PER_FIXTURE":      "$75-$175/fixture",
    "TUB_SPOUT_REPLACE":        "$100-$225",
    "UNDERGROUND_PER_LF":       "$25-$55/LF",
    "URINAL_FLUSH_VALVE_REPLACE":"$200-$425",

    # ── Phase 3: Comprehensive DFW Expansion (2025-2026) ─────────────────────
    # A. Diagnostic & Inspection
    "LEAK_DETECTION_ELECTRONIC": "$175-$400",
    "SMOKE_TEST_SEWER":         "$250-$500",
    "HYDROSTATIC_TEST_SEWER":   "$350-$700",
    "THERMAL_IMAGING_LEAK":     "$200-$450",
    "VIDEO_CALL_DIAGNOSTIC":    "$50-$95",
    "SECOND_OPINION_INSPECTION":"$95-$175",
    # B. Water Line & Supply
    "WATER_LINE_REPAIR_COPPER": "$250-$550",
    "WATER_LINE_REPAIR_PEX":    "$175-$400",
    "WATER_LINE_REPLACE_MAIN_STREET":"$2,500-$6,000",
    "MANIFOLD_INSTALL_PEX":     "$800-$1,800",
    "PRESSURE_BOOSTER_INSTALL": "$800-$1,600",
    "SHUT_OFF_VALVE_MAIN":      "$250-$600",
    "THERMAL_EXPANSION_VALVE":  "$200-$425",
    # C. Drain & Waste Expanded
    "DRAIN_CLEAN_LAUNDRY":      "$150-$325",
    "DRAIN_CLEAN_DOUBLE_KITCHEN":"$175-$375",
    "CLEANOUT_CAP_REPLACE":     "$75-$175",
    "VENT_PIPE_REPAIR_ROOF":    "$350-$750",
    "AAV_INSTALL":              "$150-$325",
    "EJECTOR_PUMP_INSTALL":     "$1,200-$2,800",
    # D. Bathroom Fixture Expanded
    "SHOWER_DOOR_PLUMBING_PREP":"$150-$350",
    "SHOWER_DIVERTER_REPAIR":   "$125-$275",
    "ROMAN_TUB_FAUCET_REPLACE": "$350-$700",
    "CLAW_FOOT_TUB_PLUMBING":  "$500-$1,200",
    "BARRIER_FREE_SHOWER_INSTALL":"$2,000-$4,500",
    "STEAM_SHOWER_VALVE_INSTALL":"$800-$1,800",
    "BIDET_SPRAYER_INSTALL":    "$100-$225",
    # E. Kitchen & Appliance
    "INSTANT_HOT_WATER_INSTALL":"$250-$500",
    "REFRIGERATOR_LINE_INSTALL":"$125-$275",
    "DISHWASHER_DRAIN_REPAIR":  "$125-$275",
    "GARBAGE_DISPOSAL_REPLACE_HP":"$350-$650",
    "PREP_SINK_INSTALL":        "$350-$700",
    "COMMERCIAL_SPRAYER_FAUCET":"$350-$700",
    # F. Outdoor & Yard Expanded
    "FRENCH_DRAIN_INSTALL":     "$1,200-$2,800/25LF",
    "SUMP_PUMP_REPLACE":        "$500-$1,200",
    "POOL_PLUMBING_REPAIR":     "$300-$700",
    "OUTDOOR_SHOWER_INSTALL":   "$600-$1,400",
    "SPRINKLER_LINE_REPAIR":    "$150-$350",
    "RAIN_BARREL_HOOKUP":       "$200-$450",
    # G. Gas System Expanded
    "GAS_LINE_POOL_HEATER":     "$500-$1,200",
    "GAS_LINE_GENERATOR":       "$600-$1,400",
    "GAS_LINE_TANKLESS_WH":     "$400-$900",
    "GAS_METER_UPGRADE_COORD":  "$200-$450",
    "GAS_APPLIANCE_DISCONNECT": "$100-$225",
    # H. Water Treatment
    "WATER_SOFTENER_REPLACE":   "$600-$1,400",
    "WATER_SOFTENER_REPAIR":    "$200-$450",
    "UV_DISINFECTION_INSTALL":  "$500-$1,100",
    "SEDIMENT_FILTER_INSTALL":  "$200-$450",
    "WATER_TESTING_SERVICE":    "$75-$175",
    # I. Emergency & After-Hours
    "EMERGENCY_WATER_SHUTOFF":  "$150-$350",
    "EMERGENCY_GAS_SHUTOFF":    "$175-$400",
    "EMERGENCY_SEWER_BACKUP":   "$350-$800",
    "FLOOD_DAMAGE_MITIGATION":  "$500-$1,500",
    "AFTER_HOURS_DIAGNOSTIC":   "$175-$375",
    # J. Maintenance & Preventive
    "PLUMBING_INSPECTION_ANNUAL":"$125-$275",
    "WINTERIZATION_SERVICE":    "$150-$350",
    "DE_WINTERIZATION_SERVICE": "$125-$275",
    "WATER_HEATER_ANNUAL_SERVICE":"$125-$250",
    "FIXTURE_CAULK_RESEAL":    "$75-$175",
    "WHOLE_HOUSE_SHUTOFF_TEST": "$95-$200",
    "HOSE_BIB_WINTERIZE":      "$45-$95/bib",

    # ── Phase 4: Construction, Commercial & Service Gap Expansion ─────────────
    # K. New Construction — Residential
    "ROUGH_IN_MASTER_BATH":     "$3,200-$6,500",
    "ROUGH_IN_SECONDARY_BATH":  "$2,000-$4,200",
    "ROUGH_IN_HALF_BATH":       "$1,200-$2,500",
    "ROUGH_IN_KITCHEN":         "$1,600-$3,200",
    "ROUGH_IN_LAUNDRY":         "$600-$1,400",
    "ROUGH_IN_OUTDOOR":         "$600-$1,400",
    "ROUGH_IN_GAS_WHOLE_HOUSE": "$2,500-$5,500",
    "ROUGH_IN_WH_LOCATION":    "$600-$1,400",
    "SEWER_TAP_CONNECTION":     "$1,500-$3,500",
    "WATER_TAP_CONNECTION":     "$1,200-$3,000",
    "FIRE_SPRINKLER_RESIDENTIAL":"$100-$225/head",
    "CONCRETE_CORE_DRILL":      "$150-$350/hole",
    "STUB_OUT_CAP_TEST":        "$250-$500",
    "FIXTURE_TRIM_OUT_FULL_BATH":"$800-$1,800",
    "SLEEVE_INSTALL_PER_PENETRATION":"$25-$65/ea",
    "MULTI_STORY_RISER_PER_FLOOR":"$1,200-$2,800/floor",
    "TANKLESS_RECIRCULATION_LOOP":"$600-$1,400",
    "SLAB_PLUMBING_LAYOUT":    "$3,500-$7,500/1000SF",
    # L. Commercial Expansion
    "COMMERCIAL_TOILET_INSTALL":"$450-$900",
    "COMMERCIAL_WALL_HUNG_TOILET":"$900-$1,800",
    "COMMERCIAL_URINAL_INSTALL":"$400-$850",
    "DRINKING_FOUNTAIN_INSTALL":"$500-$1,100",
    "EYE_WASH_STATION_INSTALL": "$700-$1,500",
    "MOP_SINK_INSTALL":         "$400-$900",
    "COMMERCIAL_DISHWASHER_HOOKUP":"$500-$1,100",
    "HANDS_FREE_FAUCET_INSTALL":"$200-$450",
    "COMMERCIAL_PRV_INSTALL":   "$500-$1,100",
    "TMV_INSTALL":              "$300-$650",
    "GREASE_INTERCEPTOR_INSTALL":"$2,500-$6,000",
    "ROOF_DRAIN_INSTALL":       "$400-$900",
    "SEWAGE_LIFT_STATION":      "$4,000-$10,000",
    "COMMERCIAL_WATER_SOFTENER":"$1,500-$3,500",
    "BACKFLOW_PREVENTER_REPAIR":"$200-$500",
    # M. Service Gaps — Water Heater & Fixtures
    "WH_DRAIN_PAN_REPLACE":    "$150-$325",
    "WH_GAS_VALVE_REPLACE":    "$250-$500",
    "TPR_VALVE_REPLACE":       "$75-$175",
    "WH_FLUE_REPAIR":          "$150-$350",
    "WHIRLPOOL_TUB_REPAIR":    "$250-$550",
    "BATHTUB_DISCONNECT_RECONNECT":"$200-$450",
    "TUB_DRAIN_ASSEMBLY_REPLACE":"$175-$375",
    "SHOWER_DRAIN_REPLACE":    "$200-$450",
    "FLOOR_DRAIN_RESIDENTIAL": "$400-$850",
    # N. Service Gaps — Valves & Backflow
    "RPZ_REBUILD":              "$250-$550",
    "DCVA_REPAIR":              "$175-$400",
    "EARTHQUAKE_VALVE_INSTALL": "$200-$450",
    "GAS_DRIP_LEG_INSTALL":    "$50-$125",
    "GATE_TO_BALL_VALVE_UPGRADE":"$75-$200/valve",
    "SUPPLY_STOP_MULTI_REPLACE":"$200-$425",
    # O. Service Gaps — Appliance Connections
    "WASHING_MACHINE_HOSE_REPLACE":"$75-$175",
    "DISHWASHER_SUPPLY_INSTALL":"$75-$175",
    "GAS_RANGE_CONNECTOR_REPLACE":"$75-$200",
    "GARBAGE_DISPOSAL_RESET_UNJAM":"$50-$125",
    # P. Service Gaps — Specialty & Emerging
    "RADIANT_FLOOR_LOOP":       "$600-$1,400",
    "HYDRONIC_HEATING_REPAIR":  "$350-$750",
    "RECLAIMED_WATER_LINE":     "$600-$1,400",
    "SEPTIC_PUMP_OUT_COORD":    "$150-$350",
    "WELL_PUMP_REPAIR":         "$350-$750",
    "WELL_PRESSURE_TANK_REPLACE":"$350-$700",
    "GREYWATER_SYSTEM_INSTALL": "$800-$2,000",
    "VANITY_PLUMBING_MODIFICATION":"$200-$450",
    "WATER_LINE_LOCATE_MARK":  "$100-$225",
    "TRAP_PRIMER_INSTALL":     "$125-$275",
    "EXPANSION_JOINT_REPAIR":  "$175-$400",
    "WATER_METER_RELOCATE":    "$300-$650",
    "CLEANOUT_INSTALL_EXTERIOR":"$350-$700",
    "SHOWER_BODY_SPRAY_INSTALL":"$250-$550/pair",
    "DUAL_FLUSH_CONVERSION":   "$50-$125",

    # ── Phase 5: Pipe Materials, Remodel, Smart, Multi-Family, Specialty ───────
    # Q. Pipe Material-Specific
    "CAST_IRON_PIPE_REPAIR":   "$300-$650",
    "CAST_IRON_SECTION_REPLACE":"$600-$1,400",
    "CAST_IRON_STACK_REPLACE": "$2,500-$6,000",
    "GALVANIZED_PIPE_REPAIR":  "$250-$550",
    "GALVANIZED_TO_PEX_SECTION":"$300-$650/run",
    "GALVANIZED_WHOLE_HOUSE_REPIPE":"$4,500-$9,000",
    "CPVC_PIPE_REPAIR":        "$175-$400",
    "CPVC_TO_PEX_SECTION":     "$225-$500/run",
    "LEAD_SERVICE_LINE_REPLACE":"$3,000-$7,000",
    "ORANGEBURG_SEWER_REPLACE":"$4,000-$9,500",
    # R. Remodel Packages
    "BATH_REMODEL_PLUMBING_STANDARD":"$1,500-$3,200",
    "BATH_REMODEL_PLUMBING_MASTER":"$2,800-$6,000",
    "KITCHEN_REMODEL_PLUMBING":"$1,500-$3,500",
    "TUB_TO_SHOWER_CONVERSION":"$1,200-$2,800",
    "SHOWER_TO_TUB_CONVERSION":"$1,200-$2,800",
    "SINGLE_TO_DOUBLE_VANITY": "$500-$1,100",
    "LAUNDRY_ROOM_RELOCATE":   "$1,000-$2,200",
    # S. Smart Plumbing & IoT
    "SMART_WATER_MONITOR_INSTALL":"$125-$275",
    "SMART_SHUTOFF_VALVE_INSTALL":"$350-$750",
    "SMART_LEAK_SENSOR_SYSTEM":"$175-$400",
    "SMART_TOILET_INSTALL":    "$350-$700",
    "TOUCHLESS_FAUCET_RESIDENTIAL":"$200-$450",
    "TANKLESS_POU_INSTALL":    "$300-$600",
    # T. Multi-Family & Condo
    "MULTIFAMILY_UNIT_SHUTOFF":"$250-$500",
    "MULTIFAMILY_RISER_REPAIR":"$600-$1,400",
    "MULTIFAMILY_STACK_REPAIR":"$1,000-$2,500",
    "CONDO_WATER_HEATER_REPLACE":"$600-$1,400",
    "SHARED_SEWER_LINE_REPAIR":"$1,200-$3,000",
    # U. Medical & Healthcare
    "MEDICAL_GAS_OUTLET_INSTALL":"$400-$900",
    "LAB_WASTE_SYSTEM":        "$2,500-$6,000",
    "DENTAL_CHAIR_PLUMBING":   "$400-$850",
    "AUTOCLAVE_PLUMBING":      "$250-$550",
    # V. Restaurant & Food Service
    "RESTAURANT_FLOOR_DRAIN_INSTALL":"$500-$1,100",
    "RESTAURANT_HANDWASH_STATION":"$350-$750",
    "THREE_COMPARTMENT_SINK_INSTALL":"$600-$1,400",
    "BAR_SINK_INSTALL":        "$400-$900",
    "ICE_MACHINE_PLUMBING":    "$200-$450",
    "COMMERCIAL_COFFEE_HOOKUP":"$175-$375",
    # W. Aging-in-Place
    "WALK_IN_TUB_INSTALL":     "$1,200-$2,800",
    "COMFORT_HEIGHT_TOILET_ADA":"$200-$450",
    "LEVER_HANDLE_CONVERSION": "$75-$175/faucet",
    "RAISED_TOILET_SEAT_PLUMBING":"$100-$225",
    "ANTI_SCALD_VALVE_RETROFIT":"$250-$550",
    # X. DFW Slab & Climate
    "SLAB_LEAK_DETECTION_FULL":"$350-$700",
    "SLAB_LEAK_TUNNEL_REPAIR": "$2,000-$5,000",
    "SLAB_LEAK_EPOXY_LINING":  "$1,500-$3,500/pipe",
    "FOUNDATION_WATERING_SYSTEM":"$500-$1,200",
    "THERMAL_PIPE_EXPANSION_FIX":"$150-$350",
    "ATTIC_PIPE_INSULATION_UPGRADE":"$300-$650",
    # Y. Tankless & WH Extended
    "TANKLESS_ERROR_DIAGNOSTIC":"$95-$200",
    "TANKLESS_VENT_INSTALL":   "$400-$900",
    "TANKLESS_CONDENSATE_DRAIN":"$125-$275",
    "WH_POWER_VENT_REPLACE":   "$1,200-$2,500",
    "WH_CONVERSION_GAS_TO_ELECTRIC":"$1,000-$2,200",
    # Z. Code Compliance & Inspection
    "PRE_INSPECTION_PREP":     "$300-$650",
    "HOME_SALE_PLUMBING_INSPECTION":"$200-$400",
    "CODE_VIOLATION_REMEDIATION":"$200-$500/issue",
    "PERMIT_CLOSURE_INSPECTION_PREP":"$200-$450",
    "WATER_CONSERVATION_AUDIT":"$150-$350",
    "CROSS_CONNECTION_SURVEY":  "$200-$450",
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
