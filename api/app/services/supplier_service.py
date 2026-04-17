"""
Supplier Service — Material cost lookup and comparison.
Canonical item → supplier SKU → current cost.
"""

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from app.models.suppliers import Supplier, SupplierProduct
from app.services.pricing_engine import MaterialItem
from app.services.data_sources.price_enrichment import get_enrichment_service

logger = structlog.get_logger()

# ─── Canonical Item → Supplier Pricing ───────────────────────────────────────
# DFW wholesale prices — 2025 Q1. DB lookup takes precedence when available.
# Format: { canonical_id: { supplier_slug: { sku, name, cost } } }
CANONICAL_MAP: dict[str, dict[str, dict]] = {
    # ── Toilet ───────────────────────────────────────────────────────────────
    "toilet.wax_ring": {
        "ferguson":    {"sku": "WX-100",   "name": "Wax Ring w/ Sleeve",         "cost": 8.42},
        "moore_supply":{"sku": "WR-STD",   "name": "Wax Ring w/ Sleeve",         "cost": 7.85},
        "apex":        {"sku": "WR-200",   "name": "Wax Ring w/ Sleeve",         "cost": 8.95},
    },
    "toilet.closet_bolts": {
        "ferguson":    {"sku": "CB-BRASS",  "name": "Brass Closet Bolt Set",      "cost": 6.18},
        "moore_supply":{"sku": "CB-2PK",   "name": "Brass Closet Bolt Set",      "cost": 5.50},
        "apex":        {"sku": "CB-STD",   "name": "Brass Closet Bolt Set",      "cost": 6.50},
    },
    "toilet.supply_line_12": {
        "ferguson":    {"sku": "SL-12SS",  "name": "12\" Braided SS Supply Line", "cost": 10.95},
        "moore_supply":{"sku": "SL12-BR",  "name": "12\" Braided SS Supply Line", "cost": 9.85},
        "apex":        {"sku": "SL-12A",   "name": "12\" Braided SS Supply Line", "cost": 11.25},
    },
    # ── Water Heater — Gas 50G ────────────────────────────────────────────────
    "wh.50g_gas_unit": {
        "ferguson":    {"sku": "XG50T06EC3",  "name": "Rheem 50G Gas WH (6yr)",    "cost": 598.00},
        "moore_supply":{"sku": "AOS-GCG50",   "name": "AO Smith 50G Gas WH",       "cost": 574.00},
        "apex":        {"sku": "PM50-2",      "name": "ProMax 50G Gas WH",         "cost": 625.00},
    },
    "wh.gas_flex_connector_18": {
        "ferguson":    {"sku": "GFC-18SS",  "name": "18\" Stainless Gas Flex",     "cost": 14.50},
        "moore_supply":{"sku": "GF-18",     "name": "18\" Stainless Gas Flex",     "cost": 12.95},
        "apex":        {"sku": "GFC18A",    "name": "18\" Stainless Gas Flex",     "cost": 15.25},
    },
    "wh.expansion_tank_2g": {
        "ferguson":    {"sku": "ST-2",      "name": "2-Gal Thermal Expansion Tank","cost": 42.80},
        "moore_supply":{"sku": "XT-2GAL",   "name": "2-Gal Thermal Expansion Tank","cost": 40.25},
        "apex":        {"sku": "ET-2A",     "name": "2-Gal Thermal Expansion Tank","cost": 44.95},
    },
    "wh.tp_valve_075": {
        "ferguson":    {"sku": "TP-3/4",    "name": "3/4\" T&P Relief Valve",      "cost": 22.95},
        "moore_supply":{"sku": "TPV-75",    "name": "3/4\" T&P Relief Valve",      "cost": 21.50},
        "apex":        {"sku": "TP34A",     "name": "3/4\" T&P Relief Valve",      "cost": 23.95},
    },
    "wh.dielectric_union_pair": {
        "ferguson":    {"sku": "DU-PAIR",   "name": "Dielectric Union Pair",       "cost": 18.40},
        "moore_supply":{"sku": "DUP-STD",   "name": "Dielectric Union Pair",       "cost": 16.95},
        "apex":        {"sku": "DU-2PK",    "name": "Dielectric Union Pair",       "cost": 19.50},
    },
    # ── Water Heater — Attic extras ───────────────────────────────────────────
    "wh.drain_pan_26": {
        "ferguson":    {"sku": "DP-26",     "name": "26\" WH Drain Pan",           "cost": 28.95},
        "moore_supply":{"sku": "WDP-26",    "name": "26\" WH Drain Pan",           "cost": 26.50},
        "apex":        {"sku": "DP26A",     "name": "26\" WH Drain Pan",           "cost": 30.25},
    },
    "wh.overflow_line_075": {
        "ferguson":    {"sku": "OL-3/4",    "name": "3/4\" CPVC Overflow Line Kit","cost": 8.50},
        "moore_supply":{"sku": "OVL-75",    "name": "3/4\" CPVC Overflow Line Kit","cost": 7.95},
        "apex":        {"sku": "OL34A",     "name": "3/4\" CPVC Overflow Line Kit","cost": 9.25},
    },
    # ── Water Heater — Gas 40G ────────────────────────────────────────────────
    "wh.40g_gas_unit": {
        "ferguson":    {"sku": "XG40T06EC3","name": "Rheem 40G Gas WH (6yr)",     "cost": 524.00},
        "moore_supply":{"sku": "AOS-GCG40", "name": "AO Smith 40G Gas WH",        "cost": 498.00},
        "apex":        {"sku": "PM40-2",    "name": "ProMax 40G Gas WH",          "cost": 548.00},
    },
    # ── Water Heater — Electric 50G ───────────────────────────────────────────
    "wh.50g_electric_unit": {
        "ferguson":    {"sku": "XE50T06HD", "name": "Rheem 50G Elec WH (6yr)",   "cost": 548.00},
        "moore_supply":{"sku": "AOS-EE650", "name": "AO Smith 50G Elec WH",      "cost": 519.00},
        "apex":        {"sku": "PME50-2",   "name": "ProMax 50G Elec WH",        "cost": 572.00},
    },
    "wh.water_supply_line_18": {
        "ferguson":    {"sku": "WSL-18SS",  "name": "18\" Braided SS Supply Line", "cost": 12.50},
        "moore_supply":{"sku": "SL18-BR",   "name": "18\" Braided SS Supply Line", "cost": 11.25},
        "apex":        {"sku": "SL-18A",    "name": "18\" Braided SS Supply Line", "cost": 13.50},
    },
    # ── Water Heater — Tankless Gas ───────────────────────────────────────────
    "wh.tankless_navien_180k": {
        "ferguson":    {"sku": "NPE-180A2", "name": "Navien 180K BTU Tankless",   "cost": 1195.00},
        "moore_supply":{"sku": "NPE180A",   "name": "Navien 180K BTU Tankless",   "cost": 1149.00},
        "apex":        {"sku": "NPE-180",   "name": "Navien 180K BTU Tankless",   "cost": 1225.00},
    },
    "wh.gas_flex_connector_24": {
        "ferguson":    {"sku": "GFC-24SS",  "name": "24\" Stainless Gas Flex",    "cost": 16.95},
        "moore_supply":{"sku": "GF-24",     "name": "24\" Stainless Gas Flex",    "cost": 15.25},
        "apex":        {"sku": "GFC24A",    "name": "24\" Stainless Gas Flex",    "cost": 17.95},
    },
    "wh.tankless_water_filter": {
        "ferguson":    {"sku": "WF-INLINE", "name": "Inline Sediment Filter",     "cost": 18.50},
        "moore_supply":{"sku": "IF-STD",    "name": "Inline Sediment Filter",     "cost": 17.25},
        "apex":        {"sku": "WF-A",      "name": "Inline Sediment Filter",     "cost": 19.50},
    },
    # ── PRV ───────────────────────────────────────────────────────────────────
    "prv.watts_3_4": {
        "ferguson":    {"sku": "25AUB-Z3",  "name": "Watts 3/4\" PRV (25-75 PSI)","cost": 48.50},
        "moore_supply":{"sku": "WTS-25AUB", "name": "Watts 3/4\" PRV",            "cost": 45.95},
        "apex":        {"sku": "PRV-34A",   "name": "Watts 3/4\" PRV",            "cost": 51.25},
    },
    "prv.union_3_4": {
        "ferguson":    {"sku": "UN-3/4",    "name": "3/4\" FIP Union",            "cost": 6.95},
        "moore_supply":{"sku": "U34-STD",   "name": "3/4\" FIP Union",            "cost": 6.25},
        "apex":        {"sku": "UN34A",     "name": "3/4\" FIP Union",            "cost": 7.50},
    },
    # ── Hose Bib ─────────────────────────────────────────────────────────────
    "hose_bib.frost_free_12": {
        "ferguson":    {"sku": "HB12-FF",   "name": "12\" Frost-Free Hose Bib",   "cost": 22.95},
        "moore_supply":{"sku": "FFB-12",    "name": "12\" Frost-Free Hose Bib",   "cost": 21.25},
        "apex":        {"sku": "HB12A",     "name": "12\" Frost-Free Hose Bib",   "cost": 24.50},
    },
    "hose_bib.escutcheon_chrome": {
        "ferguson":    {"sku": "ESC-CH",    "name": "Chrome Escutcheon Plate",    "cost": 4.25},
        "moore_supply":{"sku": "EP-CHR",    "name": "Chrome Escutcheon Plate",    "cost": 3.95},
        "apex":        {"sku": "ESC-A",     "name": "Chrome Escutcheon Plate",    "cost": 4.75},
    },
    # ── Shower Valve ─────────────────────────────────────────────────────────
    "shower.cartridge_moen_1225": {
        "ferguson":    {"sku": "1225",      "name": "Moen 1225 Cartridge",        "cost": 32.50},
        "moore_supply":{"sku": "MN-1225",   "name": "Moen 1225 Cartridge",        "cost": 30.95},
        "apex":        {"sku": "MON1225",   "name": "Moen 1225 Cartridge",        "cost": 34.95},
    },
    "shower.seat_washers_kit": {
        "ferguson":    {"sku": "SW-KIT",    "name": "Seat & Washer Kit",          "cost": 8.95},
        "moore_supply":{"sku": "SWK-STD",   "name": "Seat & Washer Kit",          "cost": 8.25},
        "apex":        {"sku": "SWK-A",     "name": "Seat & Washer Kit",          "cost": 9.50},
    },
    "shower.trim_kit_brushed_nickel": {
        "ferguson":    {"sku": "TK-BN",     "name": "Shower Trim Kit (Brushed Nickel)","cost": 42.95},
        "moore_supply":{"sku": "STK-BN",    "name": "Shower Trim Kit (Brushed Nickel)","cost": 39.95},
        "apex":        {"sku": "TK-BNA",    "name": "Shower Trim Kit (Brushed Nickel)","cost": 45.50},
    },
    # ── Kitchen Faucet ───────────────────────────────────────────────────────
    "kitchen.supply_lines_20_pair": {
        "ferguson":    {"sku": "SL-20PR",   "name": "20\" SS Supply Lines (pair)", "cost": 18.95},
        "moore_supply":{"sku": "KSL-20",    "name": "20\" SS Supply Lines (pair)", "cost": 17.50},
        "apex":        {"sku": "SL20PA",    "name": "20\" SS Supply Lines (pair)", "cost": 20.25},
    },
    "kitchen.basket_strainer": {
        "ferguson":    {"sku": "BS-STD",    "name": "Kitchen Basket Strainer",    "cost": 24.95},
        "moore_supply":{"sku": "BKS-STD",   "name": "Kitchen Basket Strainer",    "cost": 22.95},
        "apex":        {"sku": "BSA-STD",   "name": "Kitchen Basket Strainer",    "cost": 26.50},
    },
    "kitchen.teflon_tape": {
        "ferguson":    {"sku": "TT-PINK",   "name": "Pink PTFE Tape (gas-rated)", "cost": 3.50},
        "moore_supply":{"sku": "TT-WH",     "name": "PTFE Thread Tape",           "cost": 2.95},
        "apex":        {"sku": "TTA",       "name": "PTFE Thread Tape",           "cost": 3.75},
    },
    # ── Garbage Disposal ─────────────────────────────────────────────────────
    "disposal.mounting_ring_kit": {
        "ferguson":    {"sku": "ISE-MNT",   "name": "Disposal Mounting Ring Kit", "cost": 12.95},
        "moore_supply":{"sku": "MRK-STD",   "name": "Disposal Mounting Ring Kit", "cost": 11.95},
        "apex":        {"sku": "MRK-A",     "name": "Disposal Mounting Ring Kit", "cost": 13.95},
    },
    "disposal.drain_elbow_90": {
        "ferguson":    {"sku": "DE-90",     "name": "Disposal 90° Drain Elbow",   "cost": 8.50},
        "moore_supply":{"sku": "DEL-90",    "name": "Disposal 90° Drain Elbow",   "cost": 7.95},
        "apex":        {"sku": "DE90A",     "name": "Disposal 90° Drain Elbow",   "cost": 9.25},
    },
    "disposal.power_cord_3prong": {
        "ferguson":    {"sku": "PC-3P",     "name": "Disposal Power Cord (3-prong)","cost": 15.95},
        "moore_supply":{"sku": "DPC-3P",    "name": "Disposal Power Cord (3-prong)","cost": 14.95},
        "apex":        {"sku": "PC3A",      "name": "Disposal Power Cord (3-prong)","cost": 16.95},
    },
    # ── Lavatory Faucet ───────────────────────────────────────────────────────
    "lav.supply_lines_12_pair": {
        "ferguson":    {"sku": "LS-12PR",   "name": "12\" Lav Supply Lines (pair)","cost": 14.95},
        "moore_supply":{"sku": "LSL-12",    "name": "12\" Lav Supply Lines (pair)","cost": 13.95},
        "apex":        {"sku": "LS12PA",    "name": "12\" Lav Supply Lines (pair)","cost": 15.95},
    },
    "lav.pop_up_drain": {
        "ferguson":    {"sku": "PU-CHR",    "name": "Pop-Up Drain Assembly (Chrome)","cost": 18.95},
        "moore_supply":{"sku": "PUD-CH",    "name": "Pop-Up Drain Assembly (Chrome)","cost": 17.50},
        "apex":        {"sku": "PUA-CH",    "name": "Pop-Up Drain Assembly (Chrome)","cost": 20.25},
    },
    # ── Angle Stop ────────────────────────────────────────────────────────────
    "angle_stop.quarter_turn_3_8": {
        "ferguson":    {"sku": "AS-3/8QT",  "name": "3/8\" OD Quarter-Turn Stop",  "cost": 8.95},
        "moore_supply":{"sku": "QTS-38",    "name": "3/8\" OD Quarter-Turn Stop",  "cost": 8.25},
        "apex":        {"sku": "AS38A",     "name": "3/8\" OD Quarter-Turn Stop",  "cost": 9.75},
    },
    "angle_stop.supply_line_12": {
        "ferguson":    {"sku": "SL-12-38",  "name": "12\" Supply Line 3/8\"",       "cost": 6.95},
        "moore_supply":{"sku": "SL-38-12",  "name": "12\" Supply Line 3/8\"",       "cost": 6.25},
        "apex":        {"sku": "SL38-12A",  "name": "12\" Supply Line 3/8\"",       "cost": 7.50},
    },
    # ── P-Trap ────────────────────────────────────────────────────────────────
    "ptrap.chrome_1_5_inch": {
        "ferguson":    {"sku": "PT-1.5CH",  "name": "1-1/2\" Chrome P-Trap",        "cost": 14.95},
        "moore_supply":{"sku": "CPT-15",    "name": "1-1/2\" Chrome P-Trap",        "cost": 13.95},
        "apex":        {"sku": "PT15A",     "name": "1-1/2\" Chrome P-Trap",        "cost": 15.95},
    },
    "ptrap.extension_tube_12": {
        "ferguson":    {"sku": "ET-12CH",   "name": "12\" Chrome Extension Tube",   "cost": 6.50},
        "moore_supply":{"sku": "EXT-12",    "name": "12\" Chrome Extension Tube",   "cost": 6.25},
        "apex":        {"sku": "ET12A",     "name": "12\" Chrome Extension Tube",   "cost": 7.25},
    },
    # ── Expansion Tank (standalone) ───────────────────────────────────────────
    "exp_tank.2gal_thermal": {
        "ferguson":    {"sku": "ST-2",      "name": "2-Gal Thermal Expansion Tank","cost": 42.80},
        "moore_supply":{"sku": "XT-2GAL",   "name": "2-Gal Thermal Expansion Tank","cost": 40.25},
        "apex":        {"sku": "ET-2A",     "name": "2-Gal Thermal Expansion Tank","cost": 44.95},
    },
    "exp_tank.nipple_34": {
        "ferguson":    {"sku": "NIP-34x4",  "name": "3/4\" NPT Nipple 4\"",          "cost": 3.25},
        "moore_supply":{"sku": "N34-4",     "name": "3/4\" NPT Nipple 4\"",          "cost": 2.95},
        "apex":        {"sku": "NP34A",     "name": "3/4\" NPT Nipple 4\"",          "cost": 3.75},
    },
    # ── Water Softener ────────────────────────────────────────────────────────
    "softener.unit_48k_grain": {
        "ferguson":    {"sku": "WS48K-FRG", "name": "48K Grain Water Softener",    "cost": 695.00},
        "moore_supply":{"sku": "WS48K-MRS", "name": "48K Grain Water Softener",    "cost": 649.00},
        "apex":        {"sku": "WS48K-APX", "name": "48K Grain Water Softener",    "cost": 725.00},
    },
    "softener.bypass_valve_1in": {
        "ferguson":    {"sku": "BV-1NPT",   "name": "1\" Bypass Valve Assembly",    "cost": 28.50},
        "moore_supply":{"sku": "BVA-1",     "name": "1\" Bypass Valve Assembly",    "cost": 26.95},
        "apex":        {"sku": "BV1A",      "name": "1\" Bypass Valve Assembly",    "cost": 30.25},
    },
    "softener.brine_line_kit": {
        "ferguson":    {"sku": "BLK-STD",   "name": "Brine Line & Fittings Kit",   "cost": 14.95},
        "moore_supply":{"sku": "BLK-MRS",   "name": "Brine Line & Fittings Kit",   "cost": 13.50},
        "apex":        {"sku": "BLK-APX",   "name": "Brine Line & Fittings Kit",   "cost": 15.95},
    },
    "softener.supply_line_pair_1in": {
        "ferguson":    {"sku": "SLP-1-24",  "name": "1\" SS Supply Lines (pair, 24\")", "cost": 32.95},
        "moore_supply":{"sku": "SLP1-24",   "name": "1\" SS Supply Lines (pair, 24\")", "cost": 30.50},
        "apex":        {"sku": "SL1PA24",   "name": "1\" SS Supply Lines (pair, 24\")", "cost": 34.95},
    },
    # ── Tub / Shower Combo Valve ──────────────────────────────────────────────
    "tub_shower.moen_posi_temp_valve": {
        "ferguson":    {"sku": "M82606",    "name": "Moen Posi-Temp Tub/Shower Valve","cost": 58.95},
        "moore_supply":{"sku": "MN-M82606", "name": "Moen Posi-Temp Tub/Shower Valve","cost": 55.50},
        "apex":        {"sku": "M82606-APX","name": "Moen Posi-Temp Tub/Shower Valve","cost": 62.50},
    },
    "tub_shower.diverter_tee": {
        "ferguson":    {"sku": "DT-12",     "name": "Tub Spout Diverter Tee",       "cost": 12.95},
        "moore_supply":{"sku": "DTT-STD",   "name": "Tub Spout Diverter Tee",       "cost": 11.95},
        "apex":        {"sku": "DT12A",     "name": "Tub Spout Diverter Tee",       "cost": 13.95},
    },
    "tub_shower.tub_spout_chrome": {
        "ferguson":    {"sku": "TS-CHR",    "name": "Tub Spout w/ Diverter (Chrome)","cost": 22.95},
        "moore_supply":{"sku": "TSP-CHR",   "name": "Tub Spout w/ Diverter (Chrome)","cost": 21.25},
        "apex":        {"sku": "TSC-APX",   "name": "Tub Spout w/ Diverter (Chrome)","cost": 24.95},
    },
    "tub_shower.trim_kit_chrome": {
        "ferguson":    {"sku": "TK-CHR",    "name": "Tub/Shower Trim Kit (Chrome)",  "cost": 48.95},
        "moore_supply":{"sku": "STK-CHR",   "name": "Tub/Shower Trim Kit (Chrome)",  "cost": 45.50},
        "apex":        {"sku": "TK-CHRA",   "name": "Tub/Shower Trim Kit (Chrome)",  "cost": 52.50},
    },
    # ── Toilet Repair Parts ───────────────────────────────────────────────────
    "toilet.flapper_korky": {
        "ferguson":    {"sku": "K-4010BP",  "name": "Korky Universal Flapper",       "cost": 7.25},
        "moore_supply":{"sku": "FLP-UNI",   "name": "Korky Universal Flapper",       "cost": 6.75},
        "apex":        {"sku": "KRK-4010",  "name": "Korky Universal Flapper",       "cost": 7.95},
    },
    "toilet.fill_valve_400a": {
        "ferguson":    {"sku": "FM-400A",   "name": "Fluidmaster 400A Fill Valve",   "cost": 12.95},
        "moore_supply":{"sku": "FM400A",    "name": "Fluidmaster 400A Fill Valve",   "cost": 11.95},
        "apex":        {"sku": "400A-APX",  "name": "Fluidmaster 400A Fill Valve",   "cost": 13.95},
    },
    "toilet.comfort_height_unit": {
        "ferguson":    {"sku": "K-3999",    "name": "Kohler Cimarron Comfort Height WC","cost": 285.00},
        "moore_supply":{"sku": "AMS-2887",  "name": "American Standard CH Toilet",   "cost": 268.00},
        "apex":        {"sku": "ELG-3817",  "name": "Elongated Comfort Height WC",   "cost": 298.00},
    },
    # ── Tub Spout ─────────────────────────────────────────────────────────────
    "tub_spout.diverter_chrome": {
        "ferguson":    {"sku": "TS-DCH",    "name": "Tub Spout w/ Diverter (Chrome)", "cost": 18.95},
        "moore_supply":{"sku": "TSP-DCH",   "name": "Tub Spout w/ Diverter (Chrome)", "cost": 17.50},
        "apex":        {"sku": "TSD-APX",   "name": "Tub Spout w/ Diverter (Chrome)", "cost": 20.25},
    },
    "tub_spout.nipple_half": {
        "ferguson":    {"sku": "NIP-1/2x4", "name": "1/2\" IPS Nipple 4\"",           "cost": 3.95},
        "moore_supply":{"sku": "N12-4",     "name": "1/2\" IPS Nipple 4\"",           "cost": 3.50},
        "apex":        {"sku": "NP12-4A",   "name": "1/2\" IPS Nipple 4\"",           "cost": 4.25},
    },
    # ── Shower Head ───────────────────────────────────────────────────────────
    "shower_head.standard_chrome": {
        "ferguson":    {"sku": "SH-CHR",    "name": "Moen 1.75 GPM Shower Head",     "cost": 24.95},
        "moore_supply":{"sku": "SHD-CH",    "name": "Delta 1.75 GPM Shower Head",    "cost": 22.95},
        "apex":        {"sku": "SH-APX",    "name": "Standard Chrome Shower Head",   "cost": 26.50},
    },
    "shower_head.arm_flange": {
        "ferguson":    {"sku": "SHA-CH",    "name": "Shower Arm & Flange Set",       "cost": 14.95},
        "moore_supply":{"sku": "SAF-CH",    "name": "Shower Arm & Flange Set",       "cost": 13.50},
        "apex":        {"sku": "SAF-APX",   "name": "Shower Arm & Flange Set",       "cost": 15.95},
    },
    # ── Lavatory Sink ─────────────────────────────────────────────────────────
    "lav_sink.drain_grid_chrome": {
        "ferguson":    {"sku": "DG-CH",     "name": "Lav Sink Drain Grid Assembly",  "cost": 16.95},
        "moore_supply":{"sku": "SDG-CH",    "name": "Lav Sink Drain Grid Assembly",  "cost": 15.50},
        "apex":        {"sku": "DGA-APX",   "name": "Lav Sink Drain Grid Assembly",  "cost": 18.25},
    },
    "lav_sink.p_trap_white": {
        "ferguson":    {"sku": "PT-15W",    "name": "1-1/2\" White PVC P-Trap",      "cost": 7.95},
        "moore_supply":{"sku": "WPT-15",    "name": "1-1/2\" White PVC P-Trap",      "cost": 7.25},
        "apex":        {"sku": "PT15W-A",   "name": "1-1/2\" White PVC P-Trap",      "cost": 8.50},
    },
    # ── Gas Shutoff ───────────────────────────────────────────────────────────
    "gas.ball_valve_3_4": {
        "ferguson":    {"sku": "BV-34GAS",  "name": "3/4\" FIP Gas Ball Valve",      "cost": 18.95},
        "moore_supply":{"sku": "GBV-34",    "name": "3/4\" FIP Gas Ball Valve",      "cost": 17.50},
        "apex":        {"sku": "GBV34-APX", "name": "3/4\" FIP Gas Ball Valve",      "cost": 20.25},
    },
    "gas.teflon_tape_yellow": {
        "ferguson":    {"sku": "TT-GAS",    "name": "Yellow PTFE Gas Tape",          "cost": 3.25},
        "moore_supply":{"sku": "TTG-YLW",   "name": "Yellow PTFE Gas Tape",          "cost": 2.95},
        "apex":        {"sku": "TT-GASA",   "name": "Yellow PTFE Gas Tape",          "cost": 3.50},
    },
    # ── Clean-Out ─────────────────────────────────────────────────────────────
    "clean_out.4in_co_wye": {
        "ferguson":    {"sku": "CO-WYE4",   "name": "4\" PVC Clean-Out Wye w/ Plug", "cost": 14.95},
        "moore_supply":{"sku": "COW-4",     "name": "4\" PVC Clean-Out Wye w/ Plug", "cost": 13.50},
        "apex":        {"sku": "COW4-APX",  "name": "4\" PVC Clean-Out Wye w/ Plug", "cost": 15.95},
    },
    "clean_out.co_plug_4in": {
        "ferguson":    {"sku": "COP-4",     "name": "4\" PVC Clean-Out Plug",        "cost": 3.95},
        "moore_supply":{"sku": "CP-4",      "name": "4\" PVC Clean-Out Plug",        "cost": 3.50},
        "apex":        {"sku": "COP4-A",    "name": "4\" PVC Clean-Out Plug",        "cost": 4.25},
    },
    "clean_out.fernco_4in": {
        "ferguson":    {"sku": "FC-4",      "name": "4\" Fernco Flexible Coupling",  "cost": 9.50},
        "moore_supply":{"sku": "FFC-4",     "name": "4\" Fernco Flexible Coupling",  "cost": 8.75},
        "apex":        {"sku": "FNC4-A",    "name": "4\" Fernco Flexible Coupling",  "cost": 10.25},
    },

    # ── PEX-A Repipe Materials ────────────────────────────────────────────────
    "repipe.pex_a_34_10ft": {
        "ferguson":    {"sku": "PEX34-10",  "name": "Uponor PEX-A 3/4\" x 10ft coil section",  "cost": 14.50},
        "moore_supply":{"sku": "PEXA-34-10","name": "Uponor PEX-A 3/4\" x 10ft",               "cost": 13.25},
        "apex":        {"sku": "PXA34-10A", "name": "PEX-A 3/4\" x 10ft",                       "cost": 15.75},
    },
    "repipe.pex_a_12_10ft": {
        "ferguson":    {"sku": "PEX12-10",  "name": "Uponor PEX-A 1/2\" x 10ft coil section",  "cost": 9.50},
        "moore_supply":{"sku": "PEXA-12-10","name": "Uponor PEX-A 1/2\" x 10ft",               "cost": 8.75},
        "apex":        {"sku": "PXA12-10A", "name": "PEX-A 1/2\" x 10ft",                       "cost": 10.25},
    },
    "repipe.uponor_manifold_6port": {
        "ferguson":    {"sku": "UP-MAN6",   "name": "Uponor Wirsbo 6-port PEX manifold, 3/4\"", "cost": 68.50},
        "moore_supply":{"sku": "UFM-6P",    "name": "Uponor 6-port manifold",                   "cost": 63.25},
        "apex":        {"sku": "UMN6-A",    "name": "PEX 6-port distribution manifold",          "cost": 72.50},
    },
    "repipe.crimp_fitting_12_elbow": {
        "ferguson":    {"sku": "PXE-12-90", "name": "PEX crimp elbow 1/2\" x 1/2\" 90°",        "cost": 1.85},
        "moore_supply":{"sku": "PCE-12",    "name": "PEX crimp elbow 1/2\" 90°",                 "cost": 1.65},
        "apex":        {"sku": "PXE12-A",   "name": "PEX crimp elbow 1/2\" 90°",                 "cost": 2.10},
    },
    "repipe.crimp_ring_12": {
        "ferguson":    {"sku": "PCR-12-50", "name": "PEX crimp ring 1/2\" copper, 50-pk",        "cost": 12.50},
        "moore_supply":{"sku": "CRG-12",    "name": "PEX crimp rings 1/2\", 50-pk",               "cost": 11.25},
        "apex":        {"sku": "CR12-50A",  "name": "PEX crimp rings 1/2\", 50-pk",               "cost": 13.75},
    },

    # ── Sewer Spot Repair Materials ───────────────────────────────────────────
    "sewer.pvc_pipe_4_10ft": {
        "ferguson":    {"sku": "PVC4-10",   "name": "4\" PVC DWV pipe, 10ft",                    "cost": 22.50},
        "moore_supply":{"sku": "P4DWV-10",  "name": "4\" PVC DWV 10ft",                          "cost": 20.75},
        "apex":        {"sku": "PVC4-10A",  "name": "4\" PVC DWV 10ft",                          "cost": 24.00},
    },
    "sewer.fernco_4in_mission": {
        "ferguson":    {"sku": "MCF-4",     "name": "Mission Band Fernco 4\" flexible coupling",  "cost": 14.50},
        "moore_supply":{"sku": "MBF-4",     "name": "Mission Band coupling 4\"",                  "cost": 13.25},
        "apex":        {"sku": "MFC4-A",    "name": "Mission Fernco 4\"",                          "cost": 15.75},
    },
    "sewer.pvc_elbow_4in_45": {
        "ferguson":    {"sku": "4E45-DWV",  "name": "4\" PVC DWV 45° long sweep elbow",           "cost": 8.50},
        "moore_supply":{"sku": "PE45-4",    "name": "4\" PVC 45° elbow DWV",                      "cost": 7.75},
        "apex":        {"sku": "PE45-4A",   "name": "4\" PVC 45° elbow",                           "cost": 9.25},
    },

    # ── Recirculation Pump ────────────────────────────────────────────────────
    "recirc.pump_grundfos_up15": {
        "ferguson":    {"sku": "GF-UP15SU7","name": "Grundfos UP15-10SU7P recirc pump, 1/2\" sweat","cost": 245.00},
        "moore_supply":{"sku": "GRF-UP15",  "name": "Grundfos UP15 recirculation pump",             "cost": 228.00},
        "apex":        {"sku": "GUP15-A",   "name": "Grundfos UP15-10SU7P recirc pump",              "cost": 258.00},
    },
    "recirc.aquamotion_comfort_valve": {
        "ferguson":    {"sku": "AMCV-12",   "name": "AquaMotion comfort valve 1/2\" under-sink",    "cost": 38.50},
        "moore_supply":{"sku": "AMV-CV",    "name": "Comfort valve, thermostatic",                   "cost": 35.25},
        "apex":        {"sku": "AMCV-A",    "name": "Thermostatic comfort valve 1/2\"",               "cost": 42.00},
    },
    "recirc.supply_line_34_18": {
        "ferguson":    {"sku": "SL-34-18",  "name": "Supply line 3/4\" braided SS 18\"",             "cost": 14.50},
        "moore_supply":{"sku": "SL34-18",   "name": "Braided SS supply 3/4\" 18\"",                   "cost": 13.25},
        "apex":        {"sku": "SL34-18A",  "name": "Braided SS 3/4\" x 18\"",                        "cost": 15.75},
    },

    # ── Appliance Hookup ──────────────────────────────────────────────────────
    "appliance.supply_line_ss_24": {
        "ferguson":    {"sku": "SL-24SS",   "name": "Braided SS appliance supply line 1/2\" x 24\"", "cost": 14.50},
        "moore_supply":{"sku": "ASL-24",    "name": "Appliance supply 1/2\" x 24\" SS",               "cost": 13.25},
        "apex":        {"sku": "ASL24-A",   "name": "Appliance SS supply 1/2\" x 24\"",                "cost": 15.75},
    },
    "appliance.drain_hose_72": {
        "ferguson":    {"sku": "DH-72",     "name": "Dishwasher drain hose 5/8\" x 72\"",             "cost": 9.50},
        "moore_supply":{"sku": "DDH-72",    "name": "Drain hose 5/8\" x 6ft",                          "cost": 8.75},
        "apex":        {"sku": "DH72-A",    "name": "DW drain hose 5/8\" x 72\"",                       "cost": 10.25},
    },
    "appliance.drain_air_gap_chrome": {
        "ferguson":    {"sku": "DAG-CH",    "name": "Dishwasher drain air gap, chrome",                "cost": 8.50},
        "moore_supply":{"sku": "AG-DW",     "name": "DW air gap chrome",                                "cost": 7.75},
        "apex":        {"sku": "DAG-A",     "name": "DW air gap chrome",                                 "cost": 9.25},
    },

    # ── Water Main / Shutoff ──────────────────────────────────────────────────
    "main.ball_valve_1in_fullport": {
        "ferguson":    {"sku": "BV-1FP",    "name": "Ball valve 1\" FIP x FIP full port brass",        "cost": 34.50},
        "moore_supply":{"sku": "BVF-1",     "name": "1\" full port ball valve brass",                   "cost": 31.25},
        "apex":        {"sku": "BV1FP-A",   "name": "1\" FIP full port ball valve",                      "cost": 37.00},
    },
    "main.dielectric_union_1in": {
        "ferguson":    {"sku": "DU-1",      "name": "Dielectric union 1\" FIP x FIP",                   "cost": 22.50},
        "moore_supply":{"sku": "DU1-STD",   "name": "1\" dielectric union",                               "cost": 20.75},
        "apex":        {"sku": "DU1-A",     "name": "1\" dielectric union",                                "cost": 24.00},
    },
    "main.copper_pipe_1in_10ft": {
        "ferguson":    {"sku": "CU1-10",    "name": "Type L copper pipe 1\" x 10ft",                     "cost": 58.50},
        "moore_supply":{"sku": "COP1-10",   "name": "Type L copper 1\" x 10ft",                           "cost": 54.25},
        "apex":        {"sku": "CU1-10A",   "name": "1\" Type L copper 10ft",                              "cost": 62.00},
    },
    # ─── Water Heater Repair Parts ────────────────────────────────────────────
    "wh.thermocouple_universal": {
        "ferguson":    {"sku": "TC-UNI",    "name": "Universal thermocouple 36\" leads",                  "cost": 14.50},
        "moore_supply":{"sku": "TC-36U",    "name": "36\" universal thermocouple",                          "cost": 12.75},
        "apex":        {"sku": "TC-UNI-A",  "name": "Universal thermocouple",                               "cost": 15.25},
    },
    "wh.gas_valve_natural": {
        "ferguson":    {"sku": "GV-NAT",    "name": "Gas valve/thermostat combo NG WH",                   "cost": 87.50},
        "moore_supply":{"sku": "WGVN-STD",  "name": "NG water heater gas valve",                           "cost": 82.25},
        "apex":        {"sku": "GV-NG-A",   "name": "Gas valve thermostat NG",                              "cost": 94.00},
    },
    "wh.element_4500w_240v": {
        "ferguson":    {"sku": "EL-4500",   "name": "Residential WH element 4500W 240V",                  "cost": 18.50},
        "moore_supply":{"sku": "WHE-4500",  "name": "4500W electric WH element",                           "cost": 16.75},
        "apex":        {"sku": "EL4500-A",  "name": "4500W 240V water heater element",                      "cost": 19.75},
    },
    "wh.anode_rod_magnesium": {
        "ferguson":    {"sku": "AR-MAG",    "name": "Magnesium anode rod 3/4\" hex 42\"",                  "cost": 22.50},
        "moore_supply":{"sku": "AROD-MG",   "name": "Magnesium anode rod 42\"",                             "cost": 19.75},
        "apex":        {"sku": "AR-MG-A",   "name": "Magnesium anode rod",                                  "cost": 24.00},
    },
    # ─── Toilet Repair Parts ──────────────────────────────────────────────────
    "toilet.seat_elongated_white": {
        "ferguson":    {"sku": "TS-EL-WH",  "name": "Toilet seat elongated white standard close",          "cost": 28.50},
        "moore_supply":{"sku": "TSEAT-EW",  "name": "Elongated toilet seat white",                          "cost": 25.75},
        "apex":        {"sku": "TS-EW-A",   "name": "Elongated white toilet seat",                           "cost": 31.00},
    },
    "toilet.tank_lever_chrome": {
        "ferguson":    {"sku": "TL-CHR",    "name": "Toilet tank trip lever chrome",                       "cost": 12.50},
        "moore_supply":{"sku": "TTLEV-C",   "name": "Chrome tank trip lever",                               "cost": 11.25},
        "apex":        {"sku": "TL-CR-A",   "name": "Chrome toilet tank lever",                              "cost": 13.50},
    },
    "toilet.overflow_tube": {
        "ferguson":    {"sku": "OT-STD",    "name": "Toilet overflow tube & clip",                         "cost": 8.50},
        "moore_supply":{"sku": "OT-UNI",    "name": "Universal overflow tube",                              "cost": 7.75},
        "apex":        {"sku": "OT-STD-A",  "name": "Overflow tube",                                        "cost": 9.25},
    },
    # ─── Faucet Cartridge Parts ───────────────────────────────────────────────
    "faucet.delta_cartridge_rp32104": {
        "ferguson":    {"sku": "RP32104",   "name": "Delta cartridge RP32104 ceramic",                     "cost": 24.50},
        "moore_supply":{"sku": "D-RP32104", "name": "Delta RP32104 ceramic cartridge",                      "cost": 22.75},
        "apex":        {"sku": "RP32104-A", "name": "Delta ceramic cartridge",                               "cost": 26.50},
    },
    "faucet.moen_1225_cartridge": {
        "ferguson":    {"sku": "MOE-1225",  "name": "Moen 1225 single-handle cartridge",                   "cost": 28.50},
        "moore_supply":{"sku": "M-1225",    "name": "Moen 1225 cartridge",                                   "cost": 26.25},
        "apex":        {"sku": "M1225-A",   "name": "Moen 1225 faucet cartridge",                            "cost": 30.25},
    },
    # ─── French Drain / Outdoor Drain Materials ───────────────────────────────
    "drain.perf_pipe_4in_10ft": {
        "ferguson":    {"sku": "PP4-10",    "name": "Perforated HDPE 4\" corrugated pipe 10ft",            "cost": 12.50},
        "moore_supply":{"sku": "PERF4-10",  "name": "4\" perforated drain pipe 10ft",                       "cost": 11.25},
        "apex":        {"sku": "PP4-10A",   "name": "4\" perf corrugated pipe 10ft",                         "cost": 13.50},
    },
    "drain.popup_emitter_4in": {
        "ferguson":    {"sku": "PE-4",      "name": "Pop-up emitter 4\" outlet",                             "cost": 8.50},
        "moore_supply":{"sku": "EMIT-4",    "name": "4\" pop-up drain emitter",                              "cost": 7.75},
        "apex":        {"sku": "PE4-A",     "name": "4\" pop-up emitter",                                    "cost": 9.25},
    },
    "drain.filter_fabric_roll": {
        "ferguson":    {"sku": "FF-25",     "name": "Non-woven filter fabric 36\"x25ft roll",              "cost": 22.50},
        "moore_supply":{"sku": "GEO-25",    "name": "Geotextile filter fabric 25ft",                        "cost": 19.75},
        "apex":        {"sku": "FF25-A",    "name": "Filter fabric roll 36\"x25ft",                          "cost": 24.50},
    },
    # ─── Supply Line Repair Materials ─────────────────────────────────────────
    "supply.pexa_coupling_half": {
        "ferguson":    {"sku": "PEXA-CH",   "name": "PEX-A coupling 1/2\" Uponor ProPEX",                  "cost": 8.50},
        "moore_supply":{"sku": "PEXA-CH-M", "name": "1/2\" PEX-A expansion coupling",                       "cost": 7.75},
        "apex":        {"sku": "PAXC-H-A",  "name": "PEX-A 1/2\" coupling",                                  "cost": 9.25},
    },
    "supply.copper_comp_coupling_half": {
        "ferguson":    {"sku": "CCC-H",     "name": "Copper compression coupling 1/2\"",                   "cost": 9.50},
        "moore_supply":{"sku": "CCC-H-M",   "name": "1/2\" compression coupling copper",                    "cost": 8.75},
        "apex":        {"sku": "CCC-H-A",   "name": "1/2\" copper compression coupling",                     "cost": 10.25},
    },
    # ─── Slab Reroute Materials ───────────────────────────────────────────────
    "reroute.pex_a_half_100ft": {
        "ferguson":    {"sku": "PEXA-H100", "name": "PEX-A tubing 1/2\" 100ft coil Uponor",                "cost": 95.00},
        "moore_supply":{"sku": "PXAH-100",  "name": "1/2\" PEX-A 100ft coil",                               "cost": 88.50},
        "apex":        {"sku": "PXAH100-A", "name": "PEX-A 1/2\" 100ft tubing",                              "cost": 99.50},
    },
    "reroute.access_panel_12x12": {
        "ferguson":    {"sku": "AP-12",     "name": "Access panel 12\"x12\" metal frame",                   "cost": 22.50},
        "moore_supply":{"sku": "ACC-12",    "name": "12\" access panel",                                     "cost": 19.75},
        "apex":        {"sku": "AP12-A",    "name": "12x12 metal access panel",                               "cost": 24.00},
    },

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

    # ── New DFW Product Additions ─────────────────────────────────────────────
    "filter.ro_system_5stage": {
        "ferguson":    {"sku": "RO-500",    "name": "5-Stage RO Water Filter System",                    "cost": 245.00},
        "moore_supply":{"sku": "RO-STD",    "name": "5-Stage Reverse Osmosis",                           "cost": 228.00},
        "apex":        {"sku": "RO5-APX",   "name": "RO System 5-Stage",                                  "cost": 258.00},
    },
    "filter.whole_house_carbon": {
        "ferguson":    {"sku": "WHF-20",    "name": "20\" Big Blue Carbon Filter Housing",               "cost": 185.00},
        "moore_supply":{"sku": "WHF-BB",    "name": "Whole House Carbon Unit",                           "cost": 169.00},
        "apex":        {"sku": "WHF20-A",   "name": "Big Blue Filtration Unit",                          "cost": 195.00},
    },
    "sewer.pvc_pipe_4_sch40_50ft": {
        "ferguson":    {"sku": "PVC4-50",   "name": "4\" SCH40 PVC Pipe (5x 10ft joints)",               "cost": 112.50},
        "moore_supply":{"sku": "P4S40-50",  "name": "4\" PVC SCH40 50ft bundle",                         "cost": 104.00},
        "apex":        {"sku": "PVC4-50A",  "name": "4\" SCH40 PVC 50ft total",                          "cost": 120.00},
    },
    "comm.urinal_valve_sloan": {
        "ferguson":    {"sku": "SLN-186",   "name": "Sloan Royal 186-1 Urinal Valve",                    "cost": 148.00},
        "moore_supply":{"sku": "SRV-186",   "name": "Sloan Manual Urinal Valve",                         "cost": 139.00},
        "apex":        {"sku": "SLN186-A",  "name": "Sloan Urinal Flushometer",                          "cost": 155.00},
    },
    "toilet.bidet_seat_brondell": {
        "ferguson":    {"sku": "BD-SEAT",   "name": "Brondell Swash Bidet Seat",                         "cost": 285.00},
        "moore_supply":{"sku": "BS-1000",   "name": "Electronic Bidet Seat",                             "cost": 265.00},
        "apex":        {"sku": "BD-APX",    "name": "Bidet Washlet Seat",                                "cost": 298.00},
    },
    "toilet.flapper_fluidmaster": {
        "ferguson":    {"sku": "FM-502",    "name": "Fluidmaster 502 Toilet Flapper 2\"",                "cost": 4.95},
        "moore_supply":{"sku": "FL-502M",   "name": "Fluidmaster 2\" Flapper",                           "cost": 4.25},
        "apex":        {"sku": "FL502-A",   "name": "2\" Universal Toilet Flapper",                      "cost": 5.25},
    },
    "toilet.fill_valve_600": {
        "ferguson":    {"sku": "FM-400A",   "name": "Fluidmaster 400A Fill Valve Universal",             "cost": 8.49},
        "moore_supply":{"sku": "FV-400M",   "name": "Fluidmaster Fill Valve Universal",                  "cost": 7.95},
        "apex":        {"sku": "FV400-A",   "name": "Universal Fill Valve",                              "cost": 8.95},
    },

    # ─── Expanded DFW Canonical Items (2025-2026 additions) ──────────────────

    # Water Heater expansion
    "wh.50g_electric_attic_unit": {
        "ferguson":    {"sku": "XE50-ATT",  "name": "Rheem 50G Electric WH (attic-rated)",              "cost": 548.00},
        "moore_supply":{"sku": "AOS-E50A",  "name": "AO Smith 50G Electric WH attic",                   "cost": 524.00},
        "apex":        {"sku": "PME50A",    "name": "ProMax 50G Electric WH attic",                      "cost": 575.00},
    },
    "wh.tankless_electric_unit": {
        "ferguson":    {"sku": "ECO27",     "name": "EcoSmart ECO 27 Tankless Electric WH 27kW",        "cost": 425.00},
        "moore_supply":{"sku": "ECO-27M",   "name": "ECO 27 Electric Tankless",                         "cost": 398.00},
        "apex":        {"sku": "ECO27-A",   "name": "EcoSmart ECO27 Tankless",                           "cost": 448.00},
    },
    "wh.hybrid_heat_pump_unit": {
        "ferguson":    {"sku": "REHP50",    "name": "Rheem ProTerra 50G Heat Pump WH",                  "cost": 1485.00},
        "moore_supply":{"sku": "AOS-HPA50", "name": "AO Smith 50G Heat Pump WH",                        "cost": 1425.00},
        "apex":        {"sku": "HP50-A",    "name": "Heat Pump Water Heater 50G",                        "cost": 1548.00},
    },
    "wh.condensate_pump_kit": {
        "ferguson":    {"sku": "CP-120",    "name": "HVAC/WH condensate pump kit 120V",                 "cost": 48.50},
        "moore_supply":{"sku": "COND-PMP",  "name": "Condensate removal pump",                           "cost": 44.25},
        "apex":        {"sku": "CP120-A",   "name": "Condensate pump 120V",                               "cost": 52.00},
    },
    # Drain/Sewer expansion
    "sewer.cipp_liner_4in_50ft": {
        "ferguson":    {"sku": "CIPP-450",  "name": "CIPP liner kit 4\" x 50ft UV cure",                "cost": 1250.00},
        "moore_supply":{"sku": "CIPP-4-50", "name": "4\" CIPP trenchless liner 50ft",                   "cost": 1175.00},
        "apex":        {"sku": "CIPP450-A", "name": "CIPP pipe liner 4\" 50ft",                          "cost": 1325.00},
    },
    "drain.pop_up_assembly_chrome": {
        "ferguson":    {"sku": "PUA-CHR",   "name": "Pop-up drain assembly chrome 1-1/4\"",             "cost": 18.50},
        "moore_supply":{"sku": "POP-CHR",   "name": "Chrome pop-up drain asm",                           "cost": 16.25},
        "apex":        {"sku": "PUA-C-A",   "name": "Pop-up drain chrome",                                "cost": 19.75},
    },
    "drain.condensate_ptrap_34": {
        "ferguson":    {"sku": "CPT-34",    "name": "HVAC condensate P-trap 3/4\" PVC",                 "cost": 5.50},
        "moore_supply":{"sku": "CT-34",     "name": "3/4\" condensate trap",                              "cost": 4.75},
        "apex":        {"sku": "CPT34-A",   "name": "Condensate P-trap 3/4\"",                            "cost": 6.25},
    },
    "drain.condensate_pvc_34_10ft": {
        "ferguson":    {"sku": "CPVC-34",   "name": "3/4\" PVC pipe 10ft for condensate",               "cost": 4.25},
        "moore_supply":{"sku": "PVC34-10",  "name": "3/4\" PVC 10ft",                                    "cost": 3.75},
        "apex":        {"sku": "PVC34-A",   "name": "PVC 3/4\" pipe 10ft",                                "cost": 4.75},
    },
    "sewer.belly_bedding_gravel_bag": {
        "ferguson":    {"sku": "GRV-50",    "name": "Pea gravel bedding 50lb bag",                       "cost": 6.50},
        "moore_supply":{"sku": "GRVL-50",   "name": "50lb gravel bag",                                    "cost": 5.75},
        "apex":        {"sku": "GRV50-A",   "name": "Pea gravel 50lb",                                    "cost": 7.25},
    },
    # Fixture expansion
    "bidet.standalone_unit": {
        "ferguson":    {"sku": "BD-STND",   "name": "Kohler floor-mount bidet white",                   "cost": 385.00},
        "moore_supply":{"sku": "BD-FM",     "name": "Floor-mount bidet white",                           "cost": 358.00},
        "apex":        {"sku": "BD-STD-A",  "name": "Standalone bidet white",                             "cost": 412.00},
    },
    "sink.pedestal_unit_white": {
        "ferguson":    {"sku": "PED-WHT",   "name": "Pedestal sink white vitreous china",               "cost": 168.00},
        "moore_supply":{"sku": "PS-WHT",    "name": "White pedestal lav sink",                           "cost": 155.00},
        "apex":        {"sku": "PED-W-A",   "name": "Pedestal sink white",                                "cost": 178.00},
    },
    "sink.undermount_ss_single": {
        "ferguson":    {"sku": "UMS-3219",  "name": "32x19 undermount SS single bowl kitchen sink",     "cost": 225.00},
        "moore_supply":{"sku": "UMSS-32",   "name": "SS undermount kitchen 32\"",                        "cost": 208.00},
        "apex":        {"sku": "UMS32-A",   "name": "Undermount stainless 32\" single",                   "cost": 238.00},
    },
    "tub.freestanding_drain_kit": {
        "ferguson":    {"sku": "FTD-KIT",   "name": "Freestanding tub drain assembly w/ overflow",      "cost": 85.00},
        "moore_supply":{"sku": "FTDK",      "name": "Freestanding tub drain kit",                        "cost": 78.00},
        "apex":        {"sku": "FTD-A",     "name": "Tub drain kit freestanding",                         "cost": 92.00},
    },
    "tub.freestanding_filler_floor": {
        "ferguson":    {"sku": "FTF-CHR",   "name": "Floor-mount tub filler chrome w/ handshower",      "cost": 425.00},
        "moore_supply":{"sku": "FTFC",      "name": "Floor-mount tub filler chrome",                     "cost": 395.00},
        "apex":        {"sku": "FTF-A",     "name": "Chrome floor tub filler",                            "cost": 448.00},
    },
    "shower.thermostatic_valve_body": {
        "ferguson":    {"sku": "TVB-34",    "name": "3/4\" thermostatic valve body w/ diverter",         "cost": 285.00},
        "moore_supply":{"sku": "TVBD-34",   "name": "Thermostatic shower valve 3/4\"",                   "cost": 265.00},
        "apex":        {"sku": "TVB34-A",   "name": "3/4\" thermostatic diverter valve",                  "cost": 298.00},
    },
    "shower.body_spray_jet": {
        "ferguson":    {"sku": "BSJ-CHR",   "name": "Body spray jet chrome adjustable",                  "cost": 62.00},
        "moore_supply":{"sku": "BS-JET",    "name": "Chrome body spray jet",                              "cost": 56.00},
        "apex":        {"sku": "BSJ-A",     "name": "Adjustable body spray chrome",                        "cost": 68.00},
    },
    "shower.rain_head_12in": {
        "ferguson":    {"sku": "RH-12C",    "name": "12\" rain shower head chrome ceiling mount",        "cost": 95.00},
        "moore_supply":{"sku": "RSH-12",    "name": "12\" rain head chrome",                              "cost": 88.00},
        "apex":        {"sku": "RH12-A",    "name": "12\" ceiling rain shower head",                       "cost": 102.00},
    },
    "sink.bar_sink_ss_15": {
        "ferguson":    {"sku": "BS-15SS",   "name": "15\" stainless bar sink single bowl",               "cost": 98.00},
        "moore_supply":{"sku": "BSS-15",    "name": "SS bar sink 15\"",                                   "cost": 88.00},
        "apex":        {"sku": "BS15-A",    "name": "Bar sink stainless 15\"",                             "cost": 108.00},
    },
    "sink.bar_faucet_chrome": {
        "ferguson":    {"sku": "BF-CHR",    "name": "Bar/prep faucet single lever chrome",               "cost": 85.00},
        "moore_supply":{"sku": "BFC",       "name": "Chrome bar faucet single lever",                     "cost": 78.00},
        "apex":        {"sku": "BF-C-A",    "name": "Bar faucet chrome",                                   "cost": 92.00},
    },
    "sink.utility_tub_24": {
        "ferguson":    {"sku": "UT-24",     "name": "24\" utility laundry tub freestanding poly",        "cost": 85.00},
        "moore_supply":{"sku": "UTUB-24",   "name": "24\" utility sink poly",                             "cost": 78.00},
        "apex":        {"sku": "UT24-A",    "name": "Utility tub 24\" poly",                               "cost": 92.00},
    },
    "faucet.utility_chrome": {
        "ferguson":    {"sku": "UF-CHR",    "name": "Utility faucet chrome 4\" centerset",               "cost": 42.00},
        "moore_supply":{"sku": "UFC",       "name": "Chrome utility faucet",                               "cost": 38.00},
        "apex":        {"sku": "UF-A",      "name": "4\" utility faucet chrome",                            "cost": 45.00},
    },
    "faucet.pot_filler_chrome": {
        "ferguson":    {"sku": "PF-CHR",    "name": "Pot filler wall-mount articulated chrome",          "cost": 195.00},
        "moore_supply":{"sku": "PFC",       "name": "Chrome wall pot filler",                              "cost": 178.00},
        "apex":        {"sku": "PF-C-A",    "name": "Articulated pot filler chrome",                        "cost": 208.00},
    },
    # Pipe repair expansion
    "pipe.copper_coupling_propress_half": {
        "ferguson":    {"sku": "PP-CH",     "name": "ProPress copper coupling 1/2\"",                    "cost": 8.50},
        "moore_supply":{"sku": "PPC-H",     "name": "1/2\" ProPress coupling",                            "cost": 7.75},
        "apex":        {"sku": "PPH-A",     "name": "ProPress 1/2\" coupling",                              "cost": 9.25},
    },
    "pipe.copper_coupling_propress_34": {
        "ferguson":    {"sku": "PP-C34",    "name": "ProPress copper coupling 3/4\"",                    "cost": 12.50},
        "moore_supply":{"sku": "PPC-34",    "name": "3/4\" ProPress coupling",                            "cost": 11.25},
        "apex":        {"sku": "PP34-A",    "name": "ProPress 3/4\" coupling",                              "cost": 13.50},
    },
    "pipe.pex_transition_poly_b_half": {
        "ferguson":    {"sku": "PBT-H",     "name": "Poly-B to PEX transition coupling 1/2\"",           "cost": 12.50},
        "moore_supply":{"sku": "PBTC-H",    "name": "1/2\" poly-B to PEX coupler",                        "cost": 11.25},
        "apex":        {"sku": "PBT-HA",    "name": "Poly-B transition 1/2\"",                              "cost": 13.50},
    },
    "pipe.repair_clamp_half": {
        "ferguson":    {"sku": "RC-H",      "name": "Pipe repair clamp 1/2\" stainless",                 "cost": 14.50},
        "moore_supply":{"sku": "PRC-H",     "name": "1/2\" SS repair clamp",                               "cost": 12.75},
        "apex":        {"sku": "RC-HA",     "name": "Repair clamp 1/2\" SS",                                "cost": 15.50},
    },
    "pipe.insulation_foam_half_50ft": {
        "ferguson":    {"sku": "FI-H50",    "name": "Foam pipe insulation 1/2\" x 50ft self-seal",       "cost": 22.50},
        "moore_supply":{"sku": "INS-H50",   "name": "1/2\" pipe insulation 50ft",                         "cost": 19.75},
        "apex":        {"sku": "FIH50-A",   "name": "Foam insulation 1/2\" 50ft",                          "cost": 24.50},
    },
    "pipe.insulation_foam_34_50ft": {
        "ferguson":    {"sku": "FI-34-50",  "name": "Foam pipe insulation 3/4\" x 50ft self-seal",       "cost": 28.50},
        "moore_supply":{"sku": "INS-3450",  "name": "3/4\" pipe insulation 50ft",                         "cost": 25.75},
        "apex":        {"sku": "FI3450-A",  "name": "Foam insulation 3/4\" 50ft",                          "cost": 30.25},
    },
    # Gas line expansion
    "gas.flex_connector_48_range": {
        "ferguson":    {"sku": "GFC-48R",   "name": "48\" stainless gas flex connector for range",       "cost": 28.50},
        "moore_supply":{"sku": "GF-48R",    "name": "48\" gas flex range connector",                      "cost": 25.75},
        "apex":        {"sku": "GFC48-A",   "name": "Gas flex 48\" range",                                 "cost": 30.25},
    },
    "gas.flex_connector_36_dryer": {
        "ferguson":    {"sku": "GFC-36D",   "name": "36\" stainless gas flex connector for dryer",       "cost": 22.50},
        "moore_supply":{"sku": "GF-36D",    "name": "36\" gas flex dryer connector",                      "cost": 19.75},
        "apex":        {"sku": "GFC36-A",   "name": "Gas flex 36\" dryer",                                 "cost": 24.50},
    },
    "gas.quick_disconnect_outdoor": {
        "ferguson":    {"sku": "GQD-34",    "name": "3/4\" gas quick disconnect for outdoor grill",      "cost": 32.50},
        "moore_supply":{"sku": "QD-34G",    "name": "Gas quick-disconnect 3/4\"",                          "cost": 29.75},
        "apex":        {"sku": "GQD-A",     "name": "Outdoor gas quick disconnect",                        "cost": 35.00},
    },
    "gas.csst_34_25ft": {
        "ferguson":    {"sku": "CSST-25",   "name": "CSST gas tubing 3/4\" x 25ft coil",                "cost": 85.00},
        "moore_supply":{"sku": "CS-3425",   "name": "3/4\" CSST 25ft",                                    "cost": 78.00},
        "apex":        {"sku": "CSST25-A",  "name": "CSST tubing 3/4\" 25ft",                              "cost": 92.00},
    },
    # Commercial expansion
    "comm.grease_trap_50gal": {
        "ferguson":    {"sku": "GT-50",     "name": "Interior grease trap 50 GPM",                       "cost": 485.00},
        "moore_supply":{"sku": "GIT-50",    "name": "50 GPM grease interceptor",                          "cost": 448.00},
        "apex":        {"sku": "GT50-A",    "name": "Grease trap 50 GPM interior",                         "cost": 512.00},
    },
    "comm.floor_drain_6in": {
        "ferguson":    {"sku": "FD-6SS",    "name": "6\" floor drain SS strainer heavy-duty",            "cost": 68.00},
        "moore_supply":{"sku": "FDR-6",     "name": "6\" HD floor drain",                                  "cost": 62.00},
        "apex":        {"sku": "FD6-A",     "name": "Floor drain 6\" SS",                                   "cost": 72.00},
    },
    "comm.trap_primer_valve": {
        "ferguson":    {"sku": "TPV-STD",   "name": "Trap primer valve 1/2\"",                            "cost": 42.50},
        "moore_supply":{"sku": "TP-PRIME",  "name": "1/2\" trap primer",                                   "cost": 38.75},
        "apex":        {"sku": "TPV-A",     "name": "Trap primer valve",                                    "cost": 45.00},
    },
    "comm.flushometer_sloan_111": {
        "ferguson":    {"sku": "SLN-111",   "name": "Sloan Royal 111 toilet flushometer 1.6 GPF",        "cost": 195.00},
        "moore_supply":{"sku": "SR-111",    "name": "Sloan 111 flushometer",                               "cost": 182.00},
        "apex":        {"sku": "SLN111-A",  "name": "Sloan Royal 111 flush valve",                          "cost": 208.00},
    },
    "wh.commercial_75g_gas": {
        "ferguson":    {"sku": "CWH-75G",   "name": "Commercial 75G gas WH 75,000 BTU",                  "cost": 1850.00},
        "moore_supply":{"sku": "CG75-WH",   "name": "75G commercial gas WH",                               "cost": 1725.00},
        "apex":        {"sku": "CWH75-A",   "name": "Commercial WH 75G gas",                                "cost": 1950.00},
    },
    # Outdoor/Irrigation expansion
    "irrigation.pvb_backflow_1in": {
        "ferguson":    {"sku": "PVB-1",     "name": "1\" PVB backflow preventer for irrigation",          "cost": 125.00},
        "moore_supply":{"sku": "PVBBF-1",   "name": "1\" PVB irrigation backflow",                        "cost": 115.00},
        "apex":        {"sku": "PVB1-A",    "name": "PVB backflow 1\" irrigation",                          "cost": 135.00},
    },
    "irrigation.zone_valve_1in": {
        "ferguson":    {"sku": "ZV-1",      "name": "1\" irrigation zone valve w/ solenoid",              "cost": 28.50},
        "moore_supply":{"sku": "IZV-1",     "name": "1\" zone valve irrigation",                           "cost": 25.75},
        "apex":        {"sku": "ZV1-A",     "name": "Irrigation zone valve 1\"",                            "cost": 30.25},
    },
    "drain.catch_basin_12in": {
        "ferguson":    {"sku": "CB-12",     "name": "12\" catch basin with grate (green)",               "cost": 48.50},
        "moore_supply":{"sku": "CBAS-12",   "name": "12\" catch basin kit",                                "cost": 44.25},
        "apex":        {"sku": "CB12-A",    "name": "Catch basin 12\" with grate",                          "cost": 52.00},
    },
    "outdoor.yard_hydrant_3ft": {
        "ferguson":    {"sku": "YH-3",      "name": "Frost-proof yard hydrant 3ft bury",                 "cost": 125.00},
        "moore_supply":{"sku": "YHFP-3",    "name": "3ft frost-proof yard hydrant",                       "cost": 115.00},
        "apex":        {"sku": "YH3-A",     "name": "Yard hydrant frost-proof 3ft",                        "cost": 135.00},
    },
    # Specialty expansion
    "safety.grab_bar_24_ss": {
        "ferguson":    {"sku": "GB-24SS",   "name": "24\" stainless ADA grab bar",                       "cost": 38.50},
        "moore_supply":{"sku": "ADAGB-24",  "name": "24\" SS grab bar ADA",                               "cost": 35.00},
        "apex":        {"sku": "GB24-A",    "name": "ADA grab bar 24\" SS",                                 "cost": 42.00},
    },
    "safety.grab_bar_blocking": {
        "ferguson":    {"sku": "GBB-KIT",   "name": "Grab bar blocking kit (2x8 + backing plate)",      "cost": 12.50},
        "moore_supply":{"sku": "GBLK",      "name": "Grab bar blocking kit",                               "cost": 11.25},
        "apex":        {"sku": "GBB-A",     "name": "Blocking kit for grab bar",                            "cost": 13.50},
    },
    "wh.timer_programmable": {
        "ferguson":    {"sku": "WHT-PRG",   "name": "WH programmable timer 240V/40A",                    "cost": 38.50},
        "moore_supply":{"sku": "WHTMR",     "name": "Water heater timer",                                  "cost": 35.00},
        "apex":        {"sku": "WHT-A",     "name": "Programmable WH timer",                                "cost": 42.00},
    },
    "safety.auto_shutoff_valve_1in": {
        "ferguson":    {"sku": "ASV-1",     "name": "Automatic shutoff valve 1\" w/ WiFi controller",    "cost": 385.00},
        "moore_supply":{"sku": "ASHUT-1",   "name": "1\" smart auto shutoff valve",                       "cost": 358.00},
        "apex":        {"sku": "ASV1-A",    "name": "Auto water shutoff 1\" smart",                        "cost": 412.00},
    },
    "safety.leak_sensor_3pk": {
        "ferguson":    {"sku": "LS-3PK",    "name": "Water leak sensor 3-pack WiFi",                     "cost": 65.00},
        "moore_supply":{"sku": "WLS-3",     "name": "WiFi leak sensor 3-pack",                             "cost": 58.00},
        "apex":        {"sku": "LS3-A",     "name": "Leak sensor pack of 3 WiFi",                          "cost": 72.00},
    },

    # ── Phase 3: Canonical Materials ──────────────────────────────────────────
    # B. Water Line & Supply
    "pipe.copper_repair_coupling_3_4": {
        "ferguson":    {"sku": "CRC-34",   "name": "Copper repair coupling 3/4\" ProPress",     "cost": 12.50},
        "moore_supply":{"sku": "CRC34-M",  "name": "3/4\" copper ProPress repair coupling",     "cost": 11.00},
        "apex":        {"sku": "CPR34-A",  "name": "Copper press coupling 3/4\" repair",        "cost": 13.75},
    },
    "pipe.pex_crimp_ring_3_4_10pk": {
        "ferguson":    {"sku": "PCR-34-10","name": "PEX crimp ring 3/4\" 10-pack",               "cost": 5.50},
        "moore_supply":{"sku": "PCR34M",   "name": "3/4\" PEX copper crimp rings 10pk",          "cost": 4.75},
        "apex":        {"sku": "PR34-A10", "name": "PEX crimp ring 3/4\" bag of 10",             "cost": 6.00},
    },
    "pipe.pex_coupling_3_4": {
        "ferguson":    {"sku": "PXC-34",   "name": "PEX expansion coupling 3/4\"",               "cost": 4.25},
        "moore_supply":{"sku": "PEC34-M",  "name": "3/4\" PEX-A expansion coupling",             "cost": 3.80},
        "apex":        {"sku": "PEC34-A",  "name": "PEX coupling 3/4\" expansion",               "cost": 4.50},
    },
    "pipe.pex_1in_per_ft": {
        "ferguson":    {"sku": "PEX-1-FT", "name": "PEX-A tubing 1\" per foot red/blue",         "cost": 1.85},
        "moore_supply":{"sku": "PX1-M",    "name": "1\" PEX-A tubing per LF",                    "cost": 1.65},
        "apex":        {"sku": "PX1-A",    "name": "PEX 1\" tubing per foot",                    "cost": 2.00},
    },
    "pipe.main_line_copper_1in_per_ft": {
        "ferguson":    {"sku": "CU-1-FT",  "name": "Type K copper 1\" per foot",                 "cost": 8.50},
        "moore_supply":{"sku": "CK1-M",    "name": "1\" Type K copper per LF",                   "cost": 7.75},
        "apex":        {"sku": "CK1-A",    "name": "Copper Type K 1\" per foot",                 "cost": 9.25},
    },
    "valve.manifold_pex_8_port": {
        "ferguson":    {"sku": "PM-8P",    "name": "PEX manifold 8-port brass with valves",      "cost": 145.00},
        "moore_supply":{"sku": "PXMN8-M",  "name": "8-port PEX manifold brass",                  "cost": 132.00},
        "apex":        {"sku": "PM8-A",    "name": "Brass PEX manifold 8-port",                  "cost": 155.00},
    },
    "pump.pressure_booster": {
        "ferguson":    {"sku": "PBP-20",   "name": "Water pressure booster pump 20GPM",          "cost": 385.00},
        "moore_supply":{"sku": "WPB20-M",  "name": "Booster pump 20 GPM constant pressure",     "cost": 365.00},
        "apex":        {"sku": "BP20-A",   "name": "Pressure booster pump 20GPM",                "cost": 410.00},
    },
    "valve.main_shutoff_1in_ball": {
        "ferguson":    {"sku": "MSV-1B",   "name": "Main shutoff ball valve 1\" full port",       "cost": 28.00},
        "moore_supply":{"sku": "BV1FP-M",  "name": "1\" full port ball valve main shutoff",       "cost": 25.00},
        "apex":        {"sku": "MSB1-A",   "name": "Ball valve 1\" full port shutoff",            "cost": 30.00},
    },
    "valve.thermal_expansion_3_4": {
        "ferguson":    {"sku": "TEV-34",   "name": "Thermal expansion valve 3/4\" potable",       "cost": 42.00},
        "moore_supply":{"sku": "TEV34-M",  "name": "3/4\" thermal expansion relief valve",        "cost": 38.00},
        "apex":        {"sku": "TEV34-A",  "name": "Thermal expansion valve 3/4\"",               "cost": 45.00},
    },

    # C. Drain & Waste
    "fitting.cleanout_cap_4in": {
        "ferguson":    {"sku": "CC-4",     "name": "Cleanout cap 4\" PVC with plug",              "cost": 6.50},
        "moore_supply":{"sku": "CC4-M",    "name": "4\" PVC cleanout cap",                        "cost": 5.75},
        "apex":        {"sku": "CC4-A",    "name": "PVC cleanout cap 4 inch",                     "cost": 7.00},
    },
    "fitting.vent_boot_3in": {
        "ferguson":    {"sku": "VB-3",     "name": "Roof vent boot 3\" neoprene/aluminum",        "cost": 18.00},
        "moore_supply":{"sku": "RVB3-M",   "name": "3\" roof vent pipe boot",                     "cost": 15.50},
        "apex":        {"sku": "VB3-A",    "name": "Vent boot 3\" roof flashing",                 "cost": 19.50},
    },
    "valve.aav_studor_1_5in": {
        "ferguson":    {"sku": "AAV-15",   "name": "Studor AAV 1-1/2\" DFU 20",                   "cost": 22.00},
        "moore_supply":{"sku": "AAV15-M",  "name": "1-1/2\" air admittance valve 20 DFU",         "cost": 19.50},
        "apex":        {"sku": "AAV15-A",  "name": "AAV Studor vent 1.5 inch",                    "cost": 24.00},
    },
    "pump.ejector_sewage_05hp": {
        "ferguson":    {"sku": "EP-05HP",  "name": "Sewage ejector pump 1/2 HP 2\" discharge",    "cost": 285.00},
        "moore_supply":{"sku": "SEP05-M",  "name": "1/2HP sewage ejector pump",                   "cost": 265.00},
        "apex":        {"sku": "EP05-A",   "name": "Ejector pump 1/2 HP sewage",                  "cost": 310.00},
    },
    "fitting.ejector_basin_18x30": {
        "ferguson":    {"sku": "EB-1830",  "name": "Ejector basin 18\"x30\" with sealed lid",     "cost": 85.00},
        "moore_supply":{"sku": "EB18-M",   "name": "18x30 sewage ejector basin",                  "cost": 78.00},
        "apex":        {"sku": "EB1830-A", "name": "Sewage ejector pit basin 18x30",              "cost": 92.00},
    },

    # D. Bathroom Fixture
    "valve.shower_diverter_universal": {
        "ferguson":    {"sku": "SD-UNI",   "name": "Shower diverter valve universal",              "cost": 28.00},
        "moore_supply":{"sku": "SDV-M",    "name": "Universal tub/shower diverter",                "cost": 25.00},
        "apex":        {"sku": "SDU-A",    "name": "Diverter valve universal shower",              "cost": 30.00},
    },
    "faucet.roman_tub_2_handle": {
        "ferguson":    {"sku": "RTF-2H",   "name": "Roman tub faucet 2-handle with sprayer",      "cost": 185.00},
        "moore_supply":{"sku": "RTF2-M",   "name": "2-handle roman tub filler w/sprayer",         "cost": 165.00},
        "apex":        {"sku": "RTF2-A",   "name": "Roman tub faucet deck mount 2H",              "cost": 198.00},
    },
    "fixture.barrier_free_linear_drain_36": {
        "ferguson":    {"sku": "LD-36BF",  "name": "Linear drain 36\" barrier-free ADA",           "cost": 125.00},
        "moore_supply":{"sku": "LD36-M",   "name": "36\" linear shower drain ADA",                 "cost": 112.00},
        "apex":        {"sku": "LD36-A",   "name": "Linear drain 36 inch barrier free",            "cost": 135.00},
    },
    "valve.thermostatic_shower_ada": {
        "ferguson":    {"sku": "TSV-ADA",  "name": "Thermostatic shower valve ADA anti-scald",     "cost": 165.00},
        "moore_supply":{"sku": "TSA-M",    "name": "ADA thermostatic shower valve",                "cost": 148.00},
        "apex":        {"sku": "TSA-A",    "name": "Thermostatic valve ADA shower",                "cost": 178.00},
    },
    "fixture.bidet_sprayer_ss": {
        "ferguson":    {"sku": "BS-SS",    "name": "Handheld bidet sprayer kit stainless",         "cost": 32.00},
        "moore_supply":{"sku": "BSK-M",    "name": "Bidet sprayer kit SS with T-adapter",          "cost": 28.00},
        "apex":        {"sku": "BSK-A",    "name": "SS bidet sprayer with hose and holder",        "cost": 35.00},
    },

    # E. Kitchen & Appliance
    "appliance.instant_hot_dispenser": {
        "ferguson":    {"sku": "IHW-15",   "name": "Instant hot water dispenser 2/3 gallon",       "cost": 165.00},
        "moore_supply":{"sku": "IHD-M",    "name": "Under-sink instant hot dispenser",             "cost": 148.00},
        "apex":        {"sku": "IHD-A",    "name": "Instant hot water dispenser w/faucet",         "cost": 178.00},
    },
    "pipe.fridge_water_line_braided_6ft": {
        "ferguson":    {"sku": "FWL-6B",   "name": "Refrigerator water line braided SS 6ft",       "cost": 14.00},
        "moore_supply":{"sku": "RWL6-M",   "name": "6ft braided SS fridge water line",             "cost": 12.00},
        "apex":        {"sku": "FWL6-A",   "name": "Braided fridge water line 6 foot",             "cost": 15.50},
    },
    "valve.saddle_self_piercing_1_4": {
        "ferguson":    {"sku": "SV-SP14",  "name": "Saddle valve self-piercing 1/4\" outlet",      "cost": 6.00},
        "moore_supply":{"sku": "SPV-M",    "name": "Self-piercing saddle valve 1/4\"",              "cost": 5.25},
        "apex":        {"sku": "SPV-A",    "name": "Saddle valve 1/4\" self-pierce",                "cost": 6.50},
    },
    "appliance.disposal_3_4hp": {
        "ferguson":    {"sku": "GD-34HP",  "name": "Garbage disposal 3/4 HP continuous feed",      "cost": 145.00},
        "moore_supply":{"sku": "GD34-M",   "name": "3/4HP continuous feed disposal",               "cost": 132.00},
        "apex":        {"sku": "GD34-A",   "name": "Disposal 3/4 HP InSinkErator",                 "cost": 155.00},
    },
    "faucet.commercial_sprayer_wall": {
        "ferguson":    {"sku": "CSF-WM",   "name": "Pre-rinse sprayer faucet wall mount",          "cost": 185.00},
        "moore_supply":{"sku": "PRS-M",    "name": "Commercial pre-rinse sprayer wall mount",      "cost": 168.00},
        "apex":        {"sku": "PRS-A",    "name": "Wall mount pre-rinse sprayer faucet",          "cost": 198.00},
    },

    # F. Outdoor & Yard
    "pipe.perf_drain_4in_per_ft": {
        "ferguson":    {"sku": "PD4-FT",   "name": "Perforated drain pipe 4\" per foot",            "cost": 1.25},
        "moore_supply":{"sku": "PDP4-M",   "name": "4\" perforated drain per LF",                   "cost": 1.10},
        "apex":        {"sku": "PDP4-A",   "name": "Perf drain 4 inch per foot",                    "cost": 1.40},
    },
    "material.drain_gravel_per_ton": {
        "ferguson":    {"sku": "DG-TON",   "name": "Drain rock/gravel per ton",                     "cost": 45.00},
        "moore_supply":{"sku": "DRK-M",    "name": "Drain gravel 3/4\" per ton",                    "cost": 40.00},
        "apex":        {"sku": "DG-A",     "name": "French drain gravel per ton",                   "cost": 48.00},
    },
    "material.filter_fabric_per_ft": {
        "ferguson":    {"sku": "FF-FT",    "name": "Landscape filter fabric per LF",                "cost": 0.55},
        "moore_supply":{"sku": "LFF-M",    "name": "Filter fabric landscape per foot",              "cost": 0.48},
        "apex":        {"sku": "FF-A",     "name": "Geotextile filter fabric per LF",               "cost": 0.60},
    },
    "pump.sump_1_3hp": {
        "ferguson":    {"sku": "SP-13HP",  "name": "Sump pump 1/3 HP submersible",                  "cost": 125.00},
        "moore_supply":{"sku": "SP13-M",   "name": "1/3 HP submersible sump pump",                  "cost": 112.00},
        "apex":        {"sku": "SP13-A",   "name": "Sump pump submersible 1/3HP",                   "cost": 135.00},
    },
    "valve.sump_check_1_5in": {
        "ferguson":    {"sku": "SCV-15",   "name": "Sump pump check valve 1-1/2\"",                 "cost": 18.00},
        "moore_supply":{"sku": "SCV15-M",  "name": "1-1/2\" sump check valve",                      "cost": 15.50},
        "apex":        {"sku": "SCV15-A",  "name": "Check valve sump 1.5 inch",                     "cost": 19.50},
    },
    "fixture.outdoor_shower_mixer": {
        "ferguson":    {"sku": "OSM-HW",   "name": "Outdoor shower mixer valve H/C",                "cost": 85.00},
        "moore_supply":{"sku": "OSM-M",    "name": "H/C outdoor shower mixing valve",               "cost": 78.00},
        "apex":        {"sku": "OSM-A",    "name": "Outdoor shower mixer hot/cold",                  "cost": 92.00},
    },
    "fitting.sprinkler_repair_coupling": {
        "ferguson":    {"sku": "SRC-1",    "name": "Sprinkler repair coupling 1\" PVC slip",         "cost": 3.50},
        "moore_supply":{"sku": "SRC1-M",   "name": "1\" PVC sprinkler repair coupling",              "cost": 3.00},
        "apex":        {"sku": "SRC1-A",   "name": "PVC repair coupling sprinkler 1\"",              "cost": 3.75},
    },
    "fitting.rain_barrel_diverter": {
        "ferguson":    {"sku": "RBD-FF",   "name": "Rain barrel first-flush diverter kit",           "cost": 28.00},
        "moore_supply":{"sku": "RBD-M",    "name": "First-flush downspout diverter",                 "cost": 24.00},
        "apex":        {"sku": "RBD-A",    "name": "Diverter kit rain barrel first flush",            "cost": 30.00},
    },

    # G. Gas System
    "pipe.csst_3_4_per_ft": {
        "ferguson":    {"sku": "CSST-34",  "name": "CSST gas flex 3/4\" per foot",                   "cost": 5.50},
        "moore_supply":{"sku": "GF34-M",   "name": "3/4\" CSST gas tubing per LF",                   "cost": 4.85},
        "apex":        {"sku": "GF34-A",   "name": "Gas flex CSST 3/4\" per foot",                   "cost": 5.75},
    },
    "fitting.gas_termination_3_4": {
        "ferguson":    {"sku": "GT-34",    "name": "Gas termination fitting 3/4\" w/valve",           "cost": 22.00},
        "moore_supply":{"sku": "GTF34-M",  "name": "3/4\" gas termination with valve",                "cost": 19.50},
        "apex":        {"sku": "GTF34-A",  "name": "Gas termination 3/4\" brass w/valve",             "cost": 24.00},
    },
    "fitting.gas_cap_3_4": {
        "ferguson":    {"sku": "GC-34",    "name": "Gas cap 3/4\" brass test plug",                   "cost": 5.00},
        "moore_supply":{"sku": "GC34-M",   "name": "3/4\" brass gas cap/plug",                        "cost": 4.25},
        "apex":        {"sku": "GC34-A",   "name": "Brass gas cap 3/4 inch",                          "cost": 5.50},
    },

    # H. Water Treatment
    "appliance.water_softener_48k": {
        "ferguson":    {"sku": "WS-48K",   "name": "Water softener 48,000 grain",                    "cost": 485.00},
        "moore_supply":{"sku": "WS48-M",   "name": "48K grain water softener",                       "cost": 445.00},
        "apex":        {"sku": "WS48-A",   "name": "Water softener 48000 grain",                     "cost": 520.00},
    },
    "appliance.uv_system_12gpm": {
        "ferguson":    {"sku": "UV-12G",   "name": "UV disinfection system 12 GPM",                  "cost": 285.00},
        "moore_supply":{"sku": "UV12-M",   "name": "12 GPM UV water treatment",                      "cost": 265.00},
        "apex":        {"sku": "UV12-A",   "name": "UV water system 12GPM Viqua",                    "cost": 310.00},
    },
    "filter.sediment_whole_house_20in": {
        "ferguson":    {"sku": "SF-20WH",  "name": "Sediment filter housing 20\" whole-house",        "cost": 65.00},
        "moore_supply":{"sku": "SFH20-M",  "name": "20\" whole house filter housing",                 "cost": 58.00},
        "apex":        {"sku": "SF20-A",   "name": "Whole house sediment filter 20 inch",             "cost": 72.00},
    },

    # J. Maintenance
    "material.hose_bib_cover_insulated": {
        "ferguson":    {"sku": "HBC-INS",  "name": "Insulated hose bib cover faucet sock",           "cost": 5.50},
        "moore_supply":{"sku": "HBC-M",    "name": "Hose bib insulated cover",                        "cost": 4.75},
        "apex":        {"sku": "HBC-A",    "name": "Faucet cover insulated hose bib",                 "cost": 6.00},
    },

    # ── Phase 4: Canonical Materials ──────────────────────────────────────────
    # K. Construction
    "fitting.sewer_wye_4in": {
        "ferguson":    {"sku": "SWY-4",    "name": "PVC sewer wye 4\" SDR-35",                        "cost": 12.00},
        "moore_supply":{"sku": "SWY4-M",   "name": "4\" SDR-35 sewer wye",                             "cost": 10.50},
        "apex":        {"sku": "SWY4-A",   "name": "Sewer wye 4 inch PVC",                             "cost": 13.00},
    },
    "fitting.water_service_adapter_1in": {
        "ferguson":    {"sku": "WSA-1",    "name": "Water service adapter 1\" meter to copper",        "cost": 18.00},
        "moore_supply":{"sku": "WSA1-M",   "name": "1\" water service meter adapter",                  "cost": 15.50},
        "apex":        {"sku": "WSA1-A",   "name": "Meter adapter 1\" water service",                  "cost": 19.50},
    },
    "safety.fire_sprinkler_head_pendent": {
        "ferguson":    {"sku": "FSH-PD",   "name": "Fire sprinkler head pendent 155°F white",          "cost": 8.50},
        "moore_supply":{"sku": "FSP-M",    "name": "Pendent sprinkler head 155F residential",          "cost": 7.50},
        "apex":        {"sku": "FSP-A",    "name": "Residential fire sprinkler pendent 155",            "cost": 9.25},
    },
    "pipe.recirc_pex_1_2_per_ft": {
        "ferguson":    {"sku": "RPX-12",   "name": "PEX-A recirc 1/2\" per foot insulated",            "cost": 1.25},
        "moore_supply":{"sku": "RPX12-M",  "name": "1/2\" insulated PEX recirc per LF",                "cost": 1.10},
        "apex":        {"sku": "RPX12-A",  "name": "Recirc PEX 1/2 inch per foot",                     "cost": 1.35},
    },
    "pump.recirc_1_25in": {
        "ferguson":    {"sku": "RCP-125",  "name": "Recirculation pump 1-1/4\" bronze",                "cost": 165.00},
        "moore_supply":{"sku": "RCP-M",    "name": "Bronze recirc pump 1-1/4\"",                       "cost": 148.00},
        "apex":        {"sku": "RCP-A",    "name": "Recirc pump bronze 1.25 inch",                     "cost": 178.00},
    },

    # L. Commercial
    "fixture.commercial_toilet_floor_mount": {
        "ferguson":    {"sku": "CTF-FM",   "name": "Commercial toilet floor mount elongated",           "cost": 185.00},
        "moore_supply":{"sku": "CTF-M",    "name": "Floor mount commercial toilet",                     "cost": 168.00},
        "apex":        {"sku": "CTF-A",    "name": "Commercial floor mount toilet",                     "cost": 198.00},
    },
    "valve.flushometer_1_6gpf": {
        "ferguson":    {"sku": "FM-16",    "name": "Flushometer 1.6 GPF manual chrome",                "cost": 145.00},
        "moore_supply":{"sku": "FM16-M",   "name": "1.6 GPF manual flushometer",                       "cost": 132.00},
        "apex":        {"sku": "FM16-A",   "name": "Chrome flushometer 1.6GPF",                        "cost": 155.00},
    },
    "fixture.wall_hung_toilet_carrier": {
        "ferguson":    {"sku": "WTC-ADJ",  "name": "Wall hung toilet carrier adjustable",               "cost": 285.00},
        "moore_supply":{"sku": "WTC-M",    "name": "Adjustable wall carrier for toilet",                "cost": 265.00},
        "apex":        {"sku": "WTC-A",    "name": "Toilet wall carrier adjustable",                    "cost": 310.00},
    },
    "fixture.urinal_wall_mount": {
        "ferguson":    {"sku": "UWM-05",   "name": "Wall mount urinal 0.5 GPF vitreous",               "cost": 135.00},
        "moore_supply":{"sku": "UWM-M",    "name": "Vitreous urinal wall mount 0.5GPF",                "cost": 122.00},
        "apex":        {"sku": "UWM-A",    "name": "Wall urinal 0.5GPF",                               "cost": 145.00},
    },
    "valve.urinal_flush_05gpf": {
        "ferguson":    {"sku": "UFV-05",   "name": "Urinal flush valve 0.5 GPF",                       "cost": 125.00},
        "moore_supply":{"sku": "UFV-M",    "name": "0.5 GPF urinal flush valve",                       "cost": 112.00},
        "apex":        {"sku": "UFV-A",    "name": "Flush valve urinal 0.5GPF",                        "cost": 135.00},
    },
    "fixture.drinking_fountain_ada": {
        "ferguson":    {"sku": "DF-ADA",   "name": "Drinking fountain ADA with bottle filler",          "cost": 485.00},
        "moore_supply":{"sku": "DF-M",     "name": "ADA drinking fountain + bottle filler",             "cost": 445.00},
        "apex":        {"sku": "DF-A",     "name": "ADA fountain + bottle filler combo",                "cost": 520.00},
    },
    "safety.eyewash_station_combo": {
        "ferguson":    {"sku": "EWS-C",    "name": "Emergency eyewash/shower combo ANSI Z358.1",        "cost": 685.00},
        "moore_supply":{"sku": "EWS-M",    "name": "ANSI eyewash shower combo station",                 "cost": 625.00},
        "apex":        {"sku": "EWS-A",    "name": "Eyewash shower station ANSI combo",                 "cost": 745.00},
    },
    "fixture.mop_sink_24in": {
        "ferguson":    {"sku": "MS-24",    "name": "Mop basin 24\" terrazzo w/faucet",                  "cost": 285.00},
        "moore_supply":{"sku": "MS24-M",   "name": "24\" terrazzo mop sink with faucet",                "cost": 265.00},
        "apex":        {"sku": "MS24-A",   "name": "Terrazzo mop basin 24 inch",                        "cost": 310.00},
    },
    "faucet.sensor_lavatory": {
        "ferguson":    {"sku": "SFL-DC",   "name": "Sensor lavatory faucet battery/DC",                 "cost": 185.00},
        "moore_supply":{"sku": "SFL-M",    "name": "Battery sensor faucet lavatory",                    "cost": 168.00},
        "apex":        {"sku": "SFL-A",    "name": "Hands-free sensor faucet battery",                  "cost": 198.00},
    },
    "valve.commercial_prv_1_5in": {
        "ferguson":    {"sku": "CPRV-15",  "name": "Commercial PRV 1-1/2\" with strainer",              "cost": 185.00},
        "moore_supply":{"sku": "CP15-M",   "name": "1-1/2\" commercial PRV + strainer",                 "cost": 168.00},
        "apex":        {"sku": "CP15-A",   "name": "PRV commercial 1.5 inch w/ strainer",               "cost": 198.00},
    },
    "valve.tmv_asse1017": {
        "ferguson":    {"sku": "TMV-A1",   "name": "TMV ASSE 1017 point-of-use",                        "cost": 95.00},
        "moore_supply":{"sku": "TMV-M",    "name": "Point-of-use TMV ASSE 1017",                        "cost": 85.00},
        "apex":        {"sku": "TMV-A",    "name": "ASSE 1017 thermostatic mixing valve",                "cost": 102.00},
    },
    "fitting.roof_drain_4in_cast": {
        "ferguson":    {"sku": "RD-4CI",   "name": "Roof drain 4\" cast iron with dome",                 "cost": 125.00},
        "moore_supply":{"sku": "RD4-M",    "name": "4\" cast iron roof drain with strainer",             "cost": 112.00},
        "apex":        {"sku": "RD4-A",    "name": "Cast iron roof drain 4 inch dome",                   "cost": 135.00},
    },
    "appliance.commercial_softener_100k": {
        "ferguson":    {"sku": "CS-100K",  "name": "Commercial water softener 100K grain",               "cost": 1250.00},
        "moore_supply":{"sku": "CS100-M",  "name": "100K grain commercial softener",                     "cost": 1150.00},
        "apex":        {"sku": "CS100-A",  "name": "Water softener commercial 100000 grain",             "cost": 1350.00},
    },
    "valve.backflow_repair_kit_generic": {
        "ferguson":    {"sku": "BRK-G",    "name": "Backflow repair kit (checks + relief) generic",      "cost": 65.00},
        "moore_supply":{"sku": "BRK-M",    "name": "Generic backflow preventer repair kit",              "cost": 58.00},
        "apex":        {"sku": "BRK-A",    "name": "Backflow repair kit universal",                      "cost": 72.00},
    },

    # M. Water Heater & Fixture Gaps
    "valve.wh_gas_control": {
        "ferguson":    {"sku": "GCV-WH",   "name": "WH gas control valve Honeywell universal",           "cost": 165.00},
        "moore_supply":{"sku": "GCV-M",    "name": "Honeywell gas valve WH universal",                   "cost": 148.00},
        "apex":        {"sku": "GCV-A",    "name": "Gas control valve Honeywell WH",                     "cost": 178.00},
    },
    "valve.tpr_3_4": {
        "ferguson":    {"sku": "TPR-34",   "name": "T&P relief valve 3/4\" 150 PSI/210°F",               "cost": 14.00},
        "moore_supply":{"sku": "TPR-M",    "name": "3/4\" T&P relief valve",                              "cost": 12.00},
        "apex":        {"sku": "TPR-A",    "name": "TPR valve 3/4 inch",                                  "cost": 15.50},
    },
    "fixture.tub_drain_assembly": {
        "ferguson":    {"sku": "TDA-UNI",  "name": "Tub drain assembly universal shoe/overflow",          "cost": 42.00},
        "moore_supply":{"sku": "TDA-M",    "name": "Universal tub drain shoe & overflow",                 "cost": 38.00},
        "apex":        {"sku": "TDA-A",    "name": "Tub drain assembly shoe overflow universal",           "cost": 45.00},
    },
    "fixture.shower_drain_square_4": {
        "ferguson":    {"sku": "SDS-4",    "name": "Shower drain square 4\" SS strainer",                 "cost": 28.00},
        "moore_supply":{"sku": "SDS4-M",   "name": "4\" square shower drain SS",                          "cost": 24.00},
        "apex":        {"sku": "SDS4-A",   "name": "Square shower drain 4 inch stainless",                "cost": 30.00},
    },
    "fixture.floor_drain_4in": {
        "ferguson":    {"sku": "FD-4",     "name": "Floor drain 4\" PVC with trap",                       "cost": 32.00},
        "moore_supply":{"sku": "FD4-M",    "name": "4\" PVC floor drain with integral trap",              "cost": 28.00},
        "apex":        {"sku": "FD4-A",    "name": "PVC floor drain 4 inch with trap",                    "cost": 35.00},
    },

    # N. Valves & Backflow
    "valve.rpz_rebuild_kit": {
        "ferguson":    {"sku": "RRK-G",    "name": "RPZ rebuild kit generic 3/4-1\"",                     "cost": 85.00},
        "moore_supply":{"sku": "RRK-M",    "name": "RPZ rebuild kit universal",                           "cost": 78.00},
        "apex":        {"sku": "RRK-A",    "name": "Rebuild kit RPZ generic",                             "cost": 92.00},
    },
    "valve.dcva_repair_kit": {
        "ferguson":    {"sku": "DRK-G",    "name": "DCVA repair kit check valves 3/4-1\"",                "cost": 45.00},
        "moore_supply":{"sku": "DRK-M",    "name": "DCVA check valve repair kit",                         "cost": 40.00},
        "apex":        {"sku": "DRK-A",    "name": "Double check repair kit generic",                     "cost": 48.00},
    },
    "valve.earthquake_gas_shutoff": {
        "ferguson":    {"sku": "EQV-1",    "name": "Earthquake gas shutoff valve 1\"",                     "cost": 65.00},
        "moore_supply":{"sku": "EQV-M",    "name": "Seismic gas shutoff valve 1 inch",                    "cost": 58.00},
        "apex":        {"sku": "EQV-A",    "name": "Earthquake valve gas 1\"",                             "cost": 72.00},
    },
    "fitting.gas_drip_leg_1_2": {
        "ferguson":    {"sku": "GDL-12",   "name": "Gas drip leg assembly 1/2\" nipple + cap",             "cost": 6.00},
        "moore_supply":{"sku": "GDL-M",    "name": "1/2\" gas drip leg assembly",                          "cost": 5.00},
        "apex":        {"sku": "GDL-A",    "name": "Drip leg gas 1/2 inch",                                "cost": 6.50},
    },
    "valve.ball_3_4_full_port": {
        "ferguson":    {"sku": "BV-34FP",  "name": "Ball valve 3/4\" full port brass",                     "cost": 12.00},
        "moore_supply":{"sku": "BV34-M",   "name": "3/4\" full port brass ball valve",                     "cost": 10.50},
        "apex":        {"sku": "BV34-A",   "name": "Brass ball valve 3/4 full port",                       "cost": 13.00},
    },

    # O. Appliance Connections
    "pipe.washer_hose_ss_pair": {
        "ferguson":    {"sku": "WHP-SS",   "name": "Washing machine hose pair braided SS 5ft",             "cost": 22.00},
        "moore_supply":{"sku": "WHP-M",    "name": "Braided SS washer hoses pair 5 foot",                  "cost": 19.00},
        "apex":        {"sku": "WHP-A",    "name": "Washer hose SS braided pair",                          "cost": 24.00},
    },
    "pipe.dw_supply_braided": {
        "ferguson":    {"sku": "DWS-B",    "name": "Dishwasher supply line braided SS",                    "cost": 12.00},
        "moore_supply":{"sku": "DWS-M",    "name": "Braided SS dishwasher supply",                         "cost": 10.00},
        "apex":        {"sku": "DWS-A",    "name": "Dishwasher supply braided stainless",                  "cost": 13.00},
    },
    "pipe.gas_range_connector_48": {
        "ferguson":    {"sku": "GRC-48",   "name": "Gas range connector coated SS 48\"",                   "cost": 28.00},
        "moore_supply":{"sku": "GRC-M",    "name": "48\" coated SS gas range connector",                   "cost": 24.00},
        "apex":        {"sku": "GRC-A",    "name": "Gas connector range 48 inch coated",                   "cost": 30.00},
    },

    # P. Specialty & Emerging
    "valve.radiant_manifold_4loop": {
        "ferguson":    {"sku": "RM-4L",    "name": "Radiant heat manifold 4-loop with gauges",             "cost": 165.00},
        "moore_supply":{"sku": "RM4-M",    "name": "4-loop radiant manifold with T-gauges",               "cost": 148.00},
        "apex":        {"sku": "RM4-A",    "name": "Radiant manifold 4 loop gauges",                      "cost": 178.00},
    },
    "pump.well_pressure_tank_32g": {
        "ferguson":    {"sku": "WPT-32",   "name": "Well pressure tank 32 gallon bladder",                 "cost": 185.00},
        "moore_supply":{"sku": "WPT-M",    "name": "32 gal bladder well pressure tank",                   "cost": 168.00},
        "apex":        {"sku": "WPT-A",    "name": "Pressure tank well 32 gallon",                        "cost": 198.00},
    },
    "valve.trap_primer_3_4": {
        "ferguson":    {"sku": "TP-34",    "name": "Trap primer valve 3/4\" supply-side",                   "cost": 42.00},
        "moore_supply":{"sku": "TP34-M",   "name": "3/4\" trap primer valve",                              "cost": 38.00},
        "apex":        {"sku": "TP34-A",   "name": "Trap primer 3/4 inch valve",                           "cost": 45.00},
    },
    "fitting.cleanout_two_way_4in": {
        "ferguson":    {"sku": "CO2W-4",   "name": "Two-way cleanout 4\" PVC with plugs",                  "cost": 22.00},
        "moore_supply":{"sku": "CO2W-M",   "name": "4\" PVC two-way cleanout",                             "cost": 19.00},
        "apex":        {"sku": "CO2W-A",   "name": "PVC two-way cleanout 4 inch",                          "cost": 24.00},
    },
    "fixture.body_spray_pair": {
        "ferguson":    {"sku": "BSP-2",    "name": "Shower body spray pair chrome",                        "cost": 85.00},
        "moore_supply":{"sku": "BSP-M",    "name": "Chrome body spray pair shower",                        "cost": 78.00},
        "apex":        {"sku": "BSP-A",    "name": "Body spray shower pair chrome",                        "cost": 92.00},
    },
    "valve.dual_flush_retrofit": {
        "ferguson":    {"sku": "DFR-UNI",  "name": "Dual flush retrofit kit universal",                    "cost": 22.00},
        "moore_supply":{"sku": "DFR-M",    "name": "Universal dual flush conversion kit",                  "cost": 19.00},
        "apex":        {"sku": "DFR-A",    "name": "Dual flush retrofit universal",                        "cost": 24.00},
    },
}


