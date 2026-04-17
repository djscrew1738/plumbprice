"""
Labor Engine — All DFW plumbing labor templates with 2025-2026 rates.
Master Plumber: $105/hr, Journeyman: $80/hr, Helper/Apprentice: $55/hr

Rate basis: DFW metro plumbing contractor survey Q1 2026, PHCC-Texas wage data,
and BLS Occupational Employment Statistics for Dallas-Fort Worth-Arlington MSA.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AccessType(str, Enum):
    FIRST_FLOOR = "first_floor"
    SECOND_FLOOR = "second_floor"
    ATTIC = "attic"
    CRAWLSPACE = "crawlspace"
    SLAB = "slab"
    BASEMENT = "basement"


class UrgencyType(str, Enum):
    STANDARD = "standard"
    SAME_DAY = "same_day"
    EMERGENCY = "emergency"


@dataclass
class LaborTemplateData:
    code: str
    name: str
    category: str  # service, construction, commercial
    base_hours: float
    lead_rate: float = 105.0  # DFW master plumber 2025-2026
    helper_required: bool = False
    helper_rate: float = 55.0
    helper_hours: Optional[float] = None
    disposal_hours: float = 0.25
    min_hours: Optional[float] = None
    max_hours: Optional[float] = None
    access_multipliers: dict = field(default_factory=lambda: {
        "first_floor": 1.0,
        "second_floor": 1.2,
        "attic": 1.5,
        "crawlspace": 1.3,
        "slab": 1.4,
        "basement": 1.1,
    })
    urgency_multipliers: dict = field(default_factory=lambda: {
        "standard": 1.0,
        "same_day": 1.35,
        "emergency": 2.0,
    })
    applicable_assemblies: list = field(default_factory=list)
    notes: str = ""

    def calculate_labor_cost(
        self,
        access: str = "first_floor",
        urgency: str = "standard",
    ) -> dict:
        """Calculate total labor cost with multipliers applied."""
        access_mult = self.access_multipliers.get(access, 1.0)
        urgency_mult = self.urgency_multipliers.get(urgency, 1.0)
        combined_mult = access_mult * urgency_mult

        adjusted_hours = self.base_hours * combined_mult
        lead_cost = adjusted_hours * self.lead_rate

        helper_cost = 0.0
        helper_hrs = 0.0
        if self.helper_required:
            helper_hrs = (self.helper_hours or self.base_hours) * combined_mult
            helper_cost = helper_hrs * self.helper_rate

        disposal_cost = self.disposal_hours * self.lead_rate

        total = lead_cost + helper_cost + disposal_cost

        return {
            "template_code": self.code,
            "base_hours": self.base_hours,
            "adjusted_hours": round(adjusted_hours, 2),
            "access_multiplier": access_mult,
            "urgency_multiplier": urgency_mult,
            "lead_rate": self.lead_rate,
            "lead_cost": round(lead_cost, 2),
            "helper_required": self.helper_required,
            "helper_hours": round(helper_hrs, 2),
            "helper_rate": self.helper_rate,
            "helper_cost": round(helper_cost, 2),
            "disposal_hours": self.disposal_hours,
            "disposal_cost": round(disposal_cost, 2),
            "total_labor_cost": round(total, 2),
        }


# ─── SERVICE TEMPLATES ────────────────────────────────────────────────────────

LABOR_TEMPLATES: dict[str, LaborTemplateData] = {

    # ── Toilet ───────────────────────────────────────────────────────────────
    "TOILET_REPLACE_STANDARD": LaborTemplateData(
        code="TOILET_REPLACE_STANDARD",
        name="Toilet Replace — Standard",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.25,
            "attic": 1.5,
            "crawlspace": 1.3,
            "slab": 1.0,
            "basement": 1.1,
        },
        applicable_assemblies=["TOILET_INSTALL_KIT"],
        notes="Includes remove & replace. Wax ring, closet bolts, supply line in kit.",
    ),

    "TOILET_INSTALL_NEW": LaborTemplateData(
        code="TOILET_INSTALL_NEW",
        name="Toilet Install — New Rough-In (no demo)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TOILET_INSTALL_KIT"],
    ),

    "TOILET_FLANGE_REPAIR": LaborTemplateData(
        code="TOILET_FLANGE_REPAIR",
        name="Toilet Flange Repair/Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.1,
        notes="Includes flange repair ring or full PVC flange replace.",
    ),

    # ── Water Heater ─────────────────────────────────────────────────────────
    "WH_50G_GAS_STANDARD": LaborTemplateData(
        code="WH_50G_GAS_STANDARD",
        name="Water Heater 50G Gas — Standard (garage/utility room)",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.5,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.2,
            "attic": 1.0,  # attic has own template
            "crawlspace": 1.4,
            "slab": 1.0,
            "basement": 1.1,
        },
        applicable_assemblies=["WH_50G_GAS_KIT"],
        notes="Includes flex lines, expansion tank, T&P valve, permit pull.",
    ),

    "WH_50G_GAS_ATTIC": LaborTemplateData(
        code="WH_50G_GAS_ATTIC",
        name="Water Heater 50G Gas — Attic Install",
        category="service",
        base_hours=4.5,
        helper_required=True,
        helper_hours=4.5,
        disposal_hours=1.0,
        access_multipliers={
            "attic": 1.0,  # base already accounts for attic
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.3, "emergency": 1.6},
        applicable_assemblies=["WH_50G_GAS_ATTIC_KIT"],
        notes="Attic install requires 2-man crew full job. Includes drain pan, overflow line.",
    ),

    "WH_40G_GAS_STANDARD": LaborTemplateData(
        code="WH_40G_GAS_STANDARD",
        name="Water Heater 40G Gas — Standard",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=0.75,
        disposal_hours=0.5,
        applicable_assemblies=["WH_40G_GAS_KIT"],
    ),

    "WH_50G_ELECTRIC_STANDARD": LaborTemplateData(
        code="WH_50G_ELECTRIC_STANDARD",
        name="Water Heater 50G Electric — Standard",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.5,
        applicable_assemblies=["WH_50G_ELECTRIC_KIT"],
        notes="Does not include electrical work. Advise customer to schedule electrician separately.",
    ),

    "WH_TANKLESS_GAS": LaborTemplateData(
        code="WH_TANKLESS_GAS",
        name="Tankless Water Heater Gas — Install",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        applicable_assemblies=["WH_TANKLESS_GAS_KIT"],
        notes="Includes gas line upgrade, recirculation line if requested. Electrical by others.",
    ),

    # ── PRV / Pressure ────────────────────────────────────────────────────────
    "PRV_REPLACE": LaborTemplateData(
        code="PRV_REPLACE",
        name="Pressure Reducing Valve Replace",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["PRV_KIT"],
        notes="Includes shutoff and fill, minor drywall access if needed.",
    ),

    "PRV_INSTALL_NEW": LaborTemplateData(
        code="PRV_INSTALL_NEW",
        name="Pressure Reducing Valve — New Install",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["PRV_KIT"],
    ),

    # ── Hose Bibs ─────────────────────────────────────────────────────────────
    "HOSE_BIB_REPLACE": LaborTemplateData(
        code="HOSE_BIB_REPLACE",
        name="Hose Bib Replace — Frost Free",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["HOSE_BIB_KIT"],
        notes="Includes minor drywall access if needed.",
    ),

    "HOSE_BIB_ADD_NEW": LaborTemplateData(
        code="HOSE_BIB_ADD_NEW",
        name="Hose Bib — New Install (existing wall)",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["HOSE_BIB_KIT"],
    ),

    # ── Shower / Tub ─────────────────────────────────────────────────────────
    "SHOWER_VALVE_REPLACE": LaborTemplateData(
        code="SHOWER_VALVE_REPLACE",
        name="Shower Valve Replace (cartridge or valve body)",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["SHOWER_VALVE_KIT"],
        notes="Price assumes access panel exists. Add 1.5hr if tile cut required.",
    ),

    "TUB_SPOUT_REPLACE": LaborTemplateData(
        code="TUB_SPOUT_REPLACE",
        name="Tub Spout Replace",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TUB_SPOUT_KIT"],
    ),

    "SHOWER_HEAD_REPLACE": LaborTemplateData(
        code="SHOWER_HEAD_REPLACE",
        name="Shower Head Replace",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["SHOWER_HEAD_KIT"],
    ),

    # ── Kitchen ───────────────────────────────────────────────────────────────
    "KITCHEN_FAUCET_REPLACE": LaborTemplateData(
        code="KITCHEN_FAUCET_REPLACE",
        name="Kitchen Faucet Replace",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["KITCHEN_FAUCET_KIT"],
    ),

    "GARBAGE_DISPOSAL_INSTALL": LaborTemplateData(
        code="GARBAGE_DISPOSAL_INSTALL",
        name="Garbage Disposal Install/Replace",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["DISPOSAL_KIT"],
        notes="Electrical connection by others unless owner-supplied outlet exists.",
    ),

    # ── Lavatory / Bath ───────────────────────────────────────────────────────
    "LAV_FAUCET_REPLACE": LaborTemplateData(
        code="LAV_FAUCET_REPLACE",
        name="Lavatory Faucet Replace",
        category="service",
        base_hours=1.25,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["LAV_FAUCET_KIT"],
    ),

    "LAV_SINK_REPLACE": LaborTemplateData(
        code="LAV_SINK_REPLACE",
        name="Lavatory Sink Replace (drop-in)",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["LAV_SINK_KIT"],
        notes="Drop-in only. Undermount adds 0.5hr. Includes new drain and supply lines.",
    ),

    # ── Angle Stops / Supply Lines ─────────────────────────────────────────────
    "ANGLE_STOP_REPLACE": LaborTemplateData(
        code="ANGLE_STOP_REPLACE",
        name="Angle Stop Valve Replace",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["ANGLE_STOP_KIT"],
    ),

    "ANGLE_STOP_REPLACE_PAIR": LaborTemplateData(
        code="ANGLE_STOP_REPLACE_PAIR",
        name="Angle Stop Pair Replace (both hot & cold)",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["ANGLE_STOP_KIT"],
    ),

    "SUPPLY_LINE_REPLACE": LaborTemplateData(
        code="SUPPLY_LINE_REPLACE",
        name="Supply Line Replace",
        category="service",
        base_hours=0.25,
        helper_required=False,
        disposal_hours=0.0,
    ),

    # ── Drain / P-Trap ────────────────────────────────────────────────────────
    "PTRAP_REPLACE": LaborTemplateData(
        code="PTRAP_REPLACE",
        name="P-Trap Replace (standard)",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["PTRAP_KIT"],
    ),

    "DRAIN_CLEAN_STANDARD": LaborTemplateData(
        code="DRAIN_CLEAN_STANDARD",
        name="Drain Cleaning — Standard (snake)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Single fixture drain; includes cable machine. Camera inspection add-on sold separately.",
    ),

    "MAIN_LINE_CLEAN": LaborTemplateData(
        code="MAIN_LINE_CLEAN",
        name="Main Line Drain Cleaning",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Includes clean-out access. Add camera if roots suspected.",
    ),

    "HYDROJETTING": LaborTemplateData(
        code="HYDROJETTING",
        name="Hydro-Jetting — Drain/Main Line",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.0,
        notes="Up to 4\" residential line. Requires clean-out access. Camera recommended before/after.",
    ),

    "SLAB_LEAK_REPAIR": LaborTemplateData(
        code="SLAB_LEAK_REPAIR",
        name="Slab Leak Repair (tunnel or open)",
        category="service",
        base_hours=7.0,
        helper_required=True,
        helper_hours=7.0,
        disposal_hours=1.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.1,
            "attic": 1.0,
            "crawlspace": 1.0,
            "slab": 1.0,
            "basement": 1.0,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 1.5},
        notes="Per repair point. Concrete cutting/patching by GC. Includes pressure test and restore.",
    ),

    "LEAK_DETECTION": LaborTemplateData(
        code="LEAK_DETECTION",
        name="Leak Detection Service",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        notes="Acoustic/electronic detection. Slab leak locating included. Written report provided.",
    ),

    "EXPANSION_TANK_ONLY": LaborTemplateData(
        code="EXPANSION_TANK_ONLY",
        name="Thermal Expansion Tank — Add-On Only",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["EXPANSION_TANK_KIT"],
        notes="For systems with check valve or PRV — required by code in DFW.",
    ),

    "WATER_SOFTENER_INSTALL": LaborTemplateData(
        code="WATER_SOFTENER_INSTALL",
        name="Water Softener Install (whole-house)",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        applicable_assemblies=["WATER_SOFTENER_KIT"],
        notes="Includes bypass valve, brine line, drain tie-in. Homeowner provides unit location.",
    ),

    "TUB_SHOWER_COMBO_REPLACE": LaborTemplateData(
        code="TUB_SHOWER_COMBO_REPLACE",
        name="Tub/Shower Combo Valve Replace",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.1,
        applicable_assemblies=["TUB_SHOWER_VALVE_KIT"],
        notes="Includes diverter valve and trim. Access panel assumed. Add 1.5hr for tile cut.",
    ),

    # ── Gas Lines ─────────────────────────────────────────────────────────────
    "GAS_LINE_REPAIR_MINOR": LaborTemplateData(
        code="GAS_LINE_REPAIR_MINOR",
        name="Gas Line Repair — Minor (fitting/valve)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        notes="Includes pressure test and relight.",
    ),

    "GAS_LINE_NEW_RUN": LaborTemplateData(
        code="GAS_LINE_NEW_RUN",
        name="Gas Line — New Run (per 25 ft)",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
        notes="CSST or black iron per local code. Includes pressure test and permit. Price per 25-ft run.",
    ),

    "GAS_SHUTOFF_REPLACE": LaborTemplateData(
        code="GAS_SHUTOFF_REPLACE",
        name="Gas Shutoff Valve Replace",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_SHUTOFF_KIT"],
    ),

    # ── Common Repair Calls ───────────────────────────────────────────────────
    "TOILET_FLAPPER_REPLACE": LaborTemplateData(
        code="TOILET_FLAPPER_REPLACE",
        name="Toilet Flapper Replace (running toilet)",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TOILET_FLAPPER_KIT"],
        notes="Most common service call. Includes inspect fill valve and adjust float.",
    ),

    "TOILET_FILL_VALVE_REPLACE": LaborTemplateData(
        code="TOILET_FILL_VALVE_REPLACE",
        name="Toilet Fill Valve Replace",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TOILET_FILL_VALVE_KIT"],
        notes="Includes flush and leak check. Recommend replacing flapper at same time.",
    ),

    "TOILET_COMFORT_HEIGHT": LaborTemplateData(
        code="TOILET_COMFORT_HEIGHT",
        name="Comfort Height Toilet Replace (ADA/tall)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.25,
            "attic": 1.5,
            "crawlspace": 1.3,
            "slab": 1.0,
            "basement": 1.1,
        },
        applicable_assemblies=["TOILET_COMFORT_HEIGHT_KIT"],
        notes="Same labor as standard. Comfort height (17–19\") for ADA or tall users.",
    ),

    "CLEAN_OUT_INSTALL": LaborTemplateData(
        code="CLEAN_OUT_INSTALL",
        name="Clean-Out Install — 4\" ABS/PVC",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.25,
        applicable_assemblies=["CLEAN_OUT_KIT"],
        notes="Required before main line cleaning if no clean-out present. Includes concrete saw if slab.",
    ),

    "CAMERA_INSPECTION": LaborTemplateData(
        code="CAMERA_INSPECTION",
        name="Drain Camera Inspection",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Full line video inspection with recording. Locating mark-out included.",
    ),


    # ─────────────────────────────────────────────────────────────────────────
    # NEW CONSTRUCTION TEMPLATES
    # ─────────────────────────────────────────────────────────────────────────

    "ROUGH_IN_PER_BATH_GROUP": LaborTemplateData(
        code="ROUGH_IN_PER_BATH_GROUP",
        name="Rough-In — Per Bath Group",
        category="construction",
        base_hours=16.0,  # per bath group
        helper_required=True,
        helper_hours=16.0,
        disposal_hours=0.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.0, "emergency": 1.0},
        notes="Bath group = toilet + lav + tub/shower. Base includes DWV + water supply rough.",
    ),

    "TOP_OUT_PER_FIXTURE": LaborTemplateData(
        code="TOP_OUT_PER_FIXTURE",
        name="Top-Out — Per Fixture Unit",
        category="construction",
        base_hours=3.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.0, "emergency": 1.0},
    ),

    "FINAL_SET_PER_FIXTURE": LaborTemplateData(
        code="FINAL_SET_PER_FIXTURE",
        name="Final Set — Per Fixture",
        category="construction",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
    ),

    "UNDERGROUND_PER_LF": LaborTemplateData(
        code="UNDERGROUND_PER_LF",
        name="Underground Drain — Per Linear Foot",
        category="construction",
        base_hours=0.15,  # per LF
        helper_required=True,
        helper_hours=0.15,
        disposal_hours=0.0,
        notes="Includes trench, pipe, and backfill. Excavation by GC if rock.",
    ),

    "METER_SET": LaborTemplateData(
        code="METER_SET",
        name="Meter Set / Service Connection",
        category="construction",
        base_hours=4.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.0,
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # COMMERCIAL TEMPLATES
    # ─────────────────────────────────────────────────────────────────────────

    "ADA_RESTROOM_ROUGH_IN": LaborTemplateData(
        code="ADA_RESTROOM_ROUGH_IN",
        name="ADA Restroom Rough-In (per fixture)",
        category="commercial",
        base_hours=5.0,
        helper_required=True,
        helper_hours=5.0,
        disposal_hours=0.0,
        notes="Includes floor-mounted water closet carrier, wall-hung lav.",
    ),

    "COMMERCIAL_SINK_INSTALL": LaborTemplateData(
        code="COMMERCIAL_SINK_INSTALL",
        name="Commercial Sink Install (stainless, 3-comp)",
        category="commercial",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
    ),

    "BACKFLOW_PREVENTER_INSTALL": LaborTemplateData(
        code="BACKFLOW_PREVENTER_INSTALL",
        name="Backflow Preventer — Install/Test",
        category="commercial",
        base_hours=4.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Includes annual test certification filing.",
    ),

    # ── Repipe (DFW high-demand — 1960s-80s galvanized/polybutylene homes) ───
    "WHOLE_HOUSE_REPIPE_PEX": LaborTemplateData(
        code="WHOLE_HOUSE_REPIPE_PEX",
        name="Whole House Repipe — PEX-A (per fixture point)",
        category="service",
        base_hours=1.5,          # per fixture point (water outlet/fixture connection)
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,      # disposal billed separately as flat per job
        access_multipliers={
            "first_floor":  1.0,
            "second_floor": 1.2,
            "attic":        1.4,
            "crawlspace":   1.5,
            "slab":         1.8,  # slab homes require tunneling/trenching
            "basement":     1.1,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.2, "emergency": 1.5},
        applicable_assemblies=["WHOLE_HOUSE_REPIPE_PEX_KIT"],
        notes=(
            "Quoted per fixture point (each hot/cold outlet). "
            "Average DFW home: 12-18 fixture points. "
            "Permit required in all DFW counties — add PERMIT_REPIPE line. "
            "Drywall repair NOT included; recommend subcontractor."
        ),
    ),

    # ── Sewer spot repair (common DFW root intrusion / bellied line) ─────────
    "SEWER_SPOT_REPAIR": LaborTemplateData(
        code="SEWER_SPOT_REPAIR",
        name="Sewer Line Spot Repair (excavate & replace section)",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=0.5,
        access_multipliers={
            "first_floor":  1.0,   # front/back yard standard
            "second_floor": 1.0,
            "attic":        1.0,
            "crawlspace":   1.0,
            "slab":         2.2,   # slab requires saw-cutting, tunneling, restore
            "basement":     1.4,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 1.65},
        applicable_assemblies=["SEWER_SPOT_KIT"],
        notes=(
            "Includes excavation up to 4ft depth, 5ft section replace, backfill. "
            "Deeper excavation or longer runs are extra. "
            "Camera inspection recommended before pricing — see CAMERA_INSPECTION. "
            "Slab repair: tunneling billed at 2.2x; concrete restore NOT included."
        ),
    ),

    # ── Recirculation pump (very common in large DFW homes) ──────────────────
    "RECIRC_PUMP_INSTALL": LaborTemplateData(
        code="RECIRC_PUMP_INSTALL",
        name="Hot Water Recirculation Pump Install",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor":  1.0,
            "second_floor": 1.1,
            "attic":        1.4,
            "crawlspace":   1.3,
            "slab":         1.0,
            "basement":     1.1,
        },
        applicable_assemblies=["RECIRC_PUMP_KIT"],
        notes=(
            "Grundfos UP15-10SU7P or equivalent. "
            "Includes pump, timer/controller, and supply line connections. "
            "Does NOT include dedicated return line — comfort valve system assumed. "
            "Electrical outlet at water heater required (verify before quoting)."
        ),
    ),

    # ── Dishwasher / appliance hookup ─────────────────────────────────────────
    "DISHWASHER_HOOKUP": LaborTemplateData(
        code="DISHWASHER_HOOKUP",
        name="Dishwasher Supply & Drain Hookup",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor":  1.0,
            "second_floor": 1.1,
            "attic":        1.0,
            "crawlspace":   1.0,
            "slab":         1.0,
            "basement":     1.0,
        },
        applicable_assemblies=["DISHWASHER_KIT"],
        notes="Includes SS supply line, drain hose, high-loop or air gap. Electrical NOT included.",
    ),

    # ── Water main shutoff / main line repair ─────────────────────────────────
    "WATER_MAIN_REPAIR": LaborTemplateData(
        code="WATER_MAIN_REPAIR",
        name="Water Main Shutoff Valve Repair/Replace",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.25,
        access_multipliers={
            "first_floor":  1.0,
            "second_floor": 1.0,
            "attic":        1.0,
            "crawlspace":   1.3,
            "slab":         1.6,   # slab requires locating and exposing main
            "basement":     1.2,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.35, "emergency": 1.75},
        applicable_assemblies=["WATER_MAIN_KIT"],
        notes=(
            "Includes ball valve replacement on main shutoff or meter angle stop. "
            "City curb stop operation NOT included — contact water utility. "
            "If main line is leaking underground, camera/locate billed separately."
        ),
    ),

    # ─── Water Heater Repair Templates ────────────────────────────────────────
    "WH_REPAIR_GAS": LaborTemplateData(
        code="WH_REPAIR_GAS",
        name="Water Heater Repair — Gas (thermocouple/pilot/valve)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WH_REPAIR_GAS_KIT"],
        notes=(
            "Covers thermocouple replacement, pilot assembly, gas valve, or T&P valve. "
            "DFW hard water accelerates thermocouple failure. "
            "If repair fails diagnosis, upsell to full WH replacement."
        ),
    ),

    "WH_ELEMENT_REPLACE": LaborTemplateData(
        code="WH_ELEMENT_REPLACE",
        name="Water Heater Element Replacement (Electric)",
        category="service",
        base_hours=1.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WH_ELEMENT_KIT"],
        notes=(
            "Upper or lower element replacement on electric tank water heater. "
            "Includes drain/flush to access. Check anode rod while in there."
        ),
    ),

    "WH_FLUSH_MAINTENANCE": LaborTemplateData(
        code="WH_FLUSH_MAINTENANCE",
        name="Water Heater Flush & Maintenance",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Annual sediment flush + inspection. DFW water hardness (15–20 GPG) causes rapid scale. "
            "Recommend upsell to water softener if sediment is heavy."
        ),
    ),

    "WH_ANODE_REPLACE": LaborTemplateData(
        code="WH_ANODE_REPLACE",
        name="Water Heater Anode Rod Replacement",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["ANODE_ROD_KIT"],
        notes=(
            "DFW hard water depletes magnesium anode rods 2–3× faster than national average. "
            "Recommend every 3 years. Extends tank life significantly."
        ),
    ),

    # ─── Toilet Repair Templates ───────────────────────────────────────────────
    "TOILET_TANK_REBUILD": LaborTemplateData(
        code="TOILET_TANK_REBUILD",
        name="Toilet Tank Full Rebuild",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TOILET_REBUILD_KIT"],
        notes="Flapper + fill valve + handle + overflow tube. Stops running/phantom flush. Very common call.",
    ),

    "TOILET_SEAT_REPLACE": LaborTemplateData(
        code="TOILET_SEAT_REPLACE",
        name="Toilet Seat Replacement",
        category="service",
        base_hours=0.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TOILET_SEAT_KIT"],
        notes="Quick seat swap. If elongated vs round mismatch exists, measure before ordering.",
    ),

    "TOILET_WAX_RING_ONLY": LaborTemplateData(
        code="TOILET_WAX_RING_ONLY",
        name="Toilet Wax Ring Replacement (reset only — keep existing toilet)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WAX_RING_RESET_KIT"],
        notes=(
            "Pull toilet, replace wax ring (and closet bolts if corroded), reset. "
            "Inspect flange — if cracked, add TOILET_FLANGE_REPAIR to quote."
        ),
    ),

    # ─── Faucet Repair Template ────────────────────────────────────────────────
    "FAUCET_CARTRIDGE_REPAIR": LaborTemplateData(
        code="FAUCET_CARTRIDGE_REPAIR",
        name="Faucet Cartridge Replacement",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["CARTRIDGE_KIT"],
        notes=(
            "Pull and replace cartridge only; keep existing faucet. "
            "DFW hard water causes cartridge failure within 3–5 years. "
            "If valve body is pitted/cracked, upsell to full faucet replacement."
        ),
    ),

    # ─── Slab Leak Reroute ─────────────────────────────────────────────────────
    "SLAB_LEAK_REROUTE": LaborTemplateData(
        code="SLAB_LEAK_REROUTE",
        name="Slab Leak Reroute — Attic/Wall Bypass",
        category="service",
        base_hours=8.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=0.5,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.15,
            "attic": 1.05,
            "crawlspace": 1.0,
            "slab": 1.0,
            "basement": 1.0,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.35, "emergency": 2.0},
        applicable_assemblies=["SLAB_REROUTE_KIT"],
        notes=(
            "Reroute supply line through attic or wall instead of tunneling. "
            "DFW insurers increasingly prefer reroute over tunneling (avoids foundation disturbance). "
            "Includes isolation, new PEX run, access panel install. Permit required."
        ),
    ),

    # ─── Backflow & Gas Test ───────────────────────────────────────────────────
    "BACKFLOW_TEST_ANNUAL": LaborTemplateData(
        code="BACKFLOW_TEST_ANNUAL",
        name="Backflow Preventer Annual Test & Certification",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Required annually for commercial irrigation, medical, and food service. "
            "Technician must be TCEQ-certified backflow tester. "
            "Failing test: add BACKFLOW_PREVENTER_REPAIR or BACKFLOW_PREVENTER_INSTALL."
        ),
    ),

    "GAS_PRESSURE_TEST": LaborTemplateData(
        code="GAS_PRESSURE_TEST",
        name="Gas Line Pressure Test (stand-alone)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Required by permit office after any gas line work. "
            "Includes pressure gauge hookup, hold test, documentation for inspector. "
            "If test fails: diagnose leak and add GAS_LINE_REPAIR_MINOR to quote."
        ),
    ),

    # ─── Water Supply Line Repair ──────────────────────────────────────────────
    "WATER_LINE_REPAIR_MINOR": LaborTemplateData(
        code="WATER_LINE_REPAIR_MINOR",
        name="Water Supply Line Repair (pinhole / joint failure)",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WATER_LINE_REPAIR_KIT"],
        notes=(
            "Repair isolated supply line failure: pinhole leak, failed compression fitting, "
            "or corroded section. Includes pipe exposure (drywall cut not included). "
            "If galvanized or > 3 ft affected, upsell to repipe section."
        ),
    ),

    # ─── Outdoor / Yard Drain ─────────────────────────────────────────────────
    "OUTDOOR_DRAIN_INSTALL": LaborTemplateData(
        code="OUTDOOR_DRAIN_INSTALL",
        name="Outdoor French / Yard Drain Installation (per 10 LF)",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=2.5,
        disposal_hours=0.5,
        applicable_assemblies=["OUTDOOR_DRAIN_KIT"],
        notes=(
            "Per 10 linear feet of French drain. DFW clay soil causes drainage failure in yards. "
            "Includes trench, perforated pipe, filter fabric wrap, gravel bed, pop-up emitter. "
            "Scale hours proportionally (e.g., 30 LF = 3× base)."
        ),
    ),

    "DRAIN_CLEAN_KITCHEN": LaborTemplateData(
        code="DRAIN_CLEAN_KITCHEN",
        name="Kitchen Drain Cleaning (grease/buildup)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Grease-loaded kitchen drain; often needs enzyme follow-up. If P-trap fully blocked, replace. DFW restaurants: use HYDROJETTING.",
    ),

    "DRAIN_CLEAN_BATHTUB": LaborTemplateData(
        code="DRAIN_CLEAN_BATHTUB",
        name="Bathtub Drain Cleaning",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        notes="Trip lever or basket strainer hair clog. If drain is broken, add BATHTUB_DRAIN_REPAIR.",
    ),

    "DRAIN_CLEAN_SHOWER": LaborTemplateData(
        code="DRAIN_CLEAN_SHOWER",
        name="Shower Drain Cleaning",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        notes="Hair/soap clog at shower drain cover. If linear drain is blocked, may need pull and clean.",
    ),

    "TOILET_AUGER_SERVICE": LaborTemplateData(
        code="TOILET_AUGER_SERVICE",
        name="Toilet Auger / Closet Snake Service",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        notes="Closet auger for toilet clog. Foreign object retrieval may require removal -- add TOILET_WAX_RING_ONLY to quote.",
    ),

    "TANKLESS_WH_DESCALE": LaborTemplateData(
        code="TANKLESS_WH_DESCALE",
        name="Tankless Water Heater Descale / Flush",
        category="service",
        base_hours=1.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TANKLESS_DESCALE_KIT"],
        notes="DFW hard water (15-20 GPG) requires annual descale. Includes vinegar/descale solution flush through heat exchanger. Check filter screen.",
    ),

    "EXPANSION_TANK_INSTALL": LaborTemplateData(
        code="EXPANSION_TANK_INSTALL",
        name="Water Heater Expansion Tank Install",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["EXPANSION_TANK_KIT"],
        notes="Required by Dallas/Tarrant code when PRV is present (closed system). Charge to match system pressure before install.",
    ),

    "WATER_HAMMER_ARRESTER": LaborTemplateData(
        code="WATER_HAMMER_ARRESTER",
        name="Water Hammer Arrestor Install",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["HAMMER_ARRESTER_KIT"],
        notes="Install at washing machine, dishwasher, or high-velocity fixture. Size to ASSE 1010 standard. DFW high pressure areas (75+ PSI) see this frequently.",
    ),

    "LAUNDRY_BOX_REPLACE": LaborTemplateData(
        code="LAUNDRY_BOX_REPLACE",
        name="Laundry / Washing Machine Outlet Box Replace",
        category="service",
        base_hours=1.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["LAUNDRY_BOX_KIT"],
        notes="Recessed washer outlet box with hot/cold and standpipe drain. Includes valve replacement. Very common in DFW pre-2000 homes.",
    ),

    "ICE_MAKER_LINE_INSTALL": LaborTemplateData(
        code="ICE_MAKER_LINE_INSTALL",
        name="Refrigerator Ice Maker Line Install",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["ICE_MAKER_KIT"],
        notes='1/4" supply line from angle stop under sink or in wall to fridge. PEX preferred over poly.',
    ),

    "MIXING_VALVE_REPLACE": LaborTemplateData(
        code="MIXING_VALVE_REPLACE",
        name="Thermostatic Mixing Valve Replacement",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["MIXING_VALVE_KIT"],
        notes="Tempering/mixing valve on WH outlet. Required by IRC for care facilities; common on WH with 140F setting.",
    ),

    "SHOWER_VALVE_CARTRIDGE": LaborTemplateData(
        code="SHOWER_VALVE_CARTRIDGE",
        name="Shower/Tub Valve Cartridge Replacement",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["SHOWER_CARTRIDGE_KIT"],
        notes="Moen Posi-Temp, Delta Monitor, or Kohler Rite-Temp cartridge. If valve body is corroded, upsell to SHOWER_VALVE_REPLACE.",
    ),

    "BATHTUB_DRAIN_REPAIR": LaborTemplateData(
        code="BATHTUB_DRAIN_REPAIR",
        name="Bathtub Drain Assembly Repair",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TUB_DRAIN_KIT"],
        notes="Trip lever, basket strainer, or overflow plate replacement. Includes stopper mechanism. If drain is leaking into framing, inspect subfloor.",
    ),

    "SINK_REPLACE_KITCHEN": LaborTemplateData(
        code="SINK_REPLACE_KITCHEN",
        name="Kitchen Sink Replacement (drop-in or undermount)",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        applicable_assemblies=["KITCHEN_SINK_KIT"],
        notes="Includes disconnect/reconnect supply & drain, P-trap, basket strainer. Countertop cut (if needed) is extra. Undermount requires silicone cure time -- 2-visit job.",
    ),

    "SINK_REPLACE_BATH": LaborTemplateData(
        code="SINK_REPLACE_BATH",
        name="Bathroom Vanity / Lavatory Sink Replacement",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["BATH_SINK_KIT"],
        notes="Drop-in vanity sink or pedestal lav. Includes pop-up drain, P-trap, supply lines. If faucet is also being replaced, bundle with LAV_FAUCET_REPLACE.",
    ),

    "GARBAGE_DISPOSAL_REPAIR": LaborTemplateData(
        code="GARBAGE_DISPOSAL_REPAIR",
        name="Garbage Disposal Repair (reset/jam clear)",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        notes="Reset tripped breaker, clear jam with hex key, test. If motor hums but does not run, disposal is failed -- upsell to GARBAGE_DISPOSAL_INSTALL.",
    ),

    "HOSE_BIB_FREEZE_REPAIR": LaborTemplateData(
        code="HOSE_BIB_FREEZE_REPAIR",
        name="Hose Bib / Sillcock Freeze/Burst Repair",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["HOSE_BIB_FREEZE_KIT"],
        notes="Cut and replace burst sillcock. DFW freezes are rare but 2021 Uri storm created massive demand. Upgrade to frost-free sillcock.",
    ),

    "PRESSURE_TEST_SYSTEM": LaborTemplateData(
        code="PRESSURE_TEST_SYSTEM",
        name="Whole-House Plumbing Pressure Test",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        notes="Cap all fixtures, pressurize to 80 PSI, 30-minute hold test. Required for permit close-out on repipe. Also used for leak detection pre-investigation.",
    ),

    "LAUNDRY_DRAIN_INSTALL": LaborTemplateData(
        code="LAUNDRY_DRAIN_INSTALL",
        name="Laundry Standpipe & Drain Install",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        notes='2" standpipe (min 18" height), P-trap, tie-in to drain line. Required when laundry room is relocated or added.',
    ),

    "SUMP_PUMP_INSTALL": LaborTemplateData(
        code="SUMP_PUMP_INSTALL",
        name="Sump Pump Installation",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.25,
        applicable_assemblies=["SUMP_PUMP_KIT"],
        notes="Less common in DFW (no basements) but used in low-lying areas and crawl spaces. Includes basin, pump, check valve, discharge line. Electrical by others.",
    ),

    "SHOWER_PAN_REPLACE": LaborTemplateData(
        code="SHOWER_PAN_REPLACE",
        name="Shower Pan / Base Replacement (fiberglass/acrylic)",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=1.0,
        notes="Remove old pan, inspect subfloor, install new acrylic base, reconnect drain. Tile work not included. If subfloor is rotted, add subfloor repair to scope.",
    ),

    # ─── New High-Demand DFW Templates ───────────────────────────────────────
    "RO_SYSTEM_INSTALL": LaborTemplateData(
        code="RO_SYSTEM_INSTALL",
        name="Reverse Osmosis System — Under Sink",
        category="service",
        base_hours=2.0,
        helper_required=False,
        applicable_assemblies=["RO_SYSTEM_KIT"],
        notes="Includes faucet mount (stone hole drill extra), tank, and drain tie-in.",
    ),

    "FILTRATION_WHOLE_HOUSE": LaborTemplateData(
        code="FILTRATION_WHOLE_HOUSE",
        name="Whole House Water Filtration System",
        category="service",
        base_hours=3.5,
        helper_required=True,
        helper_hours=1.5,
        applicable_assemblies=["WHOLE_HOUSE_FILTER_KIT"],
        notes="Includes bypass loop and sediment pre-filter. DFW city water treatment.",
    ),

    "SEWER_LINE_REPLACE_FULL": LaborTemplateData(
        code="SEWER_LINE_REPLACE_FULL",
        name="Sewer Main Line Replacement (Yard — per 50 LF)",
        category="service",
        base_hours=12.0,
        helper_required=True,
        helper_hours=12.0,
        disposal_hours=1.0,
        applicable_assemblies=["SEWER_LINE_FULL_KIT"],
        notes="Includes excavation, 4\" SCH40 PVC, cleanouts, and backfill. Grass/landscape restore extra.",
    ),

    "URINAL_FLUSH_VALVE_REPLACE": LaborTemplateData(
        code="URINAL_FLUSH_VALVE_REPLACE",
        name="Commercial Urinal Flush Valve Replace",
        category="commercial",
        base_hours=1.25,
        helper_required=False,
        applicable_assemblies=["URINAL_VALVE_KIT"],
        notes="Sloan/Zurn manual or sensor valve. Includes shutoff and adjustment.",
    ),

    "BIDET_SEAT_INSTALL": LaborTemplateData(
        code="BIDET_SEAT_INSTALL",
        name="Bidet Seat / Washlet Installation",
        category="service",
        base_hours=0.75,
        helper_required=False,
        applicable_assemblies=["BIDET_SEAT_KIT"],
        notes="Requires GFI outlet by others. Includes T-valve and seat mounting.",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # EXPANDED DFW PRICING — 2025-2026 ADDITIONS
    # ─────────────────────────────────────────────────────────────────────────

    # ── Water Heater Additions ───────────────────────────────────────────────

    "WH_50G_ELECTRIC_ATTIC": LaborTemplateData(
        code="WH_50G_ELECTRIC_ATTIC",
        name="Water Heater 50G Electric — Attic Install",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=1.0,
        access_multipliers={"attic": 1.0},
        urgency_multipliers={"standard": 1.0, "same_day": 1.3, "emergency": 1.6},
        applicable_assemblies=["WH_50G_ELECTRIC_ATTIC_KIT"],
        notes="Electric WH attic pull. Requires 2-man crew. Drain pan + overflow mandatory. Electrical by others.",
    ),

    "WH_TANKLESS_ELECTRIC": LaborTemplateData(
        code="WH_TANKLESS_ELECTRIC",
        name="Tankless Water Heater Electric — Install",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        applicable_assemblies=["WH_TANKLESS_ELECTRIC_KIT"],
        notes="Requires 200A panel with dedicated breaker(s). Electrical by others. No gas line needed.",
    ),

    "WH_HYBRID_HEAT_PUMP": LaborTemplateData(
        code="WH_HYBRID_HEAT_PUMP",
        name="Hybrid Heat Pump Water Heater — Install",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        applicable_assemblies=["WH_HYBRID_HEAT_PUMP_KIT"],
        notes=(
            "Rheem ProTerra or AO Smith HPA. Needs 7ft ceiling clearance and conditioned space. "
            "DFW Energy Star rebates may apply. Electrical 240V by others. "
            "Condensate drain required — tie into existing drain or install new."
        ),
    ),

    "WH_RECIRCULATION_LINE_NEW": LaborTemplateData(
        code="WH_RECIRCULATION_LINE_NEW",
        name="Dedicated Hot Water Return Line — New Install",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.3,
            "attic": 1.1,
            "crawlspace": 1.4,
            "slab": 1.8,
            "basement": 1.1,
        },
        applicable_assemblies=["WH_RECIRC_LINE_KIT"],
        notes=(
            "Full dedicated return line from furthest fixture back to WH. "
            "DFW large homes (3,000+ sqft) often need this for instant hot water. "
            "Includes pump, controller, and insulated PEX return line."
        ),
    ),

    "WH_PAN_DRAIN_OVERFLOW_ONLY": LaborTemplateData(
        code="WH_PAN_DRAIN_OVERFLOW_ONLY",
        name="Water Heater Drain Pan & Overflow — Standalone",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WH_PAN_KIT"],
        notes="Standalone drain pan and CPVC overflow install. Required by DFW code for attic/2nd floor WH.",
    ),

    # ── Drain & Sewer Additions ──────────────────────────────────────────────

    "DRAIN_CLEAN_FLOOR": LaborTemplateData(
        code="DRAIN_CLEAN_FLOOR",
        name="Floor Drain Cleaning (garage/laundry/basement)",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        notes="Garage or laundry floor drain. Sediment/debris removal. DFW clay soil causes frequent floor drain backup.",
    ),

    "DRAIN_CLEAN_MAIN_HYDRO_COMBO": LaborTemplateData(
        code="DRAIN_CLEAN_MAIN_HYDRO_COMBO",
        name="Main Line Snake + Hydro-Jet Combo Service",
        category="service",
        base_hours=3.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
        notes=(
            "Main line cable machine followed by hydro-jetting for thorough root/grease removal. "
            "Most effective for DFW root intrusion (live oak, hackberry). "
            "Camera inspection recommended after to verify clear."
        ),
    ),

    "SEWER_CAMERA_LOCATOR": LaborTemplateData(
        code="SEWER_CAMERA_LOCATOR",
        name="Sewer Camera + Locator Mark-Out",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        notes=(
            "Full video inspection with sonde locator. Mark depth/location on surface with paint. "
            "Required before any DFW sewer repair for permit. Written report with screenshots."
        ),
    ),

    "SEWER_LINER_CIPP": LaborTemplateData(
        code="SEWER_LINER_CIPP",
        name="Trenchless Sewer Liner — CIPP (per 50 LF)",
        category="service",
        base_hours=8.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=0.5,
        urgency_multipliers={"standard": 1.0, "same_day": 1.2, "emergency": 1.4},
        applicable_assemblies=["SEWER_LINER_KIT"],
        notes=(
            "Cured-in-place pipe lining. No excavation — preserves landscape. "
            "DFW clay soil makes this attractive vs open-cut. "
            "Per 50 LF section. Requires camera before and after. UV or ambient cure."
        ),
    ),

    "SEWER_BELLY_REPAIR": LaborTemplateData(
        code="SEWER_BELLY_REPAIR",
        name="Sewer Belly / Sag Repair (excavate & regrade)",
        category="service",
        base_hours=8.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=1.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.0,
            "attic": 1.0,
            "crawlspace": 1.0,
            "slab": 2.0,
            "basement": 1.4,
        },
        urgency_multipliers={"standard": 1.0, "same_day": 1.2, "emergency": 1.5},
        applicable_assemblies=["SEWER_BELLY_KIT"],
        notes=(
            "DFW expansive clay soil causes sewer bellies (sags) that trap debris. "
            "Excavate, regrade bedding, replace pipe section, compact backfill. "
            "Deeper than 4ft or under driveways adds significant labor."
        ),
    ),

    "DRAIN_POP_UP_REPLACE": LaborTemplateData(
        code="DRAIN_POP_UP_REPLACE",
        name="Lavatory Pop-Up Drain Assembly Replace",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["POP_UP_DRAIN_KIT"],
        notes="Replace pop-up stopper mechanism, pivot rod, and tailpiece if corroded.",
    ),

    "CONDENSATE_DRAIN_INSTALL": LaborTemplateData(
        code="CONDENSATE_DRAIN_INSTALL",
        name="HVAC Condensate Drain Line — Plumbing Tie-In",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["CONDENSATE_DRAIN_KIT"],
        notes=(
            "PVC condensate drain from HVAC unit to plumbing drain or exterior. "
            "DFW code requires indirect waste connection with air gap. "
            "Includes P-trap, cleanout tee, and safety pan if attic."
        ),
    ),

    # ── Fixture Install/Repair Additions ─────────────────────────────────────

    "BIDET_STANDALONE_INSTALL": LaborTemplateData(
        code="BIDET_STANDALONE_INSTALL",
        name="Standalone Bidet — Full Install",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.25,
        applicable_assemblies=["BIDET_STANDALONE_KIT"],
        notes="Full floor-mount bidet. Requires hot/cold supply and dedicated drain. Rough-in must be present.",
    ),

    "PEDESTAL_SINK_INSTALL": LaborTemplateData(
        code="PEDESTAL_SINK_INSTALL",
        name="Pedestal Sink Install/Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["PEDESTAL_SINK_KIT"],
        notes="Includes wall mount bracket, supply lines, P-trap. Wall blocking required for support.",
    ),

    "UNDERMOUNT_SINK_INSTALL": LaborTemplateData(
        code="UNDERMOUNT_SINK_INSTALL",
        name="Undermount Sink Install (kitchen or bath)",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        applicable_assemblies=["UNDERMOUNT_SINK_KIT"],
        notes=(
            "Undermount requires silicone cure time — 2-visit job. "
            "First visit: set sink, connect temporary. Second visit: final connect after 24hr cure. "
            "Countertop cutout by GC if needed."
        ),
    ),

    "FREESTANDING_TUB_INSTALL": LaborTemplateData(
        code="FREESTANDING_TUB_INSTALL",
        name="Freestanding Tub — Plumbing Rough & Set",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.5,
        applicable_assemblies=["FREESTANDING_TUB_KIT"],
        notes=(
            "Floor-mount tub filler + drain for freestanding tub. "
            "DFW luxury market demand. Requires floor access for drain repositioning. "
            "Tub filler rough-in and trim included. Tub unit NOT included."
        ),
    ),

    "WALK_IN_SHOWER_VALVE_INSTALL": LaborTemplateData(
        code="WALK_IN_SHOWER_VALVE_INSTALL",
        name="Walk-In Shower Multi-Valve System Install",
        category="service",
        base_hours=5.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.25,
        applicable_assemblies=["WALK_IN_SHOWER_KIT"],
        notes=(
            "Thermostatic valve + diverter + body sprays (2-4) + rain head. "
            "DFW luxury remodel staple. Requires 3/4\" supply for adequate flow. "
            "Tile/glass work NOT included."
        ),
    ),

    "WET_BAR_SINK_INSTALL": LaborTemplateData(
        code="WET_BAR_SINK_INSTALL",
        name="Wet Bar Sink — New Install",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WET_BAR_SINK_KIT"],
        notes=(
            "Small bar sink with faucet, drain, and supply lines. "
            "Common DFW entertaining upgrade. Includes PEX stub-out from nearest supply."
        ),
    ),

    "UTILITY_SINK_INSTALL": LaborTemplateData(
        code="UTILITY_SINK_INSTALL",
        name="Utility / Laundry Tub Sink — Install",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["UTILITY_SINK_KIT"],
        notes="Freestanding laundry/garage utility tub. Includes faucet, drain tie-in, supply lines.",
    ),

    "POT_FILLER_INSTALL": LaborTemplateData(
        code="POT_FILLER_INSTALL",
        name="Pot Filler Faucet — Wall Mount Install",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.2,
            "attic": 1.0,
            "crawlspace": 1.0,
            "slab": 1.0,
            "basement": 1.0,
        },
        applicable_assemblies=["POT_FILLER_KIT"],
        notes=(
            "Wall-mount articulated pot filler above range. "
            "Requires cold water stub-out behind tile/backsplash. "
            "DFW kitchen remodel add-on. Tile repair NOT included."
        ),
    ),

    # ── Pipe Repair & Leak Additions ─────────────────────────────────────────

    "COPPER_PINHOLE_REPAIR": LaborTemplateData(
        code="COPPER_PINHOLE_REPAIR",
        name="Copper Pinhole Leak Repair (per repair)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.2,
            "attic": 1.4,
            "crawlspace": 1.3,
            "slab": 1.8,
            "basement": 1.1,
        },
        applicable_assemblies=["COPPER_REPAIR_KIT"],
        notes=(
            "DFW aggressive water chemistry causes copper pitting/pinhole leaks. "
            "Per repair point — cut out section, solder or ProPress coupling. "
            "If multiple pinholes found, recommend repipe evaluation."
        ),
    ),

    "POLYBUTYLENE_SECTION_REPLACE": LaborTemplateData(
        code="POLYBUTYLENE_SECTION_REPLACE",
        name="Polybutylene Pipe Section Replace (per section)",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        access_multipliers={
            "first_floor": 1.0,
            "second_floor": 1.2,
            "attic": 1.3,
            "crawlspace": 1.4,
            "slab": 1.6,
            "basement": 1.1,
        },
        applicable_assemblies=["POLY_B_REPAIR_KIT"],
        notes=(
            "Replace failed poly-B section with PEX-A transition. "
            "DFW has thousands of 1980s poly-B homes. Per section — if multiple failures, upsell whole-house repipe."
        ),
    ),

    "PIPE_BURST_EMERGENCY": LaborTemplateData(
        code="PIPE_BURST_EMERGENCY",
        name="Burst Pipe Emergency Response & Repair",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        urgency_multipliers={"standard": 1.0, "same_day": 1.5, "emergency": 2.0},
        applicable_assemblies=["PIPE_BURST_KIT"],
        notes=(
            "Emergency shutoff, water extraction assist, pipe repair. "
            "DFW freeze events (2021 Uri, 2022, 2024) create surge demand. "
            "Includes temporary clamp + permanent repair. Drywall/floor repair NOT included."
        ),
    ),

    "FREEZE_DAMAGE_THAW_REPAIR": LaborTemplateData(
        code="FREEZE_DAMAGE_THAW_REPAIR",
        name="Freeze Damage — Thaw & Multi-Point Repair",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        urgency_multipliers={"standard": 1.0, "same_day": 1.4, "emergency": 1.8},
        applicable_assemblies=["FREEZE_REPAIR_KIT"],
        notes=(
            "Post-freeze assessment and multi-point repair (up to 3 points). "
            "DFW pipes in exterior walls and attics are most vulnerable. "
            "Includes controlled thaw, pressure test, and repair. Additional points billed hourly."
        ),
    ),

    "PIPE_INSULATION_INSTALL": LaborTemplateData(
        code="PIPE_INSULATION_INSTALL",
        name="Pipe Insulation — Freeze Protection (per 50 LF)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["PIPE_INSULATION_KIT"],
        notes=(
            "Foam pipe insulation on exposed supply lines. Per 50 LF. "
            "DFW preventive measure for exterior wall and attic pipes. "
            "UPC/IRC requires insulation on hot water lines in unconditioned spaces."
        ),
    ),

    # ── Gas Line Additions ───────────────────────────────────────────────────

    "GAS_LINE_DRYER": LaborTemplateData(
        code="GAS_LINE_DRYER",
        name="Gas Line — Dryer Hookup",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_DRYER_KIT"],
        notes=(
            "Gas dryer connection from existing stub-out. "
            "Includes flex connector, shutoff valve, and leak test. "
            "If no stub-out exists, use GAS_LINE_NEW_RUN for new line."
        ),
    ),

    "GAS_LINE_RANGE_OVEN": LaborTemplateData(
        code="GAS_LINE_RANGE_OVEN",
        name="Gas Line — Range/Oven Hookup",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_RANGE_KIT"],
        notes=(
            "Gas range/oven connection from existing stub-out. "
            "Includes flex connector (48\" stainless), shutoff valve, and leak test with solution."
        ),
    ),

    "GAS_LINE_FIREPLACE": LaborTemplateData(
        code="GAS_LINE_FIREPLACE",
        name="Gas Line — Fireplace Install",
        category="service",
        base_hours=3.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_FIREPLACE_KIT"],
        notes=(
            "New gas line run to fireplace. CSST or black iron per local code. "
            "DFW new builds commonly spec gas fireplaces. "
            "Includes shutoff valve, pressure test, and permit coordination."
        ),
    ),

    "GAS_LINE_GRILL_OUTDOOR": LaborTemplateData(
        code="GAS_LINE_GRILL_OUTDOOR",
        name="Gas Line — Outdoor Grill/Kitchen Hookup",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_OUTDOOR_KIT"],
        notes=(
            "Permanent gas line to outdoor grill or kitchen. "
            "DFW outdoor living is huge — very common upgrade. "
            "Includes quick-disconnect, shutoff, and underground or wall run. Permit required."
        ),
    ),

    "GAS_LEAK_DETECTION": LaborTemplateData(
        code="GAS_LEAK_DETECTION",
        name="Gas Leak Detection Survey (whole-house)",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        notes=(
            "Electronic gas leak survey of all connections, fittings, and appliances. "
            "Combustible gas detector + soap solution at each joint. "
            "Written report provided. If leak found: GAS_LINE_REPAIR_MINOR for fix."
        ),
    ),

    # ── Commercial/Multi-Family Additions ────────────────────────────────────

    "COMMERCIAL_GREASE_TRAP_CLEAN": LaborTemplateData(
        code="COMMERCIAL_GREASE_TRAP_CLEAN",
        name="Grease Trap/Interceptor — Pump & Clean",
        category="commercial",
        base_hours=2.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        notes=(
            "Interior grease trap pump and clean (up to 50 gal). "
            "DFW health dept requires quarterly for restaurants. "
            "Includes scrape, flush, and reinstall baffles. Grease hauling fee extra."
        ),
    ),

    "COMMERCIAL_GREASE_TRAP_INSTALL": LaborTemplateData(
        code="COMMERCIAL_GREASE_TRAP_INSTALL",
        name="Grease Trap/Interceptor — New Install",
        category="commercial",
        base_hours=6.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=0.5,
        applicable_assemblies=["GREASE_TRAP_KIT"],
        notes=(
            "Interior or exterior grease interceptor install. "
            "DFW code requires for all new food service establishments. "
            "Includes excavation (if exterior), plumbing connections, and permit."
        ),
    ),

    "COMMERCIAL_FLOOR_DRAIN_INSTALL": LaborTemplateData(
        code="COMMERCIAL_FLOOR_DRAIN_INSTALL",
        name="Commercial Floor Drain — New Install",
        category="commercial",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.5,
        applicable_assemblies=["COMMERCIAL_FLOOR_DRAIN_KIT"],
        notes=(
            "6\" or 8\" floor drain with adjustable strainer. "
            "Concrete cutting and patching included. "
            "Tie-in to existing sewer or new connection. Trap primer recommended."
        ),
    ),

    "FLUSHOMETER_REPLACE": LaborTemplateData(
        code="FLUSHOMETER_REPLACE",
        name="Flushometer Valve Replace (toilet)",
        category="commercial",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["FLUSHOMETER_KIT"],
        notes=(
            "Sloan Royal 111 or Zurn equivalent for floor-mount commercial toilet. "
            "Includes vacuum breaker, handle kit, and tailpiece gasket. "
            "DFW offices, retail, and restaurant common call."
        ),
    ),

    "COMMERCIAL_WATER_HEATER_INSTALL": LaborTemplateData(
        code="COMMERCIAL_WATER_HEATER_INSTALL",
        name="Commercial Water Heater Install (75-100G)",
        category="commercial",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=1.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.3, "emergency": 1.6},
        applicable_assemblies=["COMMERCIAL_WH_KIT"],
        notes=(
            "75-100G commercial gas water heater. Requires mechanical room access. "
            "Includes flue/vent modifications, expansion tank, mixing valve, and T&P piping. "
            "Permit required in all DFW jurisdictions."
        ),
    ),

    # ── Outdoor/Irrigation Additions ─────────────────────────────────────────

    "IRRIGATION_BACKFLOW_INSTALL": LaborTemplateData(
        code="IRRIGATION_BACKFLOW_INSTALL",
        name="Irrigation Backflow Preventer Install",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["IRRIGATION_BACKFLOW_KIT"],
        notes=(
            "PVB or RPZ backflow preventer for sprinkler system. "
            "DFW municipalities require backflow device on all irrigation systems. "
            "Includes initial test and certification filing."
        ),
    ),

    "IRRIGATION_VALVE_REPAIR": LaborTemplateData(
        code="IRRIGATION_VALVE_REPAIR",
        name="Irrigation Zone Valve Repair/Replace",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["IRRIGATION_VALVE_KIT"],
        notes=(
            "Replace failed solenoid valve, diaphragm, or entire zone valve body. "
            "DFW sun exposure and mineral buildup cause frequent valve failures."
        ),
    ),

    "CATCH_BASIN_INSTALL": LaborTemplateData(
        code="CATCH_BASIN_INSTALL",
        name="Surface Water Catch Basin — Install",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.5,
        applicable_assemblies=["CATCH_BASIN_KIT"],
        notes=(
            "12\" or 18\" catch basin with grate. Includes excavation, basin set, "
            "and 4\" corrugated pipe connection to discharge point. "
            "DFW clay soil drainage is a major homeowner concern."
        ),
    ),

    "YARD_HYDRANT_INSTALL": LaborTemplateData(
        code="YARD_HYDRANT_INSTALL",
        name="Frost-Proof Yard Hydrant — Install",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.0,
        applicable_assemblies=["YARD_HYDRANT_KIT"],
        notes=(
            "Frost-proof yard hydrant with bury depth below frost line (12\" in DFW). "
            "Includes trenching to water main, supply line, and gravel base. "
            "Common on DFW acreage/rural properties."
        ),
    ),

    # ── Accessibility & Specialty Additions ──────────────────────────────────

    "ADA_GRAB_BAR_INSTALL": LaborTemplateData(
        code="ADA_GRAB_BAR_INSTALL",
        name="ADA Grab Bar — Install with Blocking",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GRAB_BAR_KIT"],
        notes=(
            "Per grab bar. Includes locating studs, adding blocking if needed, "
            "and SS grab bar mount. DFW aging population driving high demand. "
            "Tile drilling with diamond bit if needed."
        ),
    ),

    "WATER_HEATER_TIMER_INSTALL": LaborTemplateData(
        code="WATER_HEATER_TIMER_INSTALL",
        name="Water Heater Timer/Controller Install",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WH_TIMER_KIT"],
        notes=(
            "Programmable timer for electric or gas WH. "
            "DFW TXU/Oncor time-of-use rate savings. "
            "Electrical connection by plumber (low-voltage control) or electrician (240V)."
        ),
    ),

    "EMERGENCY_SHUTOFF_VALVE_INSTALL": LaborTemplateData(
        code="EMERGENCY_SHUTOFF_VALVE_INSTALL",
        name="Automatic Water Shutoff Valve — Install",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["AUTO_SHUTOFF_KIT"],
        notes=(
            "Whole-house automatic shutoff valve with leak detection sensors. "
            "Flo by Moen, Phyn Plus, or StreamLabs Control. "
            "DFW insurance companies increasingly offer premium discounts for these."
        ),
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # Phase 3: Comprehensive DFW Expansion (2025-2026)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── A. Diagnostic & Inspection Services ────────────────────────────────────

    "LEAK_DETECTION_ELECTRONIC": LaborTemplateData(
        code="LEAK_DETECTION_ELECTRONIC",
        name="Electronic Leak Detection — Full Survey",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Electronic leak detection with listening discs, correlation equipment. "
            "Covers slab, walls, yard. DFW expansive clay soil causes frequent slab movement."
        ),
    ),

    "SMOKE_TEST_SEWER": LaborTemplateData(
        code="SMOKE_TEST_SEWER",
        name="Sewer Smoke Test — Odor Source Location",
        category="service",
        base_hours=1.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Smoke machine test to locate sewer gas entry points. "
            "Common in DFW homes with dried-out P-traps or cracked vent stacks."
        ),
    ),

    "HYDROSTATIC_TEST_SEWER": LaborTemplateData(
        code="HYDROSTATIC_TEST_SEWER",
        name="Hydrostatic Sewer Test — Under Slab",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes=(
            "Fill sewer system to slab level to locate under-slab leaks. "
            "Required by many DFW home inspectors during real estate transactions."
        ),
    ),

    "THERMAL_IMAGING_LEAK": LaborTemplateData(
        code="THERMAL_IMAGING_LEAK",
        name="Thermal Imaging Leak Survey",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="FLIR or similar thermal camera to locate moisture behind walls, under slab.",
    ),

    "VIDEO_CALL_DIAGNOSTIC": LaborTemplateData(
        code="VIDEO_CALL_DIAGNOSTIC",
        name="Remote Video Diagnostic Consultation",
        category="service",
        base_hours=0.5,
        lead_rate=105.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Video call diagnosis for simple issues. No truck roll. Credits toward service if job booked.",
    ),

    "SECOND_OPINION_INSPECTION": LaborTemplateData(
        code="SECOND_OPINION_INSPECTION",
        name="Second Opinion Inspection — On-Site",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="On-site evaluation of work recommended by another plumber. Written assessment provided.",
    ),

    # ── B. Water Line & Supply ─────────────────────────────────────────────────

    "WATER_LINE_REPAIR_COPPER": LaborTemplateData(
        code="WATER_LINE_REPAIR_COPPER",
        name="Copper Water Line Spot Repair",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["COPPER_REPAIR_KIT"],
        notes="Spot repair on copper supply line using ProPress or solder. DFW copper corrosion common.",
    ),

    "WATER_LINE_REPAIR_PEX": LaborTemplateData(
        code="WATER_LINE_REPAIR_PEX",
        name="PEX Water Line Repair",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["PEX_REPAIR_KIT"],
        notes="Repair or splice PEX supply line with expansion fittings.",
    ),

    "WATER_LINE_REPLACE_MAIN_STREET": LaborTemplateData(
        code="WATER_LINE_REPLACE_MAIN_STREET",
        name="Main Water Line Replace — Street to House",
        category="service",
        base_hours=8.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=1.0,
        applicable_assemblies=["MAIN_LINE_REPLACE_KIT"],
        notes=(
            "Full replacement of main water line from meter to house. "
            "Typically 50-100 LF. May require city permit and meter adapter."
        ),
    ),

    "MANIFOLD_INSTALL_PEX": LaborTemplateData(
        code="MANIFOLD_INSTALL_PEX",
        name="PEX Manifold System Install",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.5,
        applicable_assemblies=["MANIFOLD_KIT"],
        notes="Install central PEX manifold with individual fixture shutoffs. Typical in DFW repipes.",
    ),

    "PRESSURE_BOOSTER_INSTALL": LaborTemplateData(
        code="PRESSURE_BOOSTER_INSTALL",
        name="Water Pressure Booster Pump — Install",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["PRESSURE_BOOSTER_KIT"],
        notes="Davey or Grundfos booster pump for low-pressure areas. Common in elevated DFW lots.",
    ),

    "SHUT_OFF_VALVE_MAIN": LaborTemplateData(
        code="SHUT_OFF_VALVE_MAIN",
        name="Main Shutoff Valve Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["MAIN_SHUTOFF_KIT"],
        notes="Replace main water shutoff valve (gate to ball valve upgrade). Requires city meter shutoff.",
    ),

    "THERMAL_EXPANSION_VALVE": LaborTemplateData(
        code="THERMAL_EXPANSION_VALVE",
        name="Thermal Expansion Relief Valve — Install",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["THERMAL_EXPANSION_KIT"],
        notes="Thermal expansion valve on closed-loop systems. DFW code requirement with PRV + check valve.",
    ),

    # ── C. Drain & Waste Expanded ──────────────────────────────────────────────

    "DRAIN_CLEAN_LAUNDRY": LaborTemplateData(
        code="DRAIN_CLEAN_LAUNDRY",
        name="Laundry Drain Clearing",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Laundry standpipe/drain clearing. Lint buildup is #1 cause in DFW.",
    ),

    "DRAIN_CLEAN_DOUBLE_KITCHEN": LaborTemplateData(
        code="DRAIN_CLEAN_DOUBLE_KITCHEN",
        name="Double Kitchen Sink Drain Clearing",
        category="service",
        base_hours=1.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Double-bowl kitchen sink drain clearing including disposal side. Grease buildup common.",
    ),

    "CLEANOUT_CAP_REPLACE": LaborTemplateData(
        code="CLEANOUT_CAP_REPLACE",
        name="Cleanout Cap Replace",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["CLEANOUT_CAP_KIT"],
        notes="Replace missing or broken cleanout cap. Prevents sewer gas and pest entry.",
    ),

    "VENT_PIPE_REPAIR_ROOF": LaborTemplateData(
        code="VENT_PIPE_REPAIR_ROOF",
        name="Roof Vent Pipe Repair & Reflash",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["VENT_PIPE_KIT"],
        notes=(
            "Repair or replace roof vent pipe and boot/flashing. "
            "DFW heat and UV degrade rubber boots — common roof leak source."
        ),
    ),

    "AAV_INSTALL": LaborTemplateData(
        code="AAV_INSTALL",
        name="Air Admittance Valve (Studor Vent) Install",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["AAV_KIT"],
        notes="Install AAV/Studor vent for island sinks or locations without vent stack access.",
    ),

    "EJECTOR_PUMP_INSTALL": LaborTemplateData(
        code="EJECTOR_PUMP_INSTALL",
        name="Sewage Ejector Pump System Install",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.5,
        applicable_assemblies=["EJECTOR_PUMP_KIT"],
        notes="Below-grade sewage ejector with basin, pump, check valve, and vent. Permit required.",
    ),

    # ── D. Bathroom Fixture Expanded ───────────────────────────────────────────

    "SHOWER_DOOR_PLUMBING_PREP": LaborTemplateData(
        code="SHOWER_DOOR_PLUMBING_PREP",
        name="Shower Door Plumbing Prep — Rough-In",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Rough-in prep for frameless shower door (drain positioning, curb prep). Plumbing side only.",
    ),

    "SHOWER_DIVERTER_REPAIR": LaborTemplateData(
        code="SHOWER_DIVERTER_REPAIR",
        name="Tub/Shower Diverter Repair or Replace",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["DIVERTER_KIT"],
        notes="Repair or replace tub spout diverter or in-wall diverter valve.",
    ),

    "ROMAN_TUB_FAUCET_REPLACE": LaborTemplateData(
        code="ROMAN_TUB_FAUCET_REPLACE",
        name="Roman Tub Faucet — Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["ROMAN_TUB_KIT"],
        notes="Deck-mount Roman tub filler with hand sprayer. Access panel required for valve body.",
    ),

    "CLAW_FOOT_TUB_PLUMBING": LaborTemplateData(
        code="CLAW_FOOT_TUB_PLUMBING",
        name="Clawfoot Tub Plumbing Hookup",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        applicable_assemblies=["CLAWFOOT_TUB_KIT"],
        notes="Supply, drain, and overflow hookup for freestanding clawfoot tub. Floor-mount or wall-mount filler.",
    ),

    "BARRIER_FREE_SHOWER_INSTALL": LaborTemplateData(
        code="BARRIER_FREE_SHOWER_INSTALL",
        name="ADA Barrier-Free Shower — Plumbing Install",
        category="service",
        base_hours=8.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=1.0,
        applicable_assemblies=["BARRIER_FREE_SHOWER_KIT"],
        notes=(
            "Zero-threshold shower with linear drain, thermostatic valve, grab bars. "
            "ADA compliant. Growing demand in DFW aging-in-place market."
        ),
    ),

    "STEAM_SHOWER_VALVE_INSTALL": LaborTemplateData(
        code="STEAM_SHOWER_VALVE_INSTALL",
        name="Steam Shower Generator — Plumbing Connection",
        category="service",
        base_hours=4.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["STEAM_SHOWER_KIT"],
        notes="Plumbing connections for steam generator: cold water supply, steam line, condensate drain.",
    ),

    "BIDET_SPRAYER_INSTALL": LaborTemplateData(
        code="BIDET_SPRAYER_INSTALL",
        name="Handheld Bidet Sprayer — Install",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["BIDET_SPRAYER_KIT"],
        notes="T-adapter install at toilet supply for handheld bidet sprayer with holder.",
    ),

    # ── E. Kitchen & Appliance ─────────────────────────────────────────────────

    "INSTANT_HOT_WATER_INSTALL": LaborTemplateData(
        code="INSTANT_HOT_WATER_INSTALL",
        name="Instant Hot Water Dispenser — Install",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["INSTANT_HOT_KIT"],
        notes="Under-sink instant hot water dispenser (InSinkErator or similar) with dedicated faucet.",
    ),

    "REFRIGERATOR_LINE_INSTALL": LaborTemplateData(
        code="REFRIGERATOR_LINE_INSTALL",
        name="Refrigerator Water/Ice Line — Install",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["FRIDGE_LINE_KIT"],
        notes="Braided SS line from cold water supply to refrigerator with saddle or angle stop valve.",
    ),

    "DISHWASHER_DRAIN_REPAIR": LaborTemplateData(
        code="DISHWASHER_DRAIN_REPAIR",
        name="Dishwasher Drain Issue — Repair",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Diagnose and repair dishwasher drain problem: air gap, high loop, blocked hose.",
    ),

    "GARBAGE_DISPOSAL_REPLACE_HP": LaborTemplateData(
        code="GARBAGE_DISPOSAL_REPLACE_HP",
        name="Garbage Disposal — Replace (3/4-1 HP Upgrade)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["DISPOSAL_HP_KIT"],
        notes="Upgrade to high-power disposal (3/4 HP or 1 HP). May require wiring upgrade.",
    ),

    "PREP_SINK_INSTALL": LaborTemplateData(
        code="PREP_SINK_INSTALL",
        name="Kitchen Prep/Island Sink — Install",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["PREP_SINK_KIT"],
        notes="Island or prep sink install with AAV vent (no vent stack on island). DFW kitchen remodel staple.",
    ),

    "COMMERCIAL_SPRAYER_FAUCET": LaborTemplateData(
        code="COMMERCIAL_SPRAYER_FAUCET",
        name="Commercial Pre-Rinse Faucet — Install",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["SPRAYER_FAUCET_KIT"],
        notes="Wall or deck mount commercial-style pre-rinse sprayer faucet. Popular in DFW luxury kitchens.",
    ),

    # ── F. Outdoor & Yard Expanded ─────────────────────────────────────────────

    "FRENCH_DRAIN_INSTALL": LaborTemplateData(
        code="FRENCH_DRAIN_INSTALL",
        name="French Drain Install (per 25 LF)",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=0.5,
        applicable_assemblies=["FRENCH_DRAIN_KIT"],
        notes=(
            "Excavate, install perforated pipe, gravel, filter fabric per 25 LF. "
            "Essential in DFW black clay soil areas for foundation drainage."
        ),
    ),

    "SUMP_PUMP_REPLACE": LaborTemplateData(
        code="SUMP_PUMP_REPLACE",
        name="Sump Pump — Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["SUMP_PUMP_REPLACE_KIT"],
        notes="Replace existing sump pump (pump only, basin reuse). Check valve and discharge line.",
    ),

    "POOL_PLUMBING_REPAIR": LaborTemplateData(
        code="POOL_PLUMBING_REPAIR",
        name="Pool Plumbing Line — Repair",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Repair pool supply/return plumbing line. Pressure test and locate leak. PVC schedule 40.",
    ),

    "OUTDOOR_SHOWER_INSTALL": LaborTemplateData(
        code="OUTDOOR_SHOWER_INSTALL",
        name="Outdoor Shower — Plumbing Install",
        category="service",
        base_hours=4.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["OUTDOOR_SHOWER_KIT"],
        notes="Hot and cold supply lines, mixing valve, drain. Freeze protection required in DFW.",
    ),

    "SPRINKLER_LINE_REPAIR": LaborTemplateData(
        code="SPRINKLER_LINE_REPAIR",
        name="Irrigation/Sprinkler Line Repair",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["SPRINKLER_REPAIR_KIT"],
        notes="Locate and repair broken sprinkler line or fitting. DFW freeze damage and lawn equipment hits.",
    ),

    "RAIN_BARREL_HOOKUP": LaborTemplateData(
        code="RAIN_BARREL_HOOKUP",
        name="Rain Barrel / Rainwater Collection Hookup",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["RAIN_BARREL_KIT"],
        notes="Connect rain barrel to downspout with first-flush diverter and overflow. DFW water conservation.",
    ),

    # ── G. Gas System Expanded ─────────────────────────────────────────────────

    "GAS_LINE_POOL_HEATER": LaborTemplateData(
        code="GAS_LINE_POOL_HEATER",
        name="Gas Line — Pool/Spa Heater",
        category="service",
        base_hours=4.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_POOL_HEATER_KIT"],
        notes="New gas line run to pool heater. Typically 3/4\" CSST, 30-60 LF. BTU load calculation required.",
    ),

    "GAS_LINE_GENERATOR": LaborTemplateData(
        code="GAS_LINE_GENERATOR",
        name="Gas Line — Standby Generator",
        category="service",
        base_hours=5.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_GENERATOR_KIT"],
        notes=(
            "Gas line to standby generator (Generac/Kohler). "
            "May require meter upgrade. Growing DFW demand after 2021 winter storm."
        ),
    ),

    "GAS_LINE_TANKLESS_WH": LaborTemplateData(
        code="GAS_LINE_TANKLESS_WH",
        name="Gas Line Upgrade — Tankless Water Heater",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_TANKLESS_UPGRADE_KIT"],
        notes="Upsize gas line from 1/2\" to 3/4\" for tankless WH BTU requirements. Common DFW upgrade.",
    ),

    "GAS_METER_UPGRADE_COORD": LaborTemplateData(
        code="GAS_METER_UPGRADE_COORD",
        name="Gas Meter Upgrade Coordination",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Coordinate gas meter upgrade with Atmos Energy. On-site meeting, paperwork, verification.",
    ),

    "GAS_APPLIANCE_DISCONNECT": LaborTemplateData(
        code="GAS_APPLIANCE_DISCONNECT",
        name="Gas Appliance Safe Disconnect & Cap",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_CAP_KIT"],
        notes="Safely disconnect gas appliance, cap line, pressure test. Per appliance.",
    ),

    # ── H. Water Treatment Expanded ────────────────────────────────────────────

    "WATER_SOFTENER_REPLACE": LaborTemplateData(
        code="WATER_SOFTENER_REPLACE",
        name="Water Softener — Replace",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.5,
        applicable_assemblies=["WATER_SOFTENER_REPLACE_KIT"],
        notes="Remove old unit, install new softener. DFW hard water (15-25 gpg) makes this high-demand.",
    ),

    "WATER_SOFTENER_REPAIR": LaborTemplateData(
        code="WATER_SOFTENER_REPAIR",
        name="Water Softener — Repair/Rebuild",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Diagnose and repair water softener: control valve, brine tank, resin bed, timer.",
    ),

    "UV_DISINFECTION_INSTALL": LaborTemplateData(
        code="UV_DISINFECTION_INSTALL",
        name="UV Water Disinfection System — Install",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["UV_SYSTEM_KIT"],
        notes="Whole-house UV disinfection (Viqua/Sterilight). Point-of-entry install with pre-filter.",
    ),

    "SEDIMENT_FILTER_INSTALL": LaborTemplateData(
        code="SEDIMENT_FILTER_INSTALL",
        name="Whole-House Sediment Filter — Install",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["SEDIMENT_FILTER_KIT"],
        notes="Install sediment/carbon filter housing on main line. DFW lake water source = sediment issues.",
    ),

    "WATER_TESTING_SERVICE": LaborTemplateData(
        code="WATER_TESTING_SERVICE",
        name="Comprehensive Water Quality Test",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="On-site water quality test: hardness, pH, chlorine, TDS, iron, bacteria. Lab send-out for metals.",
    ),

    # ── I. Emergency & After-Hours ─────────────────────────────────────────────

    "EMERGENCY_WATER_SHUTOFF": LaborTemplateData(
        code="EMERGENCY_WATER_SHUTOFF",
        name="Emergency Main Water Shutoff Response",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 2.0},
        applicable_assemblies=[],
        notes="Emergency response to locate and shut main water valve. Includes basic assessment.",
    ),

    "EMERGENCY_GAS_SHUTOFF": LaborTemplateData(
        code="EMERGENCY_GAS_SHUTOFF",
        name="Emergency Gas Shutoff Response",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 2.0},
        applicable_assemblies=[],
        notes="Emergency gas shutoff at meter or appliance. Includes gas leak check. Call Atmos Energy first.",
    ),

    "EMERGENCY_SEWER_BACKUP": LaborTemplateData(
        code="EMERGENCY_SEWER_BACKUP",
        name="Emergency Sewer Backup Response",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.5,
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 2.0},
        applicable_assemblies=[],
        notes="Emergency sewer backup: machine clear main line, extract standing water. DFW clay soil = root intrusion.",
    ),

    "FLOOD_DAMAGE_MITIGATION": LaborTemplateData(
        code="FLOOD_DAMAGE_MITIGATION",
        name="Flood Water Mitigation & Pump-Out",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=1.0,
        urgency_multipliers={"standard": 1.0, "same_day": 1.25, "emergency": 2.0},
        applicable_assemblies=[],
        notes="Emergency water extraction, temporary repairs, source shutoff. Coordinate with restoration company.",
    ),

    "AFTER_HOURS_DIAGNOSTIC": LaborTemplateData(
        code="AFTER_HOURS_DIAGNOSTIC",
        name="After-Hours Diagnostic Visit",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        urgency_multipliers={"standard": 1.5, "same_day": 1.75, "emergency": 2.5},
        applicable_assemblies=[],
        notes="After-hours (6pm-8am, weekends, holidays) diagnostic visit. Higher rate reflects overtime.",
    ),

    # ── J. Maintenance & Preventive ────────────────────────────────────────────

    "PLUMBING_INSPECTION_ANNUAL": LaborTemplateData(
        code="PLUMBING_INSPECTION_ANNUAL",
        name="Annual Plumbing Inspection",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Full-home plumbing inspection: water heater, fixtures, supply lines, drains, "
            "hose bibs, shutoff valves. Written report with priority recommendations."
        ),
    ),

    "WINTERIZATION_SERVICE": LaborTemplateData(
        code="WINTERIZATION_SERVICE",
        name="Winter Pipe Protection Service",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Insulate exposed pipes, install freeze-proof covers on hose bibs, "
            "check attic/crawl space exposure. Critical in DFW after 2021 Uri freeze event."
        ),
    ),

    "DE_WINTERIZATION_SERVICE": LaborTemplateData(
        code="DE_WINTERIZATION_SERVICE",
        name="Spring De-Winterization Service",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Remove winterization, test all fixtures, check for freeze damage, restore irrigation.",
    ),

    "WATER_HEATER_ANNUAL_SERVICE": LaborTemplateData(
        code="WATER_HEATER_ANNUAL_SERVICE",
        name="Water Heater Annual Maintenance",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Flush tank, check anode rod, test T&P valve, inspect flue/venting. Extends WH life 3-5 years.",
    ),

    "FIXTURE_CAULK_RESEAL": LaborTemplateData(
        code="FIXTURE_CAULK_RESEAL",
        name="Bathtub/Shower Caulk Reseal",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Remove old caulk, clean, apply new silicone sealant around tub, shower, or sink.",
    ),

    "WHOLE_HOUSE_SHUTOFF_TEST": LaborTemplateData(
        code="WHOLE_HOUSE_SHUTOFF_TEST",
        name="Whole-House Shutoff Valve Test",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Test and exercise all shutoff valves (main, WH, fixtures, irrigation). Identify seized valves.",
    ),

    "HOSE_BIB_WINTERIZE": LaborTemplateData(
        code="HOSE_BIB_WINTERIZE",
        name="Hose Bib Winterization (per bib)",
        category="service",
        base_hours=0.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["HOSE_BIB_COVER_KIT"],
        notes="Install insulated cover, disconnect hose, shut interior valve. Per hose bib.",
    ),

    # ═══════════════════════════════════════════════════════════════════════════
    # Phase 4: Construction, Commercial & Service Gap Expansion (2025-2026)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── K. New Construction — Residential Rough-In & Build-Out ─────────────────

    "ROUGH_IN_MASTER_BATH": LaborTemplateData(
        code="ROUGH_IN_MASTER_BATH",
        name="Master Bath Rough-In (DWV + Supply)",
        category="construction",
        base_hours=16.0,
        helper_required=True,
        helper_hours=12.0,
        disposal_hours=0.5,
        applicable_assemblies=[],
        notes=(
            "Full master bath rough-in: dual sinks, shower, soaking tub, toilet. "
            "DWV and hot/cold supply in PEX. DFW new-build standard."
        ),
    ),

    "ROUGH_IN_SECONDARY_BATH": LaborTemplateData(
        code="ROUGH_IN_SECONDARY_BATH",
        name="Secondary/Kids Bath Rough-In",
        category="construction",
        base_hours=10.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=0.5,
        applicable_assemblies=[],
        notes="Standard secondary bath: single sink, tub/shower combo, toilet rough-in.",
    ),

    "ROUGH_IN_HALF_BATH": LaborTemplateData(
        code="ROUGH_IN_HALF_BATH",
        name="Half Bath / Powder Room Rough-In",
        category="construction",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Half bath rough-in: single sink, toilet. Minimal DWV and supply.",
    ),

    "ROUGH_IN_KITCHEN": LaborTemplateData(
        code="ROUGH_IN_KITCHEN",
        name="Kitchen Plumbing Rough-In",
        category="construction",
        base_hours=8.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Kitchen rough-in: sink, dishwasher, disposal, ice maker, pot filler stub.",
    ),

    "ROUGH_IN_LAUNDRY": LaborTemplateData(
        code="ROUGH_IN_LAUNDRY",
        name="Laundry Room Plumbing Rough-In",
        category="construction",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Laundry rough-in: washer box with H/C supply, 2\" standpipe drain, gas stub for dryer.",
    ),

    "ROUGH_IN_OUTDOOR": LaborTemplateData(
        code="ROUGH_IN_OUTDOOR",
        name="Outdoor Plumbing Rough-In (Hose Bibs + Irrigation Stub)",
        category="construction",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Rough-in for 3-4 frost-proof hose bibs + irrigation tap stub. DFW freeze-resistant.",
    ),

    "ROUGH_IN_GAS_WHOLE_HOUSE": LaborTemplateData(
        code="ROUGH_IN_GAS_WHOLE_HOUSE",
        name="Whole-House Gas Rough-In",
        category="construction",
        base_hours=12.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Complete gas rough-in: WH, range, dryer, fireplace, outdoor grill. "
            "CSST manifold or black iron. BTU load calc and Atmos coordination."
        ),
    ),

    "ROUGH_IN_WH_LOCATION": LaborTemplateData(
        code="ROUGH_IN_WH_LOCATION",
        name="Water Heater Location Rough-In",
        category="construction",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="WH rough-in: gas line, cold supply, hot distribution, T&P drain, pan drain, expansion tank.",
    ),

    "SEWER_TAP_CONNECTION": LaborTemplateData(
        code="SEWER_TAP_CONNECTION",
        name="Sewer Tap & City Connection",
        category="construction",
        base_hours=6.0,
        helper_required=True,
        helper_hours=6.0,
        disposal_hours=1.0,
        applicable_assemblies=["SEWER_TAP_KIT"],
        notes="Tap into city sewer main with wye or saddle. City permit and inspection required.",
    ),

    "WATER_TAP_CONNECTION": LaborTemplateData(
        code="WATER_TAP_CONNECTION",
        name="Water Service Tap & Meter Set",
        category="construction",
        base_hours=5.0,
        helper_required=True,
        helper_hours=5.0,
        disposal_hours=0.5,
        applicable_assemblies=["WATER_TAP_KIT"],
        notes="Water service from main to meter + line to house. City coordination required.",
    ),

    "FIRE_SPRINKLER_RESIDENTIAL": LaborTemplateData(
        code="FIRE_SPRINKLER_RESIDENTIAL",
        name="Residential Fire Sprinkler — Per Head",
        category="construction",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["SPRINKLER_HEAD_KIT"],
        notes="NFPA 13D residential fire sprinkler head install. Typically 10-15 heads per home.",
    ),

    "CONCRETE_CORE_DRILL": LaborTemplateData(
        code="CONCRETE_CORE_DRILL",
        name="Concrete Core Drill for Pipe Penetration",
        category="construction",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Core drill through concrete slab or foundation for pipe penetration. Per hole.",
    ),

    "STUB_OUT_CAP_TEST": LaborTemplateData(
        code="STUB_OUT_CAP_TEST",
        name="Stub-Out Cap & Pressure Test",
        category="construction",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Cap all stub-outs, pressurize system for inspection. DWV air test + supply pressure test.",
    ),

    "FIXTURE_TRIM_OUT_FULL_BATH": LaborTemplateData(
        code="FIXTURE_TRIM_OUT_FULL_BATH",
        name="Full Bath Fixture Trim-Out (Final Set)",
        category="construction",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.5,
        applicable_assemblies=[],
        notes="Trim/set all fixtures in one full bath: toilet, vanity, faucet, shower valve, tub spout.",
    ),

    "SLEEVE_INSTALL_PER_PENETRATION": LaborTemplateData(
        code="SLEEVE_INSTALL_PER_PENETRATION",
        name="Pipe Sleeve Install (per penetration)",
        category="construction",
        base_hours=0.25,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Install pipe sleeve through wall/floor for code-required fire separation.",
    ),

    "MULTI_STORY_RISER_PER_FLOOR": LaborTemplateData(
        code="MULTI_STORY_RISER_PER_FLOOR",
        name="DWV/Supply Riser — Per Floor",
        category="construction",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.5,
        applicable_assemblies=[],
        notes="Vertical riser (DWV stack + supply) per additional floor. Multi-story residential.",
    ),

    "TANKLESS_RECIRCULATION_LOOP": LaborTemplateData(
        code="TANKLESS_RECIRCULATION_LOOP",
        name="Tankless WH Recirculation Loop — New Build",
        category="construction",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        applicable_assemblies=["RECIRC_LOOP_KIT"],
        notes="Dedicated recirculation loop from tankless WH through home. PEX with insulation.",
    ),

    "SLAB_PLUMBING_LAYOUT": LaborTemplateData(
        code="SLAB_PLUMBING_LAYOUT",
        name="Under-Slab Plumbing Layout (per 1000 SF)",
        category="construction",
        base_hours=16.0,
        helper_required=True,
        helper_hours=16.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes=(
            "Pre-slab DWV layout per 1000 SF of foundation. "
            "Includes trenching, pipe install, gravel bed. DFW post-tension slab awareness critical."
        ),
    ),

    # ── L. Commercial Expansion ────────────────────────────────────────────────

    "COMMERCIAL_TOILET_INSTALL": LaborTemplateData(
        code="COMMERCIAL_TOILET_INSTALL",
        name="Commercial Toilet — Floor Mount Install",
        category="commercial",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.5,
        applicable_assemblies=["COMMERCIAL_TOILET_KIT"],
        notes="Floor-mount commercial toilet with flushometer. ADA spacing requirements.",
    ),

    "COMMERCIAL_WALL_HUNG_TOILET": LaborTemplateData(
        code="COMMERCIAL_WALL_HUNG_TOILET",
        name="Commercial Wall-Hung Toilet — Install",
        category="commercial",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.5,
        applicable_assemblies=["WALL_HUNG_TOILET_KIT"],
        notes="Wall-hung toilet with carrier. In-wall carrier frame + flushometer. Common in DFW offices.",
    ),

    "COMMERCIAL_URINAL_INSTALL": LaborTemplateData(
        code="COMMERCIAL_URINAL_INSTALL",
        name="Commercial Urinal — Wall Mount Install",
        category="commercial",
        base_hours=2.5,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.25,
        applicable_assemblies=["URINAL_INSTALL_KIT"],
        notes="Wall-hung urinal with flush valve. Includes carrier, supply, and waste connection.",
    ),

    "DRINKING_FOUNTAIN_INSTALL": LaborTemplateData(
        code="DRINKING_FOUNTAIN_INSTALL",
        name="Drinking Fountain / Water Cooler — Install",
        category="commercial",
        base_hours=3.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.25,
        applicable_assemblies=["FOUNTAIN_KIT"],
        notes="Wall-mount drinking fountain or bi-level with bottle filler. ADA compliant.",
    ),

    "EYE_WASH_STATION_INSTALL": LaborTemplateData(
        code="EYE_WASH_STATION_INSTALL",
        name="Emergency Eye Wash / Shower Station — Install",
        category="commercial",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=["EYEWASH_KIT"],
        notes="ANSI Z358.1 compliant eyewash/shower combo. Tepid water mixing valve required.",
    ),

    "MOP_SINK_INSTALL": LaborTemplateData(
        code="MOP_SINK_INSTALL",
        name="Mop/Service Sink — Install",
        category="commercial",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=["MOP_SINK_KIT"],
        notes="Floor-mount mop basin with wall faucet and vacuum breaker. Restaurant/janitorial.",
    ),

    "COMMERCIAL_DISHWASHER_HOOKUP": LaborTemplateData(
        code="COMMERCIAL_DISHWASHER_HOOKUP",
        name="Commercial Dishwasher — Plumbing Hookup",
        category="commercial",
        base_hours=4.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Commercial dishwasher H/C supply, waste, and air gap install. Restaurant code compliance.",
    ),

    "HANDS_FREE_FAUCET_INSTALL": LaborTemplateData(
        code="HANDS_FREE_FAUCET_INSTALL",
        name="Hands-Free / Sensor Faucet — Install",
        category="commercial",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["SENSOR_FAUCET_KIT"],
        notes="Battery or hardwired sensor faucet for commercial lavatory. ADA compliant.",
    ),

    "COMMERCIAL_PRV_INSTALL": LaborTemplateData(
        code="COMMERCIAL_PRV_INSTALL",
        name="Commercial PRV — Large Diameter Install",
        category="commercial",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=["COMMERCIAL_PRV_KIT"],
        notes="Commercial PRV 1.5-2\" with strainer and relief valve. Higher flow capacity.",
    ),

    "TMV_INSTALL": LaborTemplateData(
        code="TMV_INSTALL",
        name="Thermostatic Mixing Valve (ASSE 1017) — Install",
        category="commercial",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TMV_KIT"],
        notes="Point-of-use TMV for scald prevention. Required in healthcare, childcare, assisted living.",
    ),

    "GREASE_INTERCEPTOR_INSTALL": LaborTemplateData(
        code="GREASE_INTERCEPTOR_INSTALL",
        name="In-Ground Grease Interceptor — Install",
        category="commercial",
        base_hours=8.0,
        helper_required=True,
        helper_hours=8.0,
        disposal_hours=1.0,
        applicable_assemblies=[],
        notes="In-ground grease interceptor 500-1500 gallon. Excavation, plumbing, city permit. Restaurant.",
    ),

    "ROOF_DRAIN_INSTALL": LaborTemplateData(
        code="ROOF_DRAIN_INSTALL",
        name="Commercial Roof Drain — Install",
        category="commercial",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=["ROOF_DRAIN_KIT"],
        notes="Flat roof drain with leader connection to storm system. Commercial flat-roof buildings.",
    ),

    "SEWAGE_LIFT_STATION": LaborTemplateData(
        code="SEWAGE_LIFT_STATION",
        name="Sewage Lift Station — Install",
        category="commercial",
        base_hours=12.0,
        helper_required=True,
        helper_hours=10.0,
        disposal_hours=1.0,
        applicable_assemblies=[],
        notes="Below-grade duplex sewage lift station with controls. Commercial or multi-unit. Permit required.",
    ),

    "COMMERCIAL_WATER_SOFTENER": LaborTemplateData(
        code="COMMERCIAL_WATER_SOFTENER",
        name="Commercial Water Softener — Install",
        category="commercial",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.5,
        applicable_assemblies=["COMMERCIAL_SOFTENER_KIT"],
        notes="Commercial water softener 100K+ grain for office/restaurant. DFW hard water demand.",
    ),

    "BACKFLOW_PREVENTER_REPAIR": LaborTemplateData(
        code="BACKFLOW_PREVENTER_REPAIR",
        name="Backflow Preventer Repair / Rebuild",
        category="commercial",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["BACKFLOW_REPAIR_KIT"],
        notes="Repair RPZ or DCVA backflow preventer. Replace internals/check valves. Retest after repair.",
    ),

    # ── M. Service Gaps — Water Heater & Fixtures ──────────────────────────────

    "WH_DRAIN_PAN_REPLACE": LaborTemplateData(
        code="WH_DRAIN_PAN_REPLACE",
        name="Water Heater Drain Pan — Replace Only",
        category="service",
        base_hours=1.5,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Replace corroded or damaged WH drain pan. Requires lifting WH. Often paired with WH replace.",
    ),

    "WH_GAS_VALVE_REPLACE": LaborTemplateData(
        code="WH_GAS_VALVE_REPLACE",
        name="Water Heater Gas Valve — Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WH_GAS_VALVE_KIT"],
        notes="Replace failed gas control valve (Honeywell/Resideo). Drain, disconnect, swap, relight.",
    ),

    "TPR_VALVE_REPLACE": LaborTemplateData(
        code="TPR_VALVE_REPLACE",
        name="T&P Relief Valve — Replace",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TPR_VALVE_KIT"],
        notes="Replace temperature and pressure relief valve on water heater. Safety critical.",
    ),

    "WH_FLUE_REPAIR": LaborTemplateData(
        code="WH_FLUE_REPAIR",
        name="Water Heater Flue / Vent Connector Repair",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Repair or replace single-wall or B-vent flue connector. CO safety check included.",
    ),

    "WHIRLPOOL_TUB_REPAIR": LaborTemplateData(
        code="WHIRLPOOL_TUB_REPAIR",
        name="Whirlpool / Jetted Tub — Plumbing Repair",
        category="service",
        base_hours=2.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Diagnose and repair jetted tub plumbing: pump, jets, suction, air controls. Access panel required.",
    ),

    "BATHTUB_DISCONNECT_RECONNECT": LaborTemplateData(
        code="BATHTUB_DISCONNECT_RECONNECT",
        name="Bathtub Plumbing Disconnect & Reconnect",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=1.5,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Disconnect/reconnect tub plumbing for refinishing, reglazing, or floor work.",
    ),

    "TUB_DRAIN_ASSEMBLY_REPLACE": LaborTemplateData(
        code="TUB_DRAIN_ASSEMBLY_REPLACE",
        name="Tub Drain Assembly — Replace (Shoe & Overflow)",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["TUB_DRAIN_KIT"],
        notes="Replace tub drain shoe, overflow, stopper assembly. Access from below or panel required.",
    ),

    "SHOWER_DRAIN_REPLACE": LaborTemplateData(
        code="SHOWER_DRAIN_REPLACE",
        name="Shower Drain — Replace",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=["SHOWER_DRAIN_KIT"],
        notes="Replace shower drain body and strainer. May require subfloor access.",
    ),

    "FLOOR_DRAIN_RESIDENTIAL": LaborTemplateData(
        code="FLOOR_DRAIN_RESIDENTIAL",
        name="Residential Floor Drain — Install/Replace",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        applicable_assemblies=["FLOOR_DRAIN_KIT"],
        notes="Garage, utility, or basement floor drain install. Core drill if slab. Trap primer recommended.",
    ),

    # ── N. Service Gaps — Valves & Backflow ────────────────────────────────────

    "RPZ_REBUILD": LaborTemplateData(
        code="RPZ_REBUILD",
        name="RPZ Backflow Preventer — Rebuild",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["RPZ_REBUILD_KIT"],
        notes="Full RPZ rebuild with new check/relief valve internals. Includes post-rebuild test.",
    ),

    "DCVA_REPAIR": LaborTemplateData(
        code="DCVA_REPAIR",
        name="Double Check Valve Assembly — Repair",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["DCVA_REPAIR_KIT"],
        notes="DCVA rebuild with new check valve internals. Retest and submit report.",
    ),

    "EARTHQUAKE_VALVE_INSTALL": LaborTemplateData(
        code="EARTHQUAKE_VALVE_INSTALL",
        name="Seismic/Earthquake Gas Shutoff Valve — Install",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["EARTHQUAKE_VALVE_KIT"],
        notes="Automatic seismic gas shutoff at meter. Not required in DFW but requested for high-value homes.",
    ),

    "GAS_DRIP_LEG_INSTALL": LaborTemplateData(
        code="GAS_DRIP_LEG_INSTALL",
        name="Gas Drip Leg / Sediment Trap — Install",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["DRIP_LEG_KIT"],
        notes="Install or replace drip leg (sediment trap) at gas appliance. Code requirement.",
    ),

    "GATE_TO_BALL_VALVE_UPGRADE": LaborTemplateData(
        code="GATE_TO_BALL_VALVE_UPGRADE",
        name="Gate-to-Ball Valve Upgrade (per valve)",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["BALL_VALVE_KIT"],
        notes="Replace old seized gate valve with quarter-turn ball valve. Per valve.",
    ),

    "SUPPLY_STOP_MULTI_REPLACE": LaborTemplateData(
        code="SUPPLY_STOP_MULTI_REPLACE",
        name="Supply Stop Replacement — Multi (3+ valves)",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Replace 3 or more supply stops (angle/straight) in one visit. Volume discount.",
    ),

    # ── O. Service Gaps — Appliance Connections ────────────────────────────────

    "WASHING_MACHINE_HOSE_REPLACE": LaborTemplateData(
        code="WASHING_MACHINE_HOSE_REPLACE",
        name="Washing Machine Hose Replace — Pair",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["WASHER_HOSE_KIT"],
        notes="Replace both H/C washer hoses with braided SS. #1 flood damage prevention.",
    ),

    "DISHWASHER_SUPPLY_INSTALL": LaborTemplateData(
        code="DISHWASHER_SUPPLY_INSTALL",
        name="Dishwasher Supply Line — Install/Replace",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["DW_SUPPLY_KIT"],
        notes="Replace dishwasher supply line. Braided SS upgrade from copper or plastic.",
    ),

    "GAS_RANGE_CONNECTOR_REPLACE": LaborTemplateData(
        code="GAS_RANGE_CONNECTOR_REPLACE",
        name="Gas Range Connector — Replace",
        category="service",
        base_hours=0.75,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["GAS_RANGE_CONNECTOR_KIT"],
        notes="Replace gas range flex connector with new coated SS connector. Leak test included.",
    ),

    "GARBAGE_DISPOSAL_RESET_UNJAM": LaborTemplateData(
        code="GARBAGE_DISPOSAL_RESET_UNJAM",
        name="Garbage Disposal — Reset / Unjam",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Unjam disposal, reset overload, verify operation. Included in service call if simple.",
    ),

    # ── P. Service Gaps — Specialty & Emerging ─────────────────────────────────

    "RADIANT_FLOOR_LOOP": LaborTemplateData(
        code="RADIANT_FLOOR_LOOP",
        name="Radiant Floor Heat Loop — Plumbing Connection",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        applicable_assemblies=["RADIANT_LOOP_KIT"],
        notes="Connect radiant floor heating manifold to boiler/tankless WH. Plumbing side only.",
    ),

    "HYDRONIC_HEATING_REPAIR": LaborTemplateData(
        code="HYDRONIC_HEATING_REPAIR",
        name="Hydronic Heating — Plumbing Repair",
        category="service",
        base_hours=3.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Repair hydronic heating loop: leak, circulator pump, zone valve, expansion tank.",
    ),

    "RECLAIMED_WATER_LINE": LaborTemplateData(
        code="RECLAIMED_WATER_LINE",
        name="Reclaimed/Purple Pipe Water Line — Install",
        category="service",
        base_hours=4.0,
        helper_required=True,
        helper_hours=3.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Install reclaimed (purple pipe) water line for irrigation. DFW water districts offering this.",
    ),

    "SEPTIC_PUMP_OUT_COORD": LaborTemplateData(
        code="SEPTIC_PUMP_OUT_COORD",
        name="Septic Tank Pump-Out Coordination & Inspection",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Coordinate septic pump-out, inspect baffles/tank. DFW rural areas (Parker, Wise, Johnson counties).",
    ),

    "WELL_PUMP_REPAIR": LaborTemplateData(
        code="WELL_PUMP_REPAIR",
        name="Well Pump — Diagnose & Repair",
        category="service",
        base_hours=3.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Diagnose well pump issues: pressure switch, tank, control box. DFW outer counties on well water.",
    ),

    "WELL_PRESSURE_TANK_REPLACE": LaborTemplateData(
        code="WELL_PRESSURE_TANK_REPLACE",
        name="Well Pressure Tank — Replace",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=1.0,
        disposal_hours=0.25,
        applicable_assemblies=["WELL_TANK_KIT"],
        notes="Replace failed bladder-type well pressure tank (20-50 gallon). Set air charge.",
    ),

    "GREYWATER_SYSTEM_INSTALL": LaborTemplateData(
        code="GREYWATER_SYSTEM_INSTALL",
        name="Greywater Reuse System — Plumbing Install",
        category="service",
        base_hours=6.0,
        helper_required=True,
        helper_hours=4.0,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Laundry-to-landscape greywater diversion. Growing DFW water conservation trend.",
    ),

    "VANITY_PLUMBING_MODIFICATION": LaborTemplateData(
        code="VANITY_PLUMBING_MODIFICATION",
        name="Bathroom Vanity Plumbing Modification",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Rework drain/supply to fit new vanity dimensions. Single-to-double or vessel sink conversion.",
    ),

    "WATER_LINE_LOCATE_MARK": LaborTemplateData(
        code="WATER_LINE_LOCATE_MARK",
        name="Underground Water Line Locate & Mark",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Locate and mark underground water line with electromagnetic locator. Before excavation.",
    ),

    "TRAP_PRIMER_INSTALL": LaborTemplateData(
        code="TRAP_PRIMER_INSTALL",
        name="Trap Primer Valve — Install",
        category="service",
        base_hours=1.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["TRAP_PRIMER_KIT"],
        notes="Install trap primer on floor drain to prevent P-trap dry-out and sewer gas.",
    ),

    "EXPANSION_JOINT_REPAIR": LaborTemplateData(
        code="EXPANSION_JOINT_REPAIR",
        name="Pipe Expansion Joint / Flexible Connector Repair",
        category="service",
        base_hours=1.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=[],
        notes="Replace failed expansion joint or flex connector on hot water riser or commercial piping.",
    ),

    "WATER_METER_RELOCATE": LaborTemplateData(
        code="WATER_METER_RELOCATE",
        name="Water Meter Box — Relocate / Raise to Grade",
        category="service",
        base_hours=2.0,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.25,
        applicable_assemblies=[],
        notes="Relocate or raise buried water meter box to grade. City coordination may be required.",
    ),

    "CLEANOUT_INSTALL_EXTERIOR": LaborTemplateData(
        code="CLEANOUT_INSTALL_EXTERIOR",
        name="Exterior Cleanout — Install / Relocate",
        category="service",
        base_hours=2.5,
        helper_required=True,
        helper_hours=2.0,
        disposal_hours=0.5,
        applicable_assemblies=["EXTERIOR_CLEANOUT_KIT"],
        notes="Install two-way exterior cleanout per UPC/IPC. Required for camera access. DFW code requirement.",
    ),

    "SHOWER_BODY_SPRAY_INSTALL": LaborTemplateData(
        code="SHOWER_BODY_SPRAY_INSTALL",
        name="Shower Body Spray / Jets — Install (per pair)",
        category="service",
        base_hours=2.0,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["BODY_SPRAY_KIT"],
        notes="Install body spray jets in shower wall. Per pair. Requires access and volume valve.",
    ),

    "DUAL_FLUSH_CONVERSION": LaborTemplateData(
        code="DUAL_FLUSH_CONVERSION",
        name="Toilet Dual-Flush Conversion Kit — Install",
        category="service",
        base_hours=0.5,
        helper_required=False,
        disposal_hours=0.0,
        applicable_assemblies=["DUAL_FLUSH_KIT"],
        notes="Convert standard toilet to dual-flush with retrofit kit. Water conservation upgrade.",
    ),
}


def get_template(code: str) -> Optional[LaborTemplateData]:
    """Get a labor template by code."""
    return LABOR_TEMPLATES.get(code)


def get_templates_by_category(category: str) -> dict[str, LaborTemplateData]:
    """Get all templates in a category."""
    return {k: v for k, v in LABOR_TEMPLATES.items() if v.category == category}


def list_template_codes() -> list[str]:
    return list(LABOR_TEMPLATES.keys())
