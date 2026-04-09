"""Patch script - Step 1: Add 20 new labor templates to labor_engine.py"""
import re

filepath = "app/services/labor_engine.py"

new_templates = '''
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
'''

with open(filepath, 'r') as f:
    content = f.read()

# Find the OUTDOOR_DRAIN_INSTALL closing and insert before the closing }
old = '''    "OUTDOOR_DRAIN_INSTALL": LaborTemplateData(
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
            "Scale hours proportionally (e.g., 30 LF = 3\u00d7 base)."
        ),
    ),
}'''

new = '''    "OUTDOOR_DRAIN_INSTALL": LaborTemplateData(
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
            "Scale hours proportionally (e.g., 30 LF = 3\u00d7 base)."
        ),
    ),
''' + new_templates + '\n}'

if old in content:
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print("SUCCESS: labor_engine.py patched")
else:
    print("ERROR: Could not find target string")
    # Show what the closing looks like
    idx = content.find('"OUTDOOR_DRAIN_INSTALL"')
    print(repr(content[idx:idx+400]))
