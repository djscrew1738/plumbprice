"""Patch script - Steps 2 & 3: Add canonical items and assemblies to supplier_service.py"""

filepath = "app/services/supplier_service.py"

# ── Step 2: New canonical items to add before closing } of CANONICAL_MAP (line 521) ──
new_canonical = '''
    # --- Tankless WH Descale Supplies -----------------------------------------------
    "wh.descale_solution_1gal": {
        "ferguson":    {"sku": "DESC-1G",   "name": "Tankless WH descale solution 1 gal",                "cost": 28.50},
        "moore_supply":{"sku": "DSOL-1G",   "name": "Descaler solution 1 gal",                            "cost": 25.75},
        "apex":        {"sku": "DESC-1G-A", "name": "WH descale solution 1 gal",                          "cost": 30.25},
    },
    # --- Expansion Tank --------------------------------------------------------------
    "wh.expansion_tank_2gal": {
        "ferguson":    {"sku": "ET-2",      "name": "Thermal expansion tank 2 gal 3/4\" NPT",            "cost": 42.50},
        "moore_supply":{"sku": "EXT-2G",    "name": "2 gal expansion tank",                               "cost": 38.75},
        "apex":        {"sku": "ET2-A",     "name": "Expansion tank 2 gal",                               "cost": 45.00},
    },
    # --- Water Hammer Arrestor -------------------------------------------------------
    "plumbing.hammer_arrester_c": {
        "ferguson":    {"sku": "HA-C",      "name": "Water hammer arrester size C 1/2\" SIPT",           "cost": 18.50},
        "moore_supply":{"sku": "WHA-C",     "name": "Size C hammer arrester",                              "cost": 16.75},
        "apex":        {"sku": "HA-C-A",    "name": "Water hammer arrester C",                             "cost": 20.00},
    },
    # --- Laundry Box -----------------------------------------------------------------
    "plumbing.laundry_outlet_box": {
        "ferguson":    {"sku": "LOB-STD",   "name": "Laundry outlet box hot/cold 3/4\" + 2\" drain",      "cost": 48.50},
        "moore_supply":{"sku": "LB-STD",    "name": "Washing machine outlet box",                          "cost": 43.75},
        "apex":        {"sku": "LOB-A",     "name": "Laundry outlet box",                                  "cost": 52.00},
    },
    # --- Ice Maker Line --------------------------------------------------------------
    "plumbing.ice_maker_line_25ft": {
        "ferguson":    {"sku": "IML-25",    "name": "Ice maker water line 1/4\" PEX 25ft",               "cost": 18.50},
        "moore_supply":{"sku": "ICELN-25",  "name": "1/4\" ice maker line 25ft",                           "cost": 16.75},
        "apex":        {"sku": "IML25-A",   "name": "Ice maker line 25ft 1/4\"",                           "cost": 19.75},
    },
    "plumbing.angle_stop_quarter_inch": {
        "ferguson":    {"sku": "AS-14",     "name": "Angle stop 1/4\" OD x 3/8\" comp",                  "cost": 9.50},
        "moore_supply":{"sku": "ASTOP-14",  "name": "1/4\" angle stop",                                    "cost": 8.75},
        "apex":        {"sku": "AS14-A",    "name": "1/4\" OD angle stop",                                 "cost": 10.25},
    },
    # --- Mixing Valve ----------------------------------------------------------------
    "wh.mixing_valve_3way": {
        "ferguson":    {"sku": "MV-3W",     "name": "Thermostatic mixing valve 3/4\" in/out adjustable", "cost": 68.50},
        "moore_supply":{"sku": "TMV-34",    "name": "3/4\" thermostatic mixing valve",                    "cost": 62.75},
        "apex":        {"sku": "TMV-A",     "name": "3/4\" mixing valve adjustable",                       "cost": 72.00},
    },
    # --- Shower Cartridge ------------------------------------------------------------
    "shower.moen_posiTemp_1222": {
        "ferguson":    {"sku": "MOE-1222",  "name": "Moen Posi-Temp 1222 cartridge",                     "cost": 32.50},
        "moore_supply":{"sku": "M-1222",    "name": "Moen 1222 shower cartridge",                          "cost": 29.75},
        "apex":        {"sku": "M1222-A",   "name": "Moen Posi-Temp 1222",                                 "cost": 34.50},
    },
    "shower.delta_monitor_r10000": {
        "ferguson":    {"sku": "D-R10000",  "name": "Delta Monitor R10000-UNBX cartridge",               "cost": 38.50},
        "moore_supply":{"sku": "DR10000",   "name": "Delta R10000 shower cartridge",                       "cost": 35.75},
        "apex":        {"sku": "DR10K-A",   "name": "Delta Monitor cartridge R10000",                      "cost": 41.00},
    },
    # --- Tub Drain Parts -------------------------------------------------------------
    "tub.drain_assembly_chrome": {
        "ferguson":    {"sku": "TDA-CHR",   "name": "Tub drain assembly trip lever chrome",              "cost": 42.50},
        "moore_supply":{"sku": "TDAC",      "name": "Chrome tub drain assembly",                           "cost": 38.75},
        "apex":        {"sku": "TDA-C-A",   "name": "Tub trip lever drain assembly chrome",                "cost": 45.00},
    },
    "tub.overflow_plate_chrome": {
        "ferguson":    {"sku": "TOP-CHR",   "name": "Tub overflow plate chrome",                          "cost": 12.50},
        "moore_supply":{"sku": "TOPC",      "name": "Chrome overflow plate",                               "cost": 11.25},
        "apex":        {"sku": "TOP-C-A",   "name": "Chrome tub overflow plate",                           "cost": 13.50},
    },
    # --- Kitchen Sink Parts ----------------------------------------------------------
    "sink.basket_strainer_chrome": {
        "ferguson":    {"sku": "BS-CHR",    "name": "Kitchen sink basket strainer stainless",            "cost": 22.50},
        "moore_supply":{"sku": "BSC",       "name": "Stainless basket strainer",                           "cost": 19.75},
        "apex":        {"sku": "BS-C-A",    "name": "Kitchen basket strainer SS",                          "cost": 24.50},
    },
    "sink.ptrap_1p5_abs": {
        "ferguson":    {"sku": "PT-1.5",    "name": "P-trap 1-1/2\" ABS with slip joint",                "cost": 9.50},
        "moore_supply":{"sku": "PTR-15",    "name": "1.5\" ABS P-trap",                                    "cost": 8.75},
        "apex":        {"sku": "PT15-A",    "name": "1.5\" ABS P-trap slip",                               "cost": 10.25},
    },
    "sink.supply_line_braided_12in": {
        "ferguson":    {"sku": "BSL-12",    "name": "Braided SS supply line 12\" 3/8\" comp x 1/2\" FIP","cost": 8.50},
        "moore_supply":{"sku": "BSSL-12",   "name": "12\" braided supply line",                            "cost": 7.75},
        "apex":        {"sku": "BSL12-A",   "name": "12\" SS braided supply line",                         "cost": 9.25},
    },
    # --- Hose Bib --------------------------------------------------------------------
    "outdoor.frost_free_sillcock_12in": {
        "ferguson":    {"sku": "FFS-12",    "name": "Frost-free sillcock 12\" reach 3/4\" MIP",          "cost": 28.50},
        "moore_supply":{"sku": "FFSC-12",   "name": "12\" frost-free hose bib",                            "cost": 25.75},
        "apex":        {"sku": "FFS12-A",   "name": "Frost-free sillcock 12\"",                            "cost": 30.25},
    },
    # --- Sump Pump -------------------------------------------------------------------
    "plumbing.sump_pump_1_3hp": {
        "ferguson":    {"sku": "SP-13HP",   "name": "Zoeller M53 1/3HP submersible sump pump",           "cost": 148.50},
        "moore_supply":{"sku": "SPUMP-13",  "name": "1/3HP sump pump submersible",                         "cost": 135.75},
        "apex":        {"sku": "SP13-A",    "name": "1/3HP submersible sump pump",                         "cost": 158.00},
    },
    "plumbing.sump_basin_18in": {
        "ferguson":    {"sku": "SB-18",     "name": "Sump basin 18\" x 22\" poly with lid",              "cost": 42.50},
        "moore_supply":{"sku": "SBAS-18",   "name": "18\" sump basin and lid",                             "cost": 38.75},
        "apex":        {"sku": "SB18-A",    "name": "18\" poly sump basin",                                "cost": 45.00},
    },
    "plumbing.check_valve_1p5in": {
        "ferguson":    {"sku": "CV-1.5",    "name": "Check valve 1-1/2\" swing type",                    "cost": 18.50},
        "moore_supply":{"sku": "CVS-15",    "name": "1.5\" swing check valve",                             "cost": 16.75},
        "apex":        {"sku": "CV15-A",    "name": "1.5\" check valve",                                   "cost": 19.75},
    },
'''

