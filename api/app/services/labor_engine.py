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
}


def get_template(code: str) -> Optional[LaborTemplateData]:
    """Get a labor template by code."""
    return LABOR_TEMPLATES.get(code)


def get_templates_by_category(category: str) -> dict[str, LaborTemplateData]:
    """Get all templates in a category."""
    return {k: v for k, v in LABOR_TEMPLATES.items() if v.category == category}


def list_template_codes() -> list[str]:
    return list(LABOR_TEMPLATES.keys())