# ─── Material Assemblies ──────────────────────────────────────────────────────
# Maps assembly_code → { name, labor_template, items: { canonical_id: qty } }
MATERIAL_ASSEMBLIES: dict[str, dict] = {
    "TOILET_INSTALL_KIT": {
        "name": "Toilet Install Kit",
        "labor_template": "TOILET_REPLACE_STANDARD",
        "items": {
            "toilet.wax_ring":      1,
            "toilet.closet_bolts":  1,
            "toilet.supply_line_12": 1,
        },
    },
    "WH_50G_GAS_KIT": {
        "name": "Water Heater 50G Gas Kit",
        "labor_template": "WH_50G_GAS_STANDARD",
        "items": {
            "wh.50g_gas_unit":           1,
            "wh.gas_flex_connector_18":  1,
            "wh.expansion_tank_2g":      1,
            "wh.tp_valve_075":           1,
            "wh.dielectric_union_pair":  1,
        },
    },
    "WH_50G_GAS_ATTIC_KIT": {
        "name": "Water Heater 50G Gas Attic Kit",
        "labor_template": "WH_50G_GAS_ATTIC",
        "items": {
            "wh.50g_gas_unit":           1,
            "wh.gas_flex_connector_18":  1,
            "wh.expansion_tank_2g":      1,
            "wh.tp_valve_075":           1,
            "wh.dielectric_union_pair":  1,
            "wh.drain_pan_26":           1,
            "wh.overflow_line_075":      1,
        },
    },
    "WH_40G_GAS_KIT": {
        "name": "Water Heater 40G Gas Kit",
        "labor_template": "WH_40G_GAS_STANDARD",
        "items": {
            "wh.40g_gas_unit":           1,
            "wh.gas_flex_connector_18":  1,
            "wh.expansion_tank_2g":      1,
            "wh.tp_valve_075":           1,
            "wh.dielectric_union_pair":  1,
        },
    },
    "WH_50G_ELECTRIC_KIT": {
        "name": "Water Heater 50G Electric Kit",
        "labor_template": "WH_50G_ELECTRIC_STANDARD",
        "items": {
            "wh.50g_electric_unit":      1,
            "wh.expansion_tank_2g":      1,
            "wh.tp_valve_075":           1,
            "wh.dielectric_union_pair":  1,
            "wh.water_supply_line_18":   2,
        },
    },
    "WH_TANKLESS_GAS_KIT": {
        "name": "Tankless Water Heater Gas Kit",
        "labor_template": "WH_TANKLESS_GAS",
        "items": {
            "wh.tankless_navien_180k":   1,
            "wh.gas_flex_connector_24":  1,
            "wh.tankless_water_filter":  1,
            "wh.dielectric_union_pair":  1,
        },
    },
    "PRV_KIT": {
        "name": "Pressure Reducing Valve Kit",
        "labor_template": "PRV_REPLACE",
        "items": {
            "prv.watts_3_4":  1,
            "prv.union_3_4":  2,
        },
    },
    "HOSE_BIB_KIT": {
        "name": "Hose Bib Kit",
        "labor_template": "HOSE_BIB_REPLACE",
        "items": {
            "hose_bib.frost_free_12":       1,
            "hose_bib.escutcheon_chrome":   1,
        },
    },
    "SHOWER_VALVE_KIT": {
        "name": "Shower Valve Kit",
        "labor_template": "SHOWER_VALVE_REPLACE",
        "items": {
            "shower.cartridge_moen_1225":       1,
            "shower.seat_washers_kit":          1,
            "shower.trim_kit_brushed_nickel":   1,
        },
    },
    "KITCHEN_FAUCET_KIT": {
        "name": "Kitchen Faucet Install Kit",
        "labor_template": "KITCHEN_FAUCET_REPLACE",
        "items": {
            "kitchen.supply_lines_20_pair": 1,
            "kitchen.basket_strainer":      1,
            "kitchen.teflon_tape":          1,
        },
    },
    "DISPOSAL_KIT": {
        "name": "Garbage Disposal Install Kit",
        "labor_template": "GARBAGE_DISPOSAL_INSTALL",
        "items": {
            "disposal.mounting_ring_kit":   1,
            "disposal.drain_elbow_90":      1,
            "disposal.power_cord_3prong":   1,
        },
    },
    "LAV_FAUCET_KIT": {
        "name": "Lavatory Faucet Install Kit",
        "labor_template": "LAV_FAUCET_REPLACE",
        "items": {
            "lav.supply_lines_12_pair": 1,
            "lav.pop_up_drain":         1,
        },
    },
    "ANGLE_STOP_KIT": {
        "name": "Angle Stop Valve Kit",
        "labor_template": "ANGLE_STOP_REPLACE",
        "items": {
            "angle_stop.quarter_turn_3_8": 1,
            "angle_stop.supply_line_12":   1,
        },
    },
    "PTRAP_KIT": {
        "name": "P-Trap Replace Kit",
        "labor_template": "PTRAP_REPLACE",
        "items": {
            "ptrap.chrome_1_5_inch":    1,
            "ptrap.extension_tube_12":  1,
        },
    },
    "EXPANSION_TANK_KIT": {
        "name": "Thermal Expansion Tank Add-On Kit",
        "labor_template": "EXPANSION_TANK_ONLY",
        "items": {
            "exp_tank.2gal_thermal":  1,
            "exp_tank.nipple_34":     2,
        },
    },
    "WATER_SOFTENER_KIT": {
        "name": "Water Softener Install Kit",
        "labor_template": "WATER_SOFTENER_INSTALL",
        "items": {
            "softener.unit_48k_grain":        1,
            "softener.bypass_valve_1in":      1,
            "softener.brine_line_kit":        1,
            "softener.supply_line_pair_1in":  1,
        },
    },
    "TUB_SHOWER_VALVE_KIT": {
        "name": "Tub/Shower Combo Valve Kit",
        "labor_template": "TUB_SHOWER_COMBO_REPLACE",
        "items": {
            "tub_shower.moen_posi_temp_valve": 1,
            "tub_shower.diverter_tee":         1,
            "tub_shower.tub_spout_chrome":     1,
            "tub_shower.trim_kit_chrome":      1,
        },
    },
    "TOILET_FLAPPER_KIT": {
        "name": "Toilet Flapper Replacement Kit",
        "labor_template": "TOILET_FLAPPER_REPLACE",
        "items": {
            "toilet.flapper_korky":  1,
        },
    },
    "TOILET_FILL_VALVE_KIT": {
        "name": "Toilet Fill Valve Replacement Kit",
        "labor_template": "TOILET_FILL_VALVE_REPLACE",
        "items": {
            "toilet.fill_valve_400a": 1,
            "toilet.flapper_korky":   1,  # replace both while in there
        },
    },
    "TOILET_COMFORT_HEIGHT_KIT": {
        "name": "Comfort Height Toilet Install Kit",
        "labor_template": "TOILET_COMFORT_HEIGHT",
        "items": {
            "toilet.comfort_height_unit": 1,
            "toilet.wax_ring":            1,
            "toilet.closet_bolts":        1,
            "toilet.supply_line_12":      1,
        },
    },
    "TUB_SPOUT_KIT": {
        "name": "Tub Spout Replace Kit",
        "labor_template": "TUB_SPOUT_REPLACE",
        "items": {
            "tub_spout.diverter_chrome": 1,
            "tub_spout.nipple_half":     1,
        },
    },
    "SHOWER_HEAD_KIT": {
        "name": "Shower Head Replacement Kit",
        "labor_template": "SHOWER_HEAD_REPLACE",
        "items": {
            "shower_head.standard_chrome": 1,
            "shower_head.arm_flange":      1,
        },
    },
    "LAV_SINK_KIT": {
        "name": "Lavatory Sink Replace Kit",
        "labor_template": "LAV_SINK_REPLACE",
        "items": {
            "lav_sink.drain_grid_chrome":  1,
            "lav_sink.p_trap_white":       1,
            "lav.supply_lines_12_pair":    1,
            "angle_stop.quarter_turn_3_8": 2,
        },
    },
    "GAS_SHUTOFF_KIT": {
        "name": "Gas Shutoff Valve Kit",
        "labor_template": "GAS_SHUTOFF_REPLACE",
        "items": {
            "gas.ball_valve_3_4":       1,
            "gas.teflon_tape_yellow":   1,
        },
    },
    "CLEAN_OUT_KIT": {
        "name": "4\" Clean-Out Install Kit",
        "labor_template": "CLEAN_OUT_INSTALL",
        "items": {
            "clean_out.4in_co_wye":   1,
            "clean_out.co_plug_4in":  1,
            "clean_out.fernco_4in":   1,
        },
    },

    # ── New high-demand DFW kits ───────────────────────────────────────────────
    "WHOLE_HOUSE_REPIPE_PEX_KIT": {
        "name": "Whole House Repipe PEX-A Kit (per fixture point)",
        "labor_template": "WHOLE_HOUSE_REPIPE_PEX",
        "items": {
            # Materials per fixture point (avg 1 hot + 1 cold outlet per point)
            "repipe.pex_a_12_10ft":         2,   # ~20ft per fixture point in/out
            "repipe.crimp_fitting_12_elbow": 4,   # elbows per point
            "repipe.crimp_ring_12":          0.1, # fraction of 50-pk per point
        },
    },
    "WHOLE_HOUSE_REPIPE_PEX_MANIFOLD_ADD": {
        "name": "Repipe Manifold Add-On (6-port, per manifold)",
        "labor_template": "WHOLE_HOUSE_REPIPE_PEX",
        "items": {
            "repipe.uponor_manifold_6port": 1,
            "repipe.pex_a_34_10ft":         2,   # manifold supply runs
        },
    },

    "SEWER_SPOT_KIT": {
        "name": "Sewer Spot Repair Kit (5ft section)",
        "labor_template": "SEWER_SPOT_REPAIR",
        "items": {
            "sewer.pvc_pipe_4_10ft":     1,
            "sewer.fernco_4in_mission":  2,   # one each end
            "sewer.pvc_elbow_4in_45":    1,
        },
    },

    "RECIRC_PUMP_KIT": {
        "name": "Hot Water Recirculation Pump Kit",
        "labor_template": "RECIRC_PUMP_INSTALL",
        "items": {
            "recirc.pump_grundfos_up15":        1,
            "recirc.aquamotion_comfort_valve":   1,
            "recirc.supply_line_34_18":          1,
        },
    },

    "DISHWASHER_KIT": {
        "name": "Dishwasher Supply & Drain Kit",
        "labor_template": "DISHWASHER_HOOKUP",
        "items": {
            "appliance.supply_line_ss_24":   1,
            "appliance.drain_hose_72":       1,
            "appliance.drain_air_gap_chrome": 1,
        },
    },

    "WATER_MAIN_KIT": {
        "name": "Water Main Shutoff Valve Kit",
        "labor_template": "WATER_MAIN_REPAIR",
        "items": {
            "main.ball_valve_1in_fullport": 1,
            "main.dielectric_union_1in":    2,
            "main.copper_pipe_1in_10ft":    0.5,
        },
    },

    # ─── Water Heater Repair Kits ─────────────────────────────────────────────
    "WH_REPAIR_GAS_KIT": {
        "name": "Gas Water Heater Repair Kit (thermocouple/gas valve)",
        "labor_template": "WH_REPAIR_GAS",
        "items": {
            "wh.thermocouple_universal": 1,
            "wh.gas_valve_natural":      1,
        },
    },

    "WH_ELEMENT_KIT": {
        "name": "Electric Water Heater Element Kit",
        "labor_template": "WH_ELEMENT_REPLACE",
        "items": {
            "wh.element_4500w_240v": 1,
        },
    },

    "ANODE_ROD_KIT": {
        "name": "Anode Rod Replacement Kit",
        "labor_template": "WH_ANODE_REPLACE",
        "items": {
            "wh.anode_rod_magnesium": 1,
        },
    },

    # ─── Toilet Repair Kits ───────────────────────────────────────────────────
    "TOILET_REBUILD_KIT": {
        "name": "Full Toilet Tank Rebuild Kit",
        "labor_template": "TOILET_TANK_REBUILD",
        "items": {
            "toilet.flapper_fluidmaster":  1,
            "toilet.fill_valve_600":       1,
            "toilet.tank_lever_chrome":    1,
            "toilet.overflow_tube":        1,
        },
    },

    "TOILET_SEAT_KIT": {
        "name": "Toilet Seat Replacement Kit",
        "labor_template": "TOILET_SEAT_REPLACE",
        "items": {
            "toilet.seat_elongated_white": 1,
        },
    },

    "WAX_RING_RESET_KIT": {
        "name": "Toilet Wax Ring Reset Kit",
        "labor_template": "TOILET_WAX_RING_ONLY",
        "items": {
            "toilet.wax_ring":       1,
            "toilet.closet_bolts":   1,
        },
    },

    # ─── Faucet Cartridge Kit ─────────────────────────────────────────────────
    "CARTRIDGE_KIT": {
        "name": "Faucet Cartridge Replacement Kit",
        "labor_template": "FAUCET_CARTRIDGE_REPAIR",
        "items": {
            "faucet.delta_cartridge_rp32104": 1,  # most common DFW faucet brand
        },
    },

    # ─── Water Supply Line Repair Kit ─────────────────────────────────────────
    "WATER_LINE_REPAIR_KIT": {
        "name": "Supply Line Repair Kit (pinhole/joint)",
        "labor_template": "WATER_LINE_REPAIR_MINOR",
        "items": {
            "supply.pexa_coupling_half":        2,
            "supply.copper_comp_coupling_half": 2,
        },
    },

    # ─── Slab Leak Reroute Kit ────────────────────────────────────────────────
    "SLAB_REROUTE_KIT": {
        "name": "Slab Leak Attic/Wall Reroute Kit",
        "labor_template": "SLAB_LEAK_REROUTE",
        "items": {
            "reroute.pex_a_half_100ft":   1,
            "reroute.access_panel_12x12": 2,
            "supply.pexa_coupling_half":  4,
        },
    },

    # ─── Outdoor Drain Kit (per 10 LF) ────────────────────────────────────────
    "OUTDOOR_DRAIN_KIT": {
        "name": "French / Yard Drain Kit (per 10 LF)",
        "labor_template": "OUTDOOR_DRAIN_INSTALL",
        "items": {
            "drain.perf_pipe_4in_10ft": 1,
            "drain.popup_emitter_4in":  1,
            "drain.filter_fabric_roll": 0.4,  # ~10ft of 25ft roll
        },
    },

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
    "SUMP_PUMP_INSTALL": {
        "name": "Sump Pump Installation Kit",
        "labor_template": "SUMP_PUMP_INSTALL",
        "items": {
            "plumbing.sump_pump_1_3hp":   1,
            "plumbing.sump_basin_18in":   1,
            "plumbing.check_valve_1p5in": 1,
        },
    },

    # ── New DFW High-Demand Assemblies ────────────────────────────────────────
    "RO_SYSTEM_KIT": {
        "name": "Reverse Osmosis Install Kit",
        "labor_template": "RO_SYSTEM_INSTALL",
        "items": {
            "filter.ro_system_5stage": 1,
            "angle_stop.quarter_turn_3_8": 1,
        },
    },
    "WHOLE_HOUSE_FILTER_KIT": {
        "name": "Whole House Filtration Kit",
        "labor_template": "FILTRATION_WHOLE_HOUSE",
        "items": {
            "filter.whole_house_carbon": 1,
            "main.ball_valve_1in_fullport": 2, # for bypass
        },
    },
    "SEWER_LINE_FULL_KIT": {
        "name": "Sewer Main Line Kit (50 LF)",
        "labor_template": "SEWER_LINE_REPLACE_FULL",
        "items": {
            "sewer.pvc_pipe_4_sch40_50ft": 1,
            "clean_out.4in_co_wye": 2, # two-way cleanout
        },
    },
    "URINAL_VALVE_KIT": {
        "name": "Urinal Valve Replacement Kit",
        "labor_template": "URINAL_FLUSH_VALVE_REPLACE",
        "items": {
            "comm.urinal_valve_sloan": 1,
        },
    },
    "BIDET_SEAT_KIT": {
        "name": "Bidet Seat Installation Kit",
        "labor_template": "BIDET_SEAT_INSTALL",
        "items": {
            "toilet.bidet_seat_brondell": 1,
        },
    },

    # ─── Expanded DFW Material Assemblies (2025-2026 additions) ──────────────

    "WH_50G_ELECTRIC_ATTIC_KIT": {
        "name": "50G Electric WH Attic Install Kit",
        "labor_template": "WH_50G_ELECTRIC_ATTIC",
        "items": {
            "wh.50g_electric_attic_unit": 1,
            "wh.drain_pan_26":            1,
            "wh.overflow_line_075":       1,
            "wh.expansion_tank_2g":       1,
            "wh.water_supply_line_18":    2,
        },
    },

    "WH_TANKLESS_ELECTRIC_KIT": {
        "name": "Tankless Electric WH Install Kit",
        "labor_template": "WH_TANKLESS_ELECTRIC",
        "items": {
            "wh.tankless_electric_unit":  1,
            "wh.water_supply_line_18":    2,
        },
    },

    "WH_HYBRID_HEAT_PUMP_KIT": {
        "name": "Hybrid Heat Pump WH Install Kit",
        "labor_template": "WH_HYBRID_HEAT_PUMP",
        "items": {
            "wh.hybrid_heat_pump_unit":   1,
            "wh.expansion_tank_2g":       1,
            "wh.water_supply_line_18":    2,
            "wh.condensate_pump_kit":     1,
            "wh.drain_pan_26":            1,
        },
    },

    "WH_RECIRC_LINE_KIT": {
        "name": "Dedicated Recirculation Return Line Kit",
        "labor_template": "WH_RECIRCULATION_LINE_NEW",
        "items": {
            "recirc.pump_grundfos_up15":  1,
            "reroute.pex_a_half_100ft":   1,
            "pipe.insulation_foam_half_50ft": 2,
        },
    },

    "WH_PAN_KIT": {
        "name": "WH Drain Pan & Overflow Kit",
        "labor_template": "WH_PAN_DRAIN_OVERFLOW_ONLY",
        "items": {
            "wh.drain_pan_26":            1,
            "wh.overflow_line_075":       1,
        },
    },

    "SEWER_LINER_KIT": {
        "name": "CIPP Trenchless Liner Kit (50 LF)",
        "labor_template": "SEWER_LINER_CIPP",
        "items": {
            "sewer.cipp_liner_4in_50ft":  1,
        },
    },

    "SEWER_BELLY_KIT": {
        "name": "Sewer Belly Repair Kit",
        "labor_template": "SEWER_BELLY_REPAIR",
        "items": {
            "sewer.pvc_pipe_4_10ft":       2,
            "sewer.fernco_4in_mission":    2,
            "sewer.belly_bedding_gravel_bag": 4,
        },
    },

    "POP_UP_DRAIN_KIT": {
        "name": "Pop-Up Drain Assembly Kit",
        "labor_template": "DRAIN_POP_UP_REPLACE",
        "items": {
            "drain.pop_up_assembly_chrome": 1,
        },
    },

    "CONDENSATE_DRAIN_KIT": {
        "name": "HVAC Condensate Drain Tie-In Kit",
        "labor_template": "CONDENSATE_DRAIN_INSTALL",
        "items": {
            "drain.condensate_ptrap_34":   1,
            "drain.condensate_pvc_34_10ft": 2,
        },
    },

    "BIDET_STANDALONE_KIT": {
        "name": "Standalone Bidet Install Kit",
        "labor_template": "BIDET_STANDALONE_INSTALL",
        "items": {
            "bidet.standalone_unit":       1,
            "lav.supply_lines_12_pair":    1,
            "ptrap.chrome_1_5_inch":       1,
        },
    },

    "PEDESTAL_SINK_KIT": {
        "name": "Pedestal Sink Install Kit",
        "labor_template": "PEDESTAL_SINK_INSTALL",
        "items": {
            "sink.pedestal_unit_white":    1,
            "lav.supply_lines_12_pair":    1,
            "lav.pop_up_drain":            1,
            "ptrap.chrome_1_5_inch":       1,
        },
    },

    "UNDERMOUNT_SINK_KIT": {
        "name": "Undermount Sink Install Kit",
        "labor_template": "UNDERMOUNT_SINK_INSTALL",
        "items": {
            "sink.undermount_ss_single":   1,
            "sink.basket_strainer_chrome":  1,
            "sink.ptrap_1p5_abs":          1,
            "sink.supply_line_braided_12in": 2,
        },
    },

    "FREESTANDING_TUB_KIT": {
        "name": "Freestanding Tub Plumbing Kit",
        "labor_template": "FREESTANDING_TUB_INSTALL",
        "items": {
            "tub.freestanding_drain_kit":    1,
            "tub.freestanding_filler_floor": 1,
        },
    },

    "WALK_IN_SHOWER_KIT": {
        "name": "Walk-In Shower Multi-Valve Kit",
        "labor_template": "WALK_IN_SHOWER_VALVE_INSTALL",
        "items": {
            "shower.thermostatic_valve_body": 1,
            "shower.body_spray_jet":          3,
            "shower.rain_head_12in":          1,
        },
    },

    "WET_BAR_SINK_KIT": {
        "name": "Wet Bar Sink Install Kit",
        "labor_template": "WET_BAR_SINK_INSTALL",
        "items": {
            "sink.bar_sink_ss_15":          1,
            "sink.bar_faucet_chrome":       1,
            "ptrap.chrome_1_5_inch":        1,
            "angle_stop.quarter_turn_3_8":  2,
        },
    },

    "UTILITY_SINK_KIT": {
        "name": "Utility/Laundry Sink Install Kit",
        "labor_template": "UTILITY_SINK_INSTALL",
        "items": {
            "sink.utility_tub_24":          1,
            "faucet.utility_chrome":        1,
            "ptrap.chrome_1_5_inch":        1,
        },
    },

    "POT_FILLER_KIT": {
        "name": "Pot Filler Faucet Kit",
        "labor_template": "POT_FILLER_INSTALL",
        "items": {
            "faucet.pot_filler_chrome":     1,
        },
    },

    "COPPER_REPAIR_KIT": {
        "name": "Copper Pinhole Repair Kit (per point)",
        "labor_template": "COPPER_PINHOLE_REPAIR",
        "items": {
            "pipe.copper_coupling_propress_half": 2,
        },
    },

    "POLY_B_REPAIR_KIT": {
        "name": "Polybutylene Section Repair Kit",
        "labor_template": "POLYBUTYLENE_SECTION_REPLACE",
        "items": {
            "pipe.pex_transition_poly_b_half": 2,
            "repipe.pex_a_12_10ft":             1,
        },
    },

    "PIPE_BURST_KIT": {
        "name": "Burst Pipe Emergency Kit",
        "labor_template": "PIPE_BURST_EMERGENCY",
        "items": {
            "pipe.repair_clamp_half":           1,
            "pipe.copper_coupling_propress_half": 2,
            "pipe.copper_coupling_propress_34":   1,
        },
    },

    "FREEZE_REPAIR_KIT": {
        "name": "Freeze Damage Repair Kit (up to 3 points)",
        "labor_template": "FREEZE_DAMAGE_THAW_REPAIR",
        "items": {
            "pipe.copper_coupling_propress_half": 3,
            "pipe.copper_coupling_propress_34":   2,
            "pipe.repair_clamp_half":             1,
        },
    },

    "PIPE_INSULATION_KIT": {
        "name": "Pipe Insulation Kit (50 LF)",
        "labor_template": "PIPE_INSULATION_INSTALL",
        "items": {
            "pipe.insulation_foam_half_50ft":  1,
            "pipe.insulation_foam_34_50ft":    1,
        },
    },

    "GAS_DRYER_KIT": {
        "name": "Gas Dryer Hookup Kit",
        "labor_template": "GAS_LINE_DRYER",
        "items": {
            "gas.flex_connector_36_dryer":     1,
            "gas.ball_valve_3_4":              1,
            "gas.teflon_tape_yellow":          1,
        },
    },

    "GAS_RANGE_KIT": {
        "name": "Gas Range/Oven Hookup Kit",
        "labor_template": "GAS_LINE_RANGE_OVEN",
        "items": {
            "gas.flex_connector_48_range":     1,
            "gas.ball_valve_3_4":              1,
            "gas.teflon_tape_yellow":          1,
        },
    },

    "GAS_FIREPLACE_KIT": {
        "name": "Gas Fireplace Line Kit",
        "labor_template": "GAS_LINE_FIREPLACE",
        "items": {
            "gas.csst_34_25ft":                1,
            "gas.ball_valve_3_4":              1,
            "gas.teflon_tape_yellow":          1,
        },
    },

    "GAS_OUTDOOR_KIT": {
        "name": "Outdoor Grill Gas Line Kit",
        "labor_template": "GAS_LINE_GRILL_OUTDOOR",
        "items": {
            "gas.csst_34_25ft":                1,
            "gas.quick_disconnect_outdoor":    1,
            "gas.ball_valve_3_4":              1,
            "gas.teflon_tape_yellow":          1,
        },
    },

    "GREASE_TRAP_KIT": {
        "name": "Commercial Grease Trap Install Kit",
        "labor_template": "COMMERCIAL_GREASE_TRAP_INSTALL",
        "items": {
            "comm.grease_trap_50gal":          1,
        },
    },

    "COMMERCIAL_FLOOR_DRAIN_KIT": {
        "name": "Commercial Floor Drain Install Kit",
        "labor_template": "COMMERCIAL_FLOOR_DRAIN_INSTALL",
        "items": {
            "comm.floor_drain_6in":            1,
            "comm.trap_primer_valve":          1,
        },
    },

    "FLUSHOMETER_KIT": {
        "name": "Flushometer Valve Replacement Kit",
        "labor_template": "FLUSHOMETER_REPLACE",
        "items": {
            "comm.flushometer_sloan_111":      1,
        },
    },

    "COMMERCIAL_WH_KIT": {
        "name": "Commercial Water Heater Install Kit",
        "labor_template": "COMMERCIAL_WATER_HEATER_INSTALL",
        "items": {
            "wh.commercial_75g_gas":           1,
            "wh.expansion_tank_2g":            1,
            "wh.tp_valve_075":                 1,
            "wh.dielectric_union_pair":        2,
        },
    },

    "IRRIGATION_BACKFLOW_KIT": {
        "name": "Irrigation Backflow Preventer Kit",
        "labor_template": "IRRIGATION_BACKFLOW_INSTALL",
        "items": {
            "irrigation.pvb_backflow_1in":     1,
        },
    },

    "IRRIGATION_VALVE_KIT": {
        "name": "Irrigation Zone Valve Repair Kit",
        "labor_template": "IRRIGATION_VALVE_REPAIR",
        "items": {
            "irrigation.zone_valve_1in":       1,
        },
    },

    "CATCH_BASIN_KIT": {
        "name": "Catch Basin Install Kit",
        "labor_template": "CATCH_BASIN_INSTALL",
        "items": {
            "drain.catch_basin_12in":          1,
            "drain.perf_pipe_4in_10ft":        2,
            "drain.popup_emitter_4in":         1,
        },
    },

    "YARD_HYDRANT_KIT": {
        "name": "Frost-Proof Yard Hydrant Kit",
        "labor_template": "YARD_HYDRANT_INSTALL",
        "items": {
            "outdoor.yard_hydrant_3ft":        1,
        },
    },

    "GRAB_BAR_KIT": {
        "name": "ADA Grab Bar Install Kit (per bar)",
        "labor_template": "ADA_GRAB_BAR_INSTALL",
        "items": {
            "safety.grab_bar_24_ss":           1,
            "safety.grab_bar_blocking":        1,
        },
    },

    "WH_TIMER_KIT": {
        "name": "Water Heater Timer Kit",
        "labor_template": "WATER_HEATER_TIMER_INSTALL",
        "items": {
            "wh.timer_programmable":           1,
        },
    },

    "AUTO_SHUTOFF_KIT": {
        "name": "Automatic Water Shutoff System Kit",
        "labor_template": "EMERGENCY_SHUTOFF_VALVE_INSTALL",
        "items": {
            "safety.auto_shutoff_valve_1in":   1,
            "safety.leak_sensor_3pk":          1,
        },
    },

    # ── Phase 3: Material Assemblies ──────────────────────────────────────────

    # B. Water Line & Supply
    "COPPER_REPAIR_KIT": {
        "name": "Copper Water Line Repair Kit",
        "labor_template": "WATER_LINE_REPAIR_COPPER",
        "items": {
            "pipe.copper_repair_coupling_3_4": 2,
        },
    },
    "PEX_REPAIR_KIT": {
        "name": "PEX Water Line Repair Kit",
        "labor_template": "WATER_LINE_REPAIR_PEX",
        "items": {
            "pipe.pex_coupling_3_4":          2,
            "pipe.pex_crimp_ring_3_4_10pk":   1,
        },
    },
    "MAIN_LINE_REPLACE_KIT": {
        "name": "Main Water Line Replace Kit (per 50 LF)",
        "labor_template": "WATER_LINE_REPLACE_MAIN_STREET",
        "items": {
            "pipe.main_line_copper_1in_per_ft": 50,
        },
    },
    "MANIFOLD_KIT": {
        "name": "PEX Manifold System Kit",
        "labor_template": "MANIFOLD_INSTALL_PEX",
        "items": {
            "valve.manifold_pex_8_port":      1,
            "pipe.pex_1in_per_ft":            20,
        },
    },
    "PRESSURE_BOOSTER_KIT": {
        "name": "Pressure Booster Pump Kit",
        "labor_template": "PRESSURE_BOOSTER_INSTALL",
        "items": {
            "pump.pressure_booster":          1,
        },
    },
    "MAIN_SHUTOFF_KIT": {
        "name": "Main Shutoff Valve Replace Kit",
        "labor_template": "SHUT_OFF_VALVE_MAIN",
        "items": {
            "valve.main_shutoff_1in_ball":    1,
        },
    },
    "THERMAL_EXPANSION_KIT": {
        "name": "Thermal Expansion Valve Kit",
        "labor_template": "THERMAL_EXPANSION_VALVE",
        "items": {
            "valve.thermal_expansion_3_4":    1,
        },
    },

    # C. Drain & Waste
    "CLEANOUT_CAP_KIT": {
        "name": "Cleanout Cap Replace Kit",
        "labor_template": "CLEANOUT_CAP_REPLACE",
        "items": {
            "fitting.cleanout_cap_4in":       1,
        },
    },
    "VENT_PIPE_KIT": {
        "name": "Roof Vent Pipe Repair Kit",
        "labor_template": "VENT_PIPE_REPAIR_ROOF",
        "items": {
            "fitting.vent_boot_3in":          1,
        },
    },
    "AAV_KIT": {
        "name": "Air Admittance Valve Kit",
        "labor_template": "AAV_INSTALL",
        "items": {
            "valve.aav_studor_1_5in":         1,
        },
    },
    "EJECTOR_PUMP_KIT": {
        "name": "Sewage Ejector Pump System Kit",
        "labor_template": "EJECTOR_PUMP_INSTALL",
        "items": {
            "pump.ejector_sewage_05hp":       1,
            "fitting.ejector_basin_18x30":    1,
        },
    },

    # D. Bathroom Fixture
    "DIVERTER_KIT": {
        "name": "Shower Diverter Repair Kit",
        "labor_template": "SHOWER_DIVERTER_REPAIR",
        "items": {
            "valve.shower_diverter_universal": 1,
        },
    },
    "ROMAN_TUB_KIT": {
        "name": "Roman Tub Faucet Replace Kit",
        "labor_template": "ROMAN_TUB_FAUCET_REPLACE",
        "items": {
            "faucet.roman_tub_2_handle":      1,
        },
    },
    "CLAWFOOT_TUB_KIT": {
        "name": "Clawfoot Tub Plumbing Kit",
        "labor_template": "CLAW_FOOT_TUB_PLUMBING",
        "items": {},
    },
    "BARRIER_FREE_SHOWER_KIT": {
        "name": "ADA Barrier-Free Shower Kit",
        "labor_template": "BARRIER_FREE_SHOWER_INSTALL",
        "items": {
            "fixture.barrier_free_linear_drain_36": 1,
            "valve.thermostatic_shower_ada":        1,
        },
    },
    "STEAM_SHOWER_KIT": {
        "name": "Steam Shower Plumbing Kit",
        "labor_template": "STEAM_SHOWER_VALVE_INSTALL",
        "items": {},
    },
    "BIDET_SPRAYER_KIT": {
        "name": "Handheld Bidet Sprayer Kit",
        "labor_template": "BIDET_SPRAYER_INSTALL",
        "items": {
            "fixture.bidet_sprayer_ss":       1,
        },
    },

    # E. Kitchen & Appliance
    "INSTANT_HOT_KIT": {
        "name": "Instant Hot Water Dispenser Kit",
        "labor_template": "INSTANT_HOT_WATER_INSTALL",
        "items": {
            "appliance.instant_hot_dispenser": 1,
        },
    },
    "FRIDGE_LINE_KIT": {
        "name": "Refrigerator Water Line Kit",
        "labor_template": "REFRIGERATOR_LINE_INSTALL",
        "items": {
            "pipe.fridge_water_line_braided_6ft": 1,
            "valve.saddle_self_piercing_1_4":     1,
        },
    },
    "DISPOSAL_HP_KIT": {
        "name": "Garbage Disposal High-Power Kit",
        "labor_template": "GARBAGE_DISPOSAL_REPLACE_HP",
        "items": {
            "appliance.disposal_3_4hp":       1,
        },
    },
    "PREP_SINK_KIT": {
        "name": "Prep/Island Sink Install Kit",
        "labor_template": "PREP_SINK_INSTALL",
        "items": {
            "valve.aav_studor_1_5in":         1,
        },
    },
    "SPRAYER_FAUCET_KIT": {
        "name": "Commercial Pre-Rinse Faucet Kit",
        "labor_template": "COMMERCIAL_SPRAYER_FAUCET",
        "items": {
            "faucet.commercial_sprayer_wall":  1,
        },
    },

    # F. Outdoor & Yard
    "FRENCH_DRAIN_KIT": {
        "name": "French Drain Kit (per 25 LF)",
        "labor_template": "FRENCH_DRAIN_INSTALL",
        "items": {
            "pipe.perf_drain_4in_per_ft":     25,
            "material.drain_gravel_per_ton":  1,
            "material.filter_fabric_per_ft":  25,
        },
    },
    "SUMP_PUMP_REPLACE_KIT": {
        "name": "Sump Pump Replace Kit",
        "labor_template": "SUMP_PUMP_REPLACE",
        "items": {
            "pump.sump_1_3hp":                1,
            "valve.sump_check_1_5in":         1,
        },
    },
    "OUTDOOR_SHOWER_KIT": {
        "name": "Outdoor Shower Plumbing Kit",
        "labor_template": "OUTDOOR_SHOWER_INSTALL",
        "items": {
            "fixture.outdoor_shower_mixer":   1,
        },
    },
    "SPRINKLER_REPAIR_KIT": {
        "name": "Sprinkler Line Repair Kit",
        "labor_template": "SPRINKLER_LINE_REPAIR",
        "items": {
            "fitting.sprinkler_repair_coupling": 2,
        },
    },
    "RAIN_BARREL_KIT": {
        "name": "Rain Barrel Hookup Kit",
        "labor_template": "RAIN_BARREL_HOOKUP",
        "items": {
            "fitting.rain_barrel_diverter":   1,
        },
    },

    # G. Gas System
    "GAS_POOL_HEATER_KIT": {
        "name": "Gas Line Pool Heater Kit",
        "labor_template": "GAS_LINE_POOL_HEATER",
        "items": {
            "pipe.csst_3_4_per_ft":           40,
            "fitting.gas_termination_3_4":    1,
        },
    },
    "GAS_GENERATOR_KIT": {
        "name": "Gas Line Generator Kit",
        "labor_template": "GAS_LINE_GENERATOR",
        "items": {
            "pipe.csst_3_4_per_ft":           50,
            "fitting.gas_termination_3_4":    1,
        },
    },
    "GAS_TANKLESS_UPGRADE_KIT": {
        "name": "Gas Line Tankless WH Upgrade Kit",
        "labor_template": "GAS_LINE_TANKLESS_WH",
        "items": {
            "pipe.csst_3_4_per_ft":           20,
            "fitting.gas_termination_3_4":    1,
        },
    },
    "GAS_CAP_KIT": {
        "name": "Gas Appliance Disconnect & Cap Kit",
        "labor_template": "GAS_APPLIANCE_DISCONNECT",
        "items": {
            "fitting.gas_cap_3_4":            1,
        },
    },

    # H. Water Treatment
    "WATER_SOFTENER_REPLACE_KIT": {
        "name": "Water Softener Replace Kit",
        "labor_template": "WATER_SOFTENER_REPLACE",
        "items": {
            "appliance.water_softener_48k":   1,
        },
    },
    "UV_SYSTEM_KIT": {
        "name": "UV Disinfection System Kit",
        "labor_template": "UV_DISINFECTION_INSTALL",
        "items": {
            "appliance.uv_system_12gpm":      1,
        },
    },
    "SEDIMENT_FILTER_KIT": {
        "name": "Sediment Filter Install Kit",
        "labor_template": "SEDIMENT_FILTER_INSTALL",
        "items": {
            "filter.sediment_whole_house_20in": 1,
        },
    },

    # J. Maintenance
    "HOSE_BIB_COVER_KIT": {
        "name": "Hose Bib Winterization Kit (per bib)",
        "labor_template": "HOSE_BIB_WINTERIZE",
        "items": {
            "material.hose_bib_cover_insulated": 1,
        },
    },

    # ── Phase 4: Material Assemblies ──────────────────────────────────────────

    # K. Construction
    "SEWER_TAP_KIT": {
        "name": "Sewer Tap & Connection Kit",
        "labor_template": "SEWER_TAP_CONNECTION",
        "items": {
            "fitting.sewer_wye_4in":  1,
        },
    },
    "WATER_TAP_KIT": {
        "name": "Water Service Tap Kit",
        "labor_template": "WATER_TAP_CONNECTION",
        "items": {
            "fitting.water_service_adapter_1in": 1,
        },
    },
    "SPRINKLER_HEAD_KIT": {
        "name": "Residential Fire Sprinkler Kit (per head)",
        "labor_template": "FIRE_SPRINKLER_RESIDENTIAL",
        "items": {
            "safety.fire_sprinkler_head_pendent": 1,
        },
    },
    "RECIRC_LOOP_KIT": {
        "name": "Tankless Recirculation Loop Kit",
        "labor_template": "TANKLESS_RECIRCULATION_LOOP",
        "items": {
            "pipe.recirc_pex_1_2_per_ft": 60,
            "pump.recirc_1_25in":         1,
        },
    },

    # L. Commercial
    "COMMERCIAL_TOILET_KIT": {
        "name": "Commercial Floor Mount Toilet Kit",
        "labor_template": "COMMERCIAL_TOILET_INSTALL",
        "items": {
            "fixture.commercial_toilet_floor_mount": 1,
            "valve.flushometer_1_6gpf":             1,
        },
    },
    "WALL_HUNG_TOILET_KIT": {
        "name": "Wall-Hung Toilet with Carrier Kit",
        "labor_template": "COMMERCIAL_WALL_HUNG_TOILET",
        "items": {
            "fixture.wall_hung_toilet_carrier":     1,
            "valve.flushometer_1_6gpf":             1,
        },
    },
    "URINAL_INSTALL_KIT": {
        "name": "Commercial Urinal Install Kit",
        "labor_template": "COMMERCIAL_URINAL_INSTALL",
        "items": {
            "fixture.urinal_wall_mount":            1,
            "valve.urinal_flush_05gpf":             1,
        },
    },
    "FOUNTAIN_KIT": {
        "name": "Drinking Fountain / Bottle Filler Kit",
        "labor_template": "DRINKING_FOUNTAIN_INSTALL",
        "items": {
            "fixture.drinking_fountain_ada":        1,
        },
    },
    "EYEWASH_KIT": {
        "name": "Emergency Eyewash/Shower Station Kit",
        "labor_template": "EYE_WASH_STATION_INSTALL",
        "items": {
            "safety.eyewash_station_combo":         1,
        },
    },
    "MOP_SINK_KIT": {
        "name": "Mop/Service Sink Kit",
        "labor_template": "MOP_SINK_INSTALL",
        "items": {
            "fixture.mop_sink_24in":                1,
        },
    },
    "SENSOR_FAUCET_KIT": {
        "name": "Hands-Free Sensor Faucet Kit",
        "labor_template": "HANDS_FREE_FAUCET_INSTALL",
        "items": {
            "faucet.sensor_lavatory":               1,
        },
    },
    "COMMERCIAL_PRV_KIT": {
        "name": "Commercial PRV Kit",
        "labor_template": "COMMERCIAL_PRV_INSTALL",
        "items": {
            "valve.commercial_prv_1_5in":           1,
        },
    },
    "TMV_KIT": {
        "name": "Thermostatic Mixing Valve Kit",
        "labor_template": "TMV_INSTALL",
        "items": {
            "valve.tmv_asse1017":                   1,
        },
    },
    "ROOF_DRAIN_KIT": {
        "name": "Commercial Roof Drain Kit",
        "labor_template": "ROOF_DRAIN_INSTALL",
        "items": {
            "fitting.roof_drain_4in_cast":          1,
        },
    },
    "COMMERCIAL_SOFTENER_KIT": {
        "name": "Commercial Water Softener Kit",
        "labor_template": "COMMERCIAL_WATER_SOFTENER",
        "items": {
            "appliance.commercial_softener_100k":   1,
        },
    },
    "BACKFLOW_REPAIR_KIT": {
        "name": "Backflow Preventer Repair Kit",
        "labor_template": "BACKFLOW_PREVENTER_REPAIR",
        "items": {
            "valve.backflow_repair_kit_generic":    1,
        },
    },

    # M. Water Heater & Fixture Gaps
    "WH_GAS_VALVE_KIT": {
        "name": "WH Gas Control Valve Kit",
        "labor_template": "WH_GAS_VALVE_REPLACE",
        "items": {
            "valve.wh_gas_control":                 1,
        },
    },
    "TPR_VALVE_KIT": {
        "name": "T&P Relief Valve Kit",
        "labor_template": "TPR_VALVE_REPLACE",
        "items": {
            "valve.tpr_3_4":                        1,
        },
    },
    "TUB_DRAIN_KIT": {
        "name": "Tub Drain Assembly Kit",
        "labor_template": "TUB_DRAIN_ASSEMBLY_REPLACE",
        "items": {
            "fixture.tub_drain_assembly":           1,
        },
    },
    "SHOWER_DRAIN_KIT": {
        "name": "Shower Drain Kit",
        "labor_template": "SHOWER_DRAIN_REPLACE",
        "items": {
            "fixture.shower_drain_square_4":        1,
        },
    },
    "FLOOR_DRAIN_KIT": {
        "name": "Residential Floor Drain Kit",
        "labor_template": "FLOOR_DRAIN_RESIDENTIAL",
        "items": {
            "fixture.floor_drain_4in":              1,
        },
    },

    # N. Valves & Backflow
    "RPZ_REBUILD_KIT": {
        "name": "RPZ Rebuild Kit",
        "labor_template": "RPZ_REBUILD",
        "items": {
            "valve.rpz_rebuild_kit":                1,
        },
    },
    "DCVA_REPAIR_KIT": {
        "name": "DCVA Repair Kit",
        "labor_template": "DCVA_REPAIR",
        "items": {
            "valve.dcva_repair_kit":                1,
        },
    },
    "EARTHQUAKE_VALVE_KIT": {
        "name": "Earthquake Gas Shutoff Valve Kit",
        "labor_template": "EARTHQUAKE_VALVE_INSTALL",
        "items": {
            "valve.earthquake_gas_shutoff":         1,
        },
    },
    "DRIP_LEG_KIT": {
        "name": "Gas Drip Leg Assembly Kit",
        "labor_template": "GAS_DRIP_LEG_INSTALL",
        "items": {
            "fitting.gas_drip_leg_1_2":             1,
        },
    },
    "BALL_VALVE_KIT": {
        "name": "Ball Valve Upgrade Kit (per valve)",
        "labor_template": "GATE_TO_BALL_VALVE_UPGRADE",
        "items": {
            "valve.ball_3_4_full_port":             1,
        },
    },

    # O. Appliance Connections
    "WASHER_HOSE_KIT": {
        "name": "Washing Machine Hose Kit (pair)",
        "labor_template": "WASHING_MACHINE_HOSE_REPLACE",
        "items": {
            "pipe.washer_hose_ss_pair":             1,
        },
    },
    "DW_SUPPLY_KIT": {
        "name": "Dishwasher Supply Line Kit",
        "labor_template": "DISHWASHER_SUPPLY_INSTALL",
        "items": {
            "pipe.dw_supply_braided":               1,
        },
    },
    "GAS_RANGE_CONNECTOR_KIT": {
        "name": "Gas Range Connector Kit",
        "labor_template": "GAS_RANGE_CONNECTOR_REPLACE",
        "items": {
            "pipe.gas_range_connector_48":          1,
        },
    },

    # P. Specialty & Emerging
    "RADIANT_LOOP_KIT": {
        "name": "Radiant Floor Heat Plumbing Kit",
        "labor_template": "RADIANT_FLOOR_LOOP",
        "items": {
            "valve.radiant_manifold_4loop":         1,
        },
    },
    "WELL_TANK_KIT": {
        "name": "Well Pressure Tank Kit",
        "labor_template": "WELL_PRESSURE_TANK_REPLACE",
        "items": {
            "pump.well_pressure_tank_32g":          1,
        },
    },
    "TRAP_PRIMER_KIT": {
        "name": "Trap Primer Kit",
        "labor_template": "TRAP_PRIMER_INSTALL",
        "items": {
            "valve.trap_primer_3_4":                1,
        },
    },
    "EXTERIOR_CLEANOUT_KIT": {
        "name": "Exterior Two-Way Cleanout Kit",
        "labor_template": "CLEANOUT_INSTALL_EXTERIOR",
        "items": {
            "fitting.cleanout_two_way_4in":         1,
        },
    },
    "BODY_SPRAY_KIT": {
        "name": "Shower Body Spray Kit (pair)",
        "labor_template": "SHOWER_BODY_SPRAY_INSTALL",
        "items": {
            "fixture.body_spray_pair":              1,
        },
    },
    "DUAL_FLUSH_KIT": {
        "name": "Dual Flush Conversion Kit",
        "labor_template": "DUAL_FLUSH_CONVERSION",
        "items": {
            "valve.dual_flush_retrofit":            1,
        },
    },
    }