# ── Step 3: New assemblies to add before closing } of MATERIAL_ASSEMBLIES (line 911) ──
new_assemblies = '''
    "TANKLESS_DESCALE_KIT": {
        "name": "Tankless WH Descale Kit",
        "labor_template": "TANKLESS_WH_DESCALE",
        "items": {"wh.descale_solution_1gal": 1},
    },
    "EXPANSION_TANK_KIT": {
        "name": "WH Expansion Tank Kit",
        "labor_template": "EXPANSION_TANK_INSTALL",
        "items": {"wh.expansion_tank_2gal": 1},
    },
    "HAMMER_ARRESTER_KIT": {
        "name": "Water Hammer Arrestor Kit",
        "labor_template": "WATER_HAMMER_ARRESTER",
        "items": {"plumbing.hammer_arrester_c": 2},
    },
    "LAUNDRY_BOX_KIT": {
        "name": "Laundry Outlet Box Kit",
        "labor_template": "LAUNDRY_BOX_REPLACE",
        "items": {"plumbing.laundry_outlet_box": 1, "sink.supply_line_braided_12in": 2},
    },
    "ICE_MAKER_KIT": {
        "name": "Ice Maker Line Kit",
        "labor_template": "ICE_MAKER_LINE_INSTALL",
        "items": {
            "plumbing.ice_maker_line_25ft": 1,
            "plumbing.angle_stop_quarter_inch": 1,
        },
    },
    "MIXING_VALVE_KIT": {
        "name": "Thermostatic Mixing Valve Kit",
        "labor_template": "MIXING_VALVE_REPLACE",
        "items": {"wh.mixing_valve_3way": 1},
    },
    "SHOWER_CARTRIDGE_KIT": {
        "name": "Shower/Tub Valve Cartridge Kit",
        "labor_template": "SHOWER_VALVE_CARTRIDGE",
        "items": {"shower.moen_posiTemp_1222": 1},
    },
    "TUB_DRAIN_KIT": {
        "name": "Bathtub Drain Assembly Kit",
        "labor_template": "BATHTUB_DRAIN_REPAIR",
        "items": {
            "tub.drain_assembly_chrome": 1,
            "tub.overflow_plate_chrome": 1,
        },
    },
    "KITCHEN_SINK_KIT": {
        "name": "Kitchen Sink Replacement Kit",
        "labor_template": "SINK_REPLACE_KITCHEN",
        "items": {
            "sink.basket_strainer_chrome":   2,
            "sink.ptrap_1p5_abs":            1,
            "sink.supply_line_braided_12in": 2,
        },
    },
    "BATH_SINK_KIT": {
        "name": "Bathroom Sink Replacement Kit",
        "labor_template": "SINK_REPLACE_BATH",
        "items": {
            "sink.ptrap_1p5_abs":            1,
            "sink.supply_line_braided_12in": 2,
        },
    },
    "HOSE_BIB_FREEZE_KIT": {
        "name": "Frost-Free Hose Bib Repair Kit",
        "labor_template": "HOSE_BIB_FREEZE_REPAIR",
        "items": {"outdoor.frost_free_sillcock_12in": 1},
    },
    "SUMP_PUMP_KIT": {
        "name": "Sump Pump Installation Kit",
        "labor_template": "SUMP_PUMP_INSTALL",
        "items": {
            "plumbing.sump_pump_1_3hp":   1,
            "plumbing.sump_basin_18in":   1,
            "plumbing.check_valve_1p5in": 1,
        },
    },
'''

