"""Patch step 2: Add canonical items to CANONICAL_MAP (find actual closing marker)"""

filepath = "app/services/supplier_service.py"

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

with open(filepath, 'r') as f:
    content = f.read()

# The CANONICAL_MAP closes at line 521 (just '}' followed by two blank lines and MATERIAL_ASSEMBLIES comment)
# Find the exact marker: last dict entry closes with '},' then '}' on its own line
# Use the access_panel entry as anchor
canonical_close = '    },\n}\n\n\n# \u2500\u2500\u2500 Material Assemblies'

if canonical_close in content:
    replacement = '    },\n' + new_canonical + '\n}\n\n\n# \u2500\u2500\u2500 Material Assemblies'
    content = content.replace(canonical_close, replacement, 1)
    print("CANONICAL_MAP patched OK")
else:
    # Try alternate: just the closing brace
    lines = content.split('\n')
    # Find line with just '}' that follows the reroute.access_panel entry
    for i, line in enumerate(lines):
        if '"reroute.access_panel_12x12"' in line:
            # Find the closing } after this
            for j in range(i, min(i+10, len(lines))):
                if lines[j].strip() == '}':
                    print(f"Found closing at line {j+1}: {repr(lines[j])}")
                    print(f"Next line: {repr(lines[j+1] if j+1 < len(lines) else 'EOF')}")
                    break
            break
    print("ERROR: Could not find canonical_close marker")

with open(filepath, 'w') as f:
    f.write(content)
print("Done")
