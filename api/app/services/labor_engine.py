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
}


def get_template(code: str) -> Optional[LaborTemplateData]:
    """Get a labor template by code."""
    return LABOR_TEMPLATES.get(code)


def get_templates_by_category(category: str) -> dict[str, LaborTemplateData]:
    """Get all templates in a category."""
    return {k: v for k, v in LABOR_TEMPLATES.items() if v.category == category}


def list_template_codes() -> list[str]:
    return list(LABOR_TEMPLATES.keys())