with open(filepath, 'r') as f:
    content = f.read()

# ── Patch CANONICAL_MAP ──────────────────────────────────────────────────────────────
# The closing } is at the end of the CANONICAL_MAP dict (line 521)
# Find the boundary: last item before the closing } of CANONICAL_MAP
# We look for the outdoor drain supplies section (last section added previously)
canonical_marker = '''    "drain.filter_fabric_roll": {
        "ferguson":    {"sku": "DFF-25",    "name": "Filter fabric / landscape fabric roll 25ft",  "cost": 18.50},
        "moore_supply":{"sku": "FF-25",     "name": "Landscape filter fabric 25ft roll",           "cost": 16.75},
        "apex":        {"sku": "DFF25-A",   "name": "Filter fabric roll 25ft",                      "cost": 19.75},
    },
}


MATERIAL_ASSEMBLIES'''

canonical_replacement = '''    "drain.filter_fabric_roll": {
        "ferguson":    {"sku": "DFF-25",    "name": "Filter fabric / landscape fabric roll 25ft",  "cost": 18.50},
        "moore_supply":{"sku": "FF-25",     "name": "Landscape filter fabric 25ft roll",           "cost": 16.75},
        "apex":        {"sku": "DFF25-A",   "name": "Filter fabric roll 25ft",                      "cost": 19.75},
    },
''' + new_canonical + '''}


MATERIAL_ASSEMBLIES'''