@dataclass
class MaterialCostResult:
    canonical_item: str
    preferred_supplier: Optional[str]
    selected_supplier: str
    sku: Optional[str]
    name: str
    unit_cost: float
    confidence: float = 1.0
    source: str = "canonical_map"


class SupplierService:

    async def get_material_cost(
        self,
        canonical_item: str,
        preferred_supplier: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[MaterialCostResult]:
        """Look up material cost. Priority: DB → enrichment cache → canonical map."""

        # Tier 1: Database
        if db:
            result = await self._db_lookup(db, canonical_item, preferred_supplier)
            if result:
                return result

        # Tier 2-4: enrichment service (Apify → ConstructAPI → CWICR → canonical_map)
        enrichment = get_enrichment_service()
        # Get fallback cost from CANONICAL_MAP so enrichment can use it as last resort
        canonical_fallback = self._canonical_cost(canonical_item, preferred_supplier)
        enriched = await enrichment.get_price(canonical_item, fallback_cost=canonical_fallback)
        if enriched:
            # Prefer supplier-specific name/sku from CANONICAL_MAP if available
            base = self._canonical_lookup(canonical_item, preferred_supplier)
            return MaterialCostResult(
                canonical_item=canonical_item,
                preferred_supplier=preferred_supplier,
                selected_supplier=base.selected_supplier if base else (preferred_supplier or "market"),
                sku=enriched.sku or (base.sku if base else None),
                name=enriched.name or (base.name if base else canonical_item),
                unit_cost=enriched.unit_cost,
                confidence=0.9 if enriched.source != "canonical_map" else 1.0,
                source=enriched.source,
            )

        # Final fallback: hardcoded canonical map
        return self._canonical_lookup(canonical_item, preferred_supplier)

    async def _db_lookup(
        self, db: AsyncSession, canonical_item: str, preferred_supplier: Optional[str]
    ) -> Optional[MaterialCostResult]:
        try:
            query = (
                select(SupplierProduct, Supplier)
                .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
                .where(
                    and_(
                        SupplierProduct.canonical_item == canonical_item,
                        SupplierProduct.is_active == True,
                    )
                )
                .order_by(SupplierProduct.cost.asc())
            )

            result = await db.execute(query)
            rows = result.all()

            if not rows:
                return None

            # Prefer the requested supplier if present; otherwise use cheapest
            selected = None
            if preferred_supplier:
                for product, supplier in rows:
                    if supplier.slug == preferred_supplier:
                        selected = (product, supplier)
                        break
            if selected is None:
                selected = rows[0]

            product, supplier = selected
            return MaterialCostResult(
                canonical_item=canonical_item,
                preferred_supplier=preferred_supplier,
                selected_supplier=supplier.slug,
                sku=product.sku,
                name=product.name,
                unit_cost=product.cost,
                confidence=product.confidence_score,
                source="database",
            )
        except Exception as e:
            logger.warning("DB lookup failed, falling back to canonical map", error=str(e))

        return None

    def _canonical_lookup(
        self, canonical_item: str, preferred_supplier: Optional[str] = None
    ) -> Optional[MaterialCostResult]:
        item_map = CANONICAL_MAP.get(canonical_item)
        if not item_map:
            return None

        # Use preferred supplier if available
        if preferred_supplier and preferred_supplier in item_map:
            supplier_data = item_map[preferred_supplier]
            return MaterialCostResult(
                canonical_item=canonical_item,
                preferred_supplier=preferred_supplier,
                selected_supplier=preferred_supplier,
                sku=supplier_data.get("sku"),
                name=supplier_data["name"],
                unit_cost=supplier_data["cost"],
                source="canonical_map",
            )

        # Find lowest cost supplier
        best_supplier = None
        best_data = None
        best_cost = float("inf")

        for supplier_slug, data in item_map.items():
            if data["cost"] < best_cost:
                best_cost = data["cost"]
                best_supplier = supplier_slug
                best_data = data

        if best_data:
            return MaterialCostResult(
                canonical_item=canonical_item,
                preferred_supplier=preferred_supplier,
                selected_supplier=best_supplier,
                sku=best_data.get("sku"),
                name=best_data["name"],
                unit_cost=best_data["cost"],
                source="canonical_map",
            )

        return None

    def _canonical_cost(
        self, canonical_item: str, preferred_supplier: Optional[str] = None
    ) -> Optional[float]:
        """Return just the unit cost from the canonical map (no DB, no enrichment)."""
        result = self._canonical_lookup(canonical_item, preferred_supplier)
        return result.unit_cost if result else None

    async def _db_lookup_batch(
        self,
        db: AsyncSession,
        canonical_items: list[str],
        preferred_supplier: Optional[str] = None,
    ) -> dict[str, "MaterialCostResult"]:
        """Single query to fetch prices for multiple canonical items."""
        try:
            query = (
                select(SupplierProduct, Supplier)
                .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
                .where(
                    and_(
                        SupplierProduct.canonical_item.in_(canonical_items),
                        SupplierProduct.is_active == True,
                    )
                )
                .order_by(SupplierProduct.cost.asc())
            )
            result = await db.execute(query)
            rows = result.all()

            # Group by canonical_item; list is already sorted cheapest first
            by_item: dict[str, list] = {}
            for product, supplier in rows:
                by_item.setdefault(product.canonical_item, []).append((product, supplier))

            out: dict[str, MaterialCostResult] = {}
            for canonical_item, row_list in by_item.items():
                selected = None
                if preferred_supplier:
                    for product, supplier in row_list:
                        if supplier.slug == preferred_supplier:
                            selected = (product, supplier)
                            break
                if selected is None:
                    selected = row_list[0]  # cheapest
                product, supplier = selected
                out[canonical_item] = MaterialCostResult(
                    canonical_item=canonical_item,
                    preferred_supplier=preferred_supplier,
                    selected_supplier=supplier.slug,
                    sku=product.sku,
                    name=product.name,
                    unit_cost=product.cost,
                    confidence=product.confidence_score,
                    source="database",
                )
            return out
        except Exception as e:
            logger.warning("Batch DB lookup failed, falling back to canonical map", error=str(e))
            return {}

    async def get_assembly_costs(
        self,
        assembly_code: str,
        preferred_supplier: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[MaterialItem]:
        """Get all material costs for an assembly (single DB query when DB available)."""

        assembly = MATERIAL_ASSEMBLIES.get(assembly_code)
        if not assembly:
            logger.warning("Assembly not found", assembly_code=assembly_code)
            return []

        item_quantities = assembly["items"]
        canonical_items = list(item_quantities.keys())

        # Batch-fetch from DB in a single query, then fall back per-item to canonical map
        db_results: dict[str, MaterialCostResult] = {}
        if db:
            db_results = await self._db_lookup_batch(db, canonical_items, preferred_supplier)

        items = []
        for canonical_item, quantity in item_quantities.items():
            result = db_results.get(canonical_item) or self._canonical_lookup(canonical_item, preferred_supplier)
            if result:
                items.append(MaterialItem(
                    canonical_item=canonical_item,
                    description=result.name,
                    quantity=quantity,
                    unit="ea",
                    unit_cost=result.unit_cost,
                    supplier=result.selected_supplier,
                    sku=result.sku,
                ))
            else:
                logger.warning("No price found for canonical item", item=canonical_item)

        return items

    async def compare_suppliers(
        self,
        canonical_items: list[str],
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """Compare costs across all suppliers for a list of canonical items."""

        comparison = {}
        totals = {"ferguson": 0.0, "moore_supply": 0.0, "apex": 0.0}

        for item in canonical_items:
            item_map = CANONICAL_MAP.get(item, {})
            comparison[item] = {}

            for supplier in ["ferguson", "moore_supply", "apex"]:
                if supplier in item_map:
                    data = item_map[supplier]
                    comparison[item][supplier] = {
                        "sku": data.get("sku"),
                        "name": data["name"],
                        "cost": data["cost"],
                    }
                    totals[supplier] += data["cost"]
                else:
                    comparison[item][supplier] = None

        best_supplier = min(totals, key=totals.get) if any(totals.values()) else None

        return {
            "items": comparison,
            "totals": totals,
            "best_value_supplier": best_supplier,
        }


supplier_service = SupplierService()