if canonical_marker in content:
    content = content.replace(canonical_marker, canonical_replacement)
    print("CANONICAL_MAP patched OK")
else:
    print("ERROR: Could not find CANONICAL_MAP marker")
    # Debug: show what's around line 518-525
    lines = content.split('\n')
    for i, line in enumerate(lines[510:530], start=511):
        print(f"{i}: {repr(line)}")

# ── Patch MATERIAL_ASSEMBLIES ────────────────────────────────────────────────────────
assemblies_marker = '''    "OUTDOOR_DRAIN_KIT": {
        "name": "French / Yard Drain Kit (per 10 LF)",
        "labor_template": "OUTDOOR_DRAIN_INSTALL",
        "items": {
            "drain.perf_pipe_4in_10ft": 1,
            "drain.popup_emitter_4in":  1,
            "drain.filter_fabric_roll": 0.4,  # ~10ft of 25ft roll
        },
    },
}'''

assemblies_replacement = '''    "OUTDOOR_DRAIN_KIT": {
        "name": "French / Yard Drain Kit (per 10 LF)",
        "labor_template": "OUTDOOR_DRAIN_INSTALL",
        "items": {
            "drain.perf_pipe_4in_10ft": 1,
            "drain.popup_emitter_4in":  1,
            "drain.filter_fabric_roll": 0.4,  # ~10ft of 25ft roll
        },
    },
''' + new_assemblies + '\n}'

if assemblies_marker in content:
    content = content.replace(assemblies_marker, assemblies_replacement)
    print("MATERIAL_ASSEMBLIES patched OK")
else:
    print("ERROR: Could not find MATERIAL_ASSEMBLIES marker")

with open(filepath, 'w') as f:
    f.write(content)

print("supplier_service.py written")
