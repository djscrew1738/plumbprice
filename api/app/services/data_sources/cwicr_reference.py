"""
DDC CWICR — Construction Work Item Cost Reference (static plumbing reference data).

Source: Derived from RSMeans Plumbing Cost Data, Craftsman Construction Cost Guide,
and NCCER plumbing trade data. DFW / Texas market pricing, 2025 Q2.

Canonical IDs match supplier_service.CANONICAL_MAP exactly so tier-4 fallback
prices are always available for every item in the pricing engine.
All costs are wholesale/trade pricing (not retail markup).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CWICRItem:
    cwicr_code: str
    canonical_id: str
    name: str
    category: str
    unit: str
    unit_cost_usd: float
    cost_low: float
    cost_high: float
    source: str = "cwicr"


# ─── DFW Plumbing Work Item Cost Reference ────────────────────────────────────
# Keys MUST match supplier_service.CANONICAL_MAP exactly.
# Prices reflect DFW wholesale / trade rates, 2025 Q2.

CWICR_PLUMBING: dict[str, CWICRItem] = {

    # ── Toilet assembly ──────────────────────────────────────────────────────
    "toilet.wax_ring": CWICRItem(
        cwicr_code="P-102.1", canonical_id="toilet.wax_ring",
        name="Closet wax ring with plastic horn sleeve",
        category="plumbing.fixtures.toilet", unit="ea",
        unit_cost_usd=8.25, cost_low=6.95, cost_high=10.50,
    ),
    "toilet.closet_bolts": CWICRItem(
        cwicr_code="P-102.2", canonical_id="toilet.closet_bolts",
        name="Closet bolt set, brass, 5/16\" x 2-1/4\"",
        category="plumbing.fixtures.toilet", unit="set",
        unit_cost_usd=5.95, cost_low=4.75, cost_high=7.50,
    ),
    "toilet.supply_line_12": CWICRItem(
        cwicr_code="P-102.3", canonical_id="toilet.supply_line_12",
        name="Supply line, braided SS, 3/8\" comp x 7/8\" bsp, 12\"",
        category="plumbing.fixtures.toilet", unit="ea",
        unit_cost_usd=10.50, cost_low=8.95, cost_high=13.25,
    ),
    "toilet.comfort_height_unit": CWICRItem(
        cwicr_code="P-102.5", canonical_id="toilet.comfort_height_unit",
        name="Toilet, elongated, comfort height, 1.28 GPF, white",
        category="plumbing.fixtures.toilet", unit="ea",
        unit_cost_usd=225.00, cost_low=185.00, cost_high=295.00,
    ),
    "toilet.fill_valve_400a": CWICRItem(
        cwicr_code="P-102.6", canonical_id="toilet.fill_valve_400a",
        name="Fill valve, Fluidmaster 400A, adjustable float",
        category="plumbing.fixtures.toilet", unit="ea",
        unit_cost_usd=9.75, cost_low=7.95, cost_high=12.50,
    ),
    "toilet.flapper_korky": CWICRItem(
        cwicr_code="P-102.7", canonical_id="toilet.flapper_korky",
        name="Toilet flapper, Korky 100BP, universal fit",
        category="plumbing.fixtures.toilet", unit="ea",
        unit_cost_usd=4.25, cost_low=3.25, cost_high=6.00,
    ),

    # ── Angle stops ──────────────────────────────────────────────────────────
    "angle_stop.quarter_turn_3_8": CWICRItem(
        cwicr_code="P-103.1", canonical_id="angle_stop.quarter_turn_3_8",
        name="Angle stop valve, 1/2\" NPS x 3/8\" OD, chrome, quarter-turn",
        category="plumbing.valves", unit="ea",
        unit_cost_usd=11.25, cost_low=9.50, cost_high=14.00,
    ),
    "angle_stop.supply_line_12": CWICRItem(
        cwicr_code="P-103.2", canonical_id="angle_stop.supply_line_12",
        name="Supply line, braided SS, 3/8\" x 3/8\", 12\"",
        category="plumbing.valves", unit="ea",
        unit_cost_usd=9.50, cost_low=7.95, cost_high=12.00,
    ),

    # ── Water heater — Gas 50G ────────────────────────────────────────────────
    "wh.50g_gas_unit": CWICRItem(
        cwicr_code="W-201.1", canonical_id="wh.50g_gas_unit",
        name="Water heater, gas, 50-gal, 40 MBH, 6-yr warranty",
        category="plumbing.waterheater.gas", unit="ea",
        unit_cost_usd=585.00, cost_low=540.00, cost_high=660.00,
    ),
    "wh.gas_flex_connector_18": CWICRItem(
        cwicr_code="W-201.2", canonical_id="wh.gas_flex_connector_18",
        name="Gas flex connector, corrugated SS, 3/4\" FIP x 3/4\" FIP, 18\"",
        category="plumbing.waterheater.gas", unit="ea",
        unit_cost_usd=13.75, cost_low=11.50, cost_high=16.50,
    ),
    "wh.expansion_tank_2g": CWICRItem(
        cwicr_code="W-201.3", canonical_id="wh.expansion_tank_2g",
        name="Thermal expansion tank, 2-gal, potable water",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=41.50, cost_low=36.00, cost_high=48.00,
    ),
    "wh.tp_valve_075": CWICRItem(
        cwicr_code="W-201.4", canonical_id="wh.tp_valve_075",
        name="T&P relief valve, 3/4\" NPT, 150 PSI / 210°F",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=22.00, cost_low=18.50, cost_high=26.00,
    ),
    "wh.dielectric_union_pair": CWICRItem(
        cwicr_code="W-201.5", canonical_id="wh.dielectric_union_pair",
        name="Dielectric union pair, 3/4\" NPT",
        category="plumbing.waterheater.accessories", unit="pr",
        unit_cost_usd=17.50, cost_low=14.50, cost_high=21.00,
    ),
    "wh.drain_pan_26": CWICRItem(
        cwicr_code="W-201.6", canonical_id="wh.drain_pan_26",
        name="Water heater drain pan, 26\", galvanized with drain",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=27.50, cost_low=22.00, cost_high=33.00,
    ),
    "wh.overflow_line_075": CWICRItem(
        cwicr_code="W-201.7", canonical_id="wh.overflow_line_075",
        name="Overflow/relief line, 3/4\" CPVC, 18\" with elbow",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=8.25, cost_low=6.50, cost_high=10.50,
    ),

    # ── Water heater — Gas 40G ────────────────────────────────────────────────
    "wh.40g_gas_unit": CWICRItem(
        cwicr_code="W-202.1", canonical_id="wh.40g_gas_unit",
        name="Water heater, gas, 40-gal, 36 MBH, 6-yr warranty",
        category="plumbing.waterheater.gas", unit="ea",
        unit_cost_usd=510.00, cost_low=470.00, cost_high=575.00,
    ),

    # ── Water heater — Electric 50G ───────────────────────────────────────────
    "wh.50g_electric_unit": CWICRItem(
        cwicr_code="W-203.1", canonical_id="wh.50g_electric_unit",
        name="Water heater, electric, 50-gal, 4.5kW, 6-yr warranty",
        category="plumbing.waterheater.electric", unit="ea",
        unit_cost_usd=520.00, cost_low=480.00, cost_high=590.00,
    ),
    "wh.water_supply_line_18": CWICRItem(
        cwicr_code="W-203.2", canonical_id="wh.water_supply_line_18",
        name="Supply line, braided SS, 3/4\" x 3/4\", 18\"",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=12.50, cost_low=10.50, cost_high=15.50,
    ),

    # ── Water heater — Tankless ────────────────────────────────────────────────
    "wh.tankless_navien_180k": CWICRItem(
        cwicr_code="W-204.1", canonical_id="wh.tankless_navien_180k",
        name="Tankless water heater, gas, 180K BTU, condensing",
        category="plumbing.waterheater.tankless", unit="ea",
        unit_cost_usd=1175.00, cost_low=1095.00, cost_high=1295.00,
    ),
    "wh.gas_flex_connector_24": CWICRItem(
        cwicr_code="W-204.2", canonical_id="wh.gas_flex_connector_24",
        name="Gas flex connector, corrugated SS, 3/4\" FIP x 3/4\" FIP, 24\"",
        category="plumbing.waterheater.gas", unit="ea",
        unit_cost_usd=16.50, cost_low=13.50, cost_high=19.50,
    ),
    "wh.tankless_water_filter": CWICRItem(
        cwicr_code="W-204.3", canonical_id="wh.tankless_water_filter",
        name="Inline sediment filter, 3/4\" NPT, for tankless WH",
        category="plumbing.waterheater.tankless", unit="ea",
        unit_cost_usd=18.50, cost_low=15.00, cost_high=22.50,
    ),

    # ── Expansion tank (standalone category) ─────────────────────────────────
    "exp_tank.2gal_thermal": CWICRItem(
        cwicr_code="W-205.1", canonical_id="exp_tank.2gal_thermal",
        name="Thermal expansion tank, 2-gal, pre-charged, potable",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=41.50, cost_low=36.00, cost_high=48.00,
    ),
    "exp_tank.nipple_34": CWICRItem(
        cwicr_code="W-205.2", canonical_id="exp_tank.nipple_34",
        name="Nipple, 3/4\" x 3\" close nipple, galvanized",
        category="plumbing.waterheater.accessories", unit="ea",
        unit_cost_usd=3.75, cost_low=2.75, cost_high=5.00,
    ),

    # ── PRV ───────────────────────────────────────────────────────────────────
    "prv.watts_3_4": CWICRItem(
        cwicr_code="P-301.1", canonical_id="prv.watts_3_4",
        name="Pressure reducing valve, 3/4\" NPT, adjustable 25–75 PSI",
        category="plumbing.valves.prv", unit="ea",
        unit_cost_usd=52.00, cost_low=44.00, cost_high=62.00,
    ),
    "prv.union_3_4": CWICRItem(
        cwicr_code="P-301.2", canonical_id="prv.union_3_4",
        name="Union, 3/4\" FIP x FIP, brass",
        category="plumbing.valves.prv", unit="ea",
        unit_cost_usd=14.50, cost_low=11.50, cost_high=17.50,
    ),

    # ── Hose bib ──────────────────────────────────────────────────────────────
    "hose_bib.frost_free_12": CWICRItem(
        cwicr_code="P-401.1", canonical_id="hose_bib.frost_free_12",
        name="Frost-free hose bib, 1/2\" MIP, 12\" stem, vacuum breaker",
        category="plumbing.fixtures.hosebib", unit="ea",
        unit_cost_usd=28.50, cost_low=23.00, cost_high=34.00,
    ),
    "hose_bib.escutcheon_chrome": CWICRItem(
        cwicr_code="P-401.2", canonical_id="hose_bib.escutcheon_chrome",
        name="Escutcheon plate, chrome, 1/2\" pipe",
        category="plumbing.fixtures.hosebib", unit="ea",
        unit_cost_usd=4.25, cost_low=3.25, cost_high=5.50,
    ),

    # ── Gas valves ────────────────────────────────────────────────────────────
    "gas.ball_valve_3_4": CWICRItem(
        cwicr_code="G-101.1", canonical_id="gas.ball_valve_3_4",
        name="Ball valve, 3/4\" FIP x FIP, yellow handle, gas rated",
        category="plumbing.gas.valves", unit="ea",
        unit_cost_usd=24.50, cost_low=20.00, cost_high=29.00,
    ),
    "gas.teflon_tape_yellow": CWICRItem(
        cwicr_code="G-101.2", canonical_id="gas.teflon_tape_yellow",
        name="Thread seal tape, yellow, gas/fuel, 1/2\" x 260\"",
        category="plumbing.gas.fittings", unit="ea",
        unit_cost_usd=2.25, cost_low=1.75, cost_high=3.00,
    ),

    # ── Kitchen sink ──────────────────────────────────────────────────────────
    "kitchen.basket_strainer": CWICRItem(
        cwicr_code="P-501.1", canonical_id="kitchen.basket_strainer",
        name="Basket strainer, chrome finish, with basket",
        category="plumbing.fixtures.kitchen", unit="ea",
        unit_cost_usd=24.50, cost_low=19.00, cost_high=30.00,
    ),
    "kitchen.supply_lines_20_pair": CWICRItem(
        cwicr_code="P-501.2", canonical_id="kitchen.supply_lines_20_pair",
        name="Supply lines, braided SS, 3/8\" x 1/2\", 20\", pair",
        category="plumbing.fixtures.kitchen", unit="pr",
        unit_cost_usd=18.50, cost_low=14.50, cost_high=23.00,
    ),
    "kitchen.teflon_tape": CWICRItem(
        cwicr_code="P-501.3", canonical_id="kitchen.teflon_tape",
        name="Thread seal tape, white, 1/2\" x 520\"",
        category="plumbing.fittings.misc", unit="ea",
        unit_cost_usd=1.25, cost_low=0.95, cost_high=1.75,
    ),

    # ── Lav sink ─────────────────────────────────────────────────────────────
    "lav.pop_up_drain": CWICRItem(
        cwicr_code="P-502.1", canonical_id="lav.pop_up_drain",
        name="Pop-up drain assembly, chrome, with rod and clips",
        category="plumbing.fixtures.lav", unit="ea",
        unit_cost_usd=14.50, cost_low=11.50, cost_high=18.00,
    ),
    "lav.supply_lines_12_pair": CWICRItem(
        cwicr_code="P-502.2", canonical_id="lav.supply_lines_12_pair",
        name="Supply lines, braided SS, 3/8\" comp x 1/2\" FIP, 12\", pair",
        category="plumbing.fixtures.lav", unit="pr",
        unit_cost_usd=16.50, cost_low=13.00, cost_high=20.50,
    ),
    "lav_sink.drain_grid_chrome": CWICRItem(
        cwicr_code="P-502.3", canonical_id="lav_sink.drain_grid_chrome",
        name="Grid drain, chrome, 1-1/2\" NPT",
        category="plumbing.fixtures.lav", unit="ea",
        unit_cost_usd=11.50, cost_low=9.00, cost_high=14.50,
    ),
    "lav_sink.p_trap_white": CWICRItem(
        cwicr_code="P-502.4", canonical_id="lav_sink.p_trap_white",
        name="P-trap, white PVC, 1-1/2\" with slip joint",
        category="plumbing.fixtures.lav", unit="ea",
        unit_cost_usd=7.25, cost_low=5.75, cost_high=9.50,
    ),

    # ── P-trap (standalone) ───────────────────────────────────────────────────
    "ptrap.chrome_1_5_inch": CWICRItem(
        cwicr_code="D-101.1", canonical_id="ptrap.chrome_1_5_inch",
        name="P-trap, chrome brass, 1-1/2\" slip joint",
        category="plumbing.drain", unit="ea",
        unit_cost_usd=18.50, cost_low=15.00, cost_high=23.00,
    ),
    "ptrap.extension_tube_12": CWICRItem(
        cwicr_code="D-101.2", canonical_id="ptrap.extension_tube_12",
        name="Extension tube, chrome, 1-1/2\" x 12\" slip joint",
        category="plumbing.drain", unit="ea",
        unit_cost_usd=7.25, cost_low=5.75, cost_high=9.00,
    ),

    # ── Clean-out ─────────────────────────────────────────────────────────────
    "clean_out.4in_co_wye": CWICRItem(
        cwicr_code="D-201.1", canonical_id="clean_out.4in_co_wye",
        name="Clean-out wye, ABS 4\", with threaded plug",
        category="plumbing.drain.cleanout", unit="ea",
        unit_cost_usd=18.50, cost_low=14.50, cost_high=23.00,
    ),
    "clean_out.co_plug_4in": CWICRItem(
        cwicr_code="D-201.2", canonical_id="clean_out.co_plug_4in",
        name="Clean-out plug, ABS 4\", threaded",
        category="plumbing.drain.cleanout", unit="ea",
        unit_cost_usd=5.25, cost_low=4.00, cost_high=6.75,
    ),
    "clean_out.fernco_4in": CWICRItem(
        cwicr_code="D-201.3", canonical_id="clean_out.fernco_4in",
        name="Fernco coupling, 4\" x 4\", flexible rubber",
        category="plumbing.drain.cleanout", unit="ea",
        unit_cost_usd=12.50, cost_low=9.75, cost_high=15.50,
    ),

    # ── PEX-A Repipe Materials ────────────────────────────────────────────────
    "repipe.pex_a_34_10ft": CWICRItem(
        cwicr_code="R-101.1", canonical_id="repipe.pex_a_34_10ft",
        name="PEX-A tubing, 3/4\" x 10ft (Uponor/Rehau or equal)",
        category="plumbing.repipe.pex", unit="10ft",
        unit_cost_usd=14.50, cost_low=12.00, cost_high=17.50,
    ),
    "repipe.pex_a_12_10ft": CWICRItem(
        cwicr_code="R-101.2", canonical_id="repipe.pex_a_12_10ft",
        name="PEX-A tubing, 1/2\" x 10ft (Uponor/Rehau or equal)",
        category="plumbing.repipe.pex", unit="10ft",
        unit_cost_usd=9.50, cost_low=7.75, cost_high=11.50,
    ),
    "repipe.uponor_manifold_6port": CWICRItem(
        cwicr_code="R-101.3", canonical_id="repipe.uponor_manifold_6port",
        name="PEX manifold, 6-port, 3/4\" header w/ 1/2\" ports",
        category="plumbing.repipe.pex", unit="ea",
        unit_cost_usd=68.50, cost_low=58.00, cost_high=80.00,
    ),
    "repipe.crimp_fitting_12_elbow": CWICRItem(
        cwicr_code="R-101.4", canonical_id="repipe.crimp_fitting_12_elbow",
        name="PEX crimp elbow, 1/2\" x 90°, copper crimp",
        category="plumbing.repipe.pex", unit="ea",
        unit_cost_usd=1.85, cost_low=1.40, cost_high=2.50,
    ),
    "repipe.crimp_ring_12": CWICRItem(
        cwicr_code="R-101.5", canonical_id="repipe.crimp_ring_12",
        name="PEX crimp ring, 1/2\" copper, 50-pack",
        category="plumbing.repipe.pex", unit="50-pk",
        unit_cost_usd=12.50, cost_low=10.00, cost_high=15.00,
    ),

    # ── Sewer Spot Repair ─────────────────────────────────────────────────────
    "sewer.pvc_pipe_4_10ft": CWICRItem(
        cwicr_code="D-301.1", canonical_id="sewer.pvc_pipe_4_10ft",
        name="PVC pipe, 4\" SDR-35, 10ft (sewer/drain grade)",
        category="plumbing.sewer", unit="10ft",
        unit_cost_usd=22.50, cost_low=18.00, cost_high=27.50,
    ),
    "sewer.fernco_4in_mission": CWICRItem(
        cwicr_code="D-301.2", canonical_id="sewer.fernco_4in_mission",
        name="Mission band coupling, 4\" x 4\", stainless clamps",
        category="plumbing.sewer", unit="ea",
        unit_cost_usd=14.50, cost_low=11.50, cost_high=17.50,
    ),
    "sewer.pvc_elbow_4in_45": CWICRItem(
        cwicr_code="D-301.3", canonical_id="sewer.pvc_elbow_4in_45",
        name="PVC 45° long sweep elbow, 4\" SDR-35",
        category="plumbing.sewer", unit="ea",
        unit_cost_usd=8.50, cost_low=6.75, cost_high=10.50,
    ),

    # ── Recirculation Pump ────────────────────────────────────────────────────
    "recirc.pump_grundfos_up15": CWICRItem(
        cwicr_code="W-301.1", canonical_id="recirc.pump_grundfos_up15",
        name="Recirculation pump, Grundfos UP15-10SU7P, 1/2\" sweat",
        category="plumbing.waterheater.recirc", unit="ea",
        unit_cost_usd=245.00, cost_low=215.00, cost_high=280.00,
    ),
    "recirc.aquamotion_comfort_valve": CWICRItem(
        cwicr_code="W-301.2", canonical_id="recirc.aquamotion_comfort_valve",
        name="Thermostatic comfort valve, 1/2\" under-sink, brass",
        category="plumbing.waterheater.recirc", unit="ea",
        unit_cost_usd=38.50, cost_low=32.00, cost_high=46.00,
    ),
    "recirc.supply_line_34_18": CWICRItem(
        cwicr_code="W-301.3", canonical_id="recirc.supply_line_34_18",
        name="Supply line, braided SS, 3/4\" x 3/4\", 18\"",
        category="plumbing.waterheater.recirc", unit="ea",
        unit_cost_usd=14.50, cost_low=11.50, cost_high=18.00,
    ),

    # ── Appliance Hookup ──────────────────────────────────────────────────────
    "appliance.supply_line_ss_24": CWICRItem(
        cwicr_code="P-901.1", canonical_id="appliance.supply_line_ss_24",
        name="Appliance supply line, braided SS, 1/2\" x 24\"",
        category="plumbing.appliance", unit="ea",
        unit_cost_usd=14.50, cost_low=11.50, cost_high=18.00,
    ),
    "appliance.drain_hose_72": CWICRItem(
        cwicr_code="P-901.2", canonical_id="appliance.drain_hose_72",
        name="Dishwasher drain hose, 5/8\" x 72\", corrugated",
        category="plumbing.appliance", unit="ea",
        unit_cost_usd=9.50, cost_low=7.50, cost_high=12.00,
    ),
    "appliance.drain_air_gap_chrome": CWICRItem(
        cwicr_code="P-901.3", canonical_id="appliance.drain_air_gap_chrome",
        name="Drain air gap, chrome, dishwasher",
        category="plumbing.appliance", unit="ea",
        unit_cost_usd=8.50, cost_low=6.75, cost_high=10.50,
    ),

    # ── Water Main / Shutoff ──────────────────────────────────────────────────
    "main.ball_valve_1in_fullport": CWICRItem(
        cwicr_code="P-201.1", canonical_id="main.ball_valve_1in_fullport",
        name="Ball valve, 1\" FIP x FIP, full port, brass",
        category="plumbing.valves.main", unit="ea",
        unit_cost_usd=34.50, cost_low=28.00, cost_high=42.00,
    ),
    "main.dielectric_union_1in": CWICRItem(
        cwicr_code="P-201.2", canonical_id="main.dielectric_union_1in",
        name="Dielectric union, 1\" FIP x FIP, brass body",
        category="plumbing.valves.main", unit="ea",
        unit_cost_usd=22.50, cost_low=18.00, cost_high=27.50,
    ),
    "main.copper_pipe_1in_10ft": CWICRItem(
        cwicr_code="P-201.3", canonical_id="main.copper_pipe_1in_10ft",
        name="Type L copper pipe, 1\" x 10ft, hard drawn",
        category="plumbing.valves.main", unit="10ft",
        unit_cost_usd=58.50, cost_low=48.00, cost_high=70.00,
    ),

    # ── Shower ────────────────────────────────────────────────────────────────
    "shower.trim_kit_brushed_nickel": CWICRItem(
        cwicr_code="P-601.1", canonical_id="shower.trim_kit_brushed_nickel",
        name="Shower trim kit, brushed nickel, for Moen/Price Pfister",
        category="plumbing.fixtures.shower", unit="kit",
        unit_cost_usd=68.00, cost_low=55.00, cost_high=85.00,
    ),
    "shower.cartridge_moen_1225": CWICRItem(
        cwicr_code="P-601.2", canonical_id="shower.cartridge_moen_1225",
        name="Cartridge, Moen 1225, replacement",
        category="plumbing.fixtures.shower", unit="ea",
        unit_cost_usd=24.50, cost_low=19.00, cost_high=30.00,
    ),
    "shower.seat_washers_kit": CWICRItem(
        cwicr_code="P-601.3", canonical_id="shower.seat_washers_kit",
        name="Seat and washer kit, assorted, faucet repair",
        category="plumbing.fixtures.shower", unit="kit",
        unit_cost_usd=6.75, cost_low=5.00, cost_high=8.50,
    ),
    "shower_head.arm_flange": CWICRItem(
        cwicr_code="P-601.4", canonical_id="shower_head.arm_flange",
        name="Shower arm and flange, chrome, 1/2\" FIP, 6\"",
        category="plumbing.fixtures.shower", unit="ea",
        unit_cost_usd=22.50, cost_low=17.50, cost_high=28.00,
    ),
    "shower_head.standard_chrome": CWICRItem(
        cwicr_code="P-601.5", canonical_id="shower_head.standard_chrome",
        name="Shower head, chrome, 2.5 GPM, fixed mount",
        category="plumbing.fixtures.shower", unit="ea",
        unit_cost_usd=28.00, cost_low=22.00, cost_high=36.00,
    ),

    # ── Tub / shower valve ────────────────────────────────────────────────────
    "tub_shower.moen_posi_temp_valve": CWICRItem(
        cwicr_code="P-602.1", canonical_id="tub_shower.moen_posi_temp_valve",
        name="Tub/shower valve body, Moen Posi-Temp, 1/2\" NPT",
        category="plumbing.fixtures.tub_shower", unit="ea",
        unit_cost_usd=95.00, cost_low=79.00, cost_high=115.00,
    ),
    "tub_shower.trim_kit_chrome": CWICRItem(
        cwicr_code="P-602.2", canonical_id="tub_shower.trim_kit_chrome",
        name="Tub/shower trim kit, chrome, for Moen Posi-Temp",
        category="plumbing.fixtures.tub_shower", unit="kit",
        unit_cost_usd=65.00, cost_low=52.00, cost_high=80.00,
    ),
    "tub_shower.diverter_tee": CWICRItem(
        cwicr_code="P-602.3", canonical_id="tub_shower.diverter_tee",
        name="Diverter tee, chrome, 1/2\" FIP x 1/2\" FIP x 1/2\" FIP",
        category="plumbing.fixtures.tub_shower", unit="ea",
        unit_cost_usd=18.50, cost_low=14.50, cost_high=23.00,
    ),
    "tub_shower.tub_spout_chrome": CWICRItem(
        cwicr_code="P-602.4", canonical_id="tub_shower.tub_spout_chrome",
        name="Tub spout, chrome, slip-fit 1/2\" IPS",
        category="plumbing.fixtures.tub_shower", unit="ea",
        unit_cost_usd=22.50, cost_low=17.50, cost_high=28.00,
    ),

    # ── Tub spout ─────────────────────────────────────────────────────────────
    "tub_spout.diverter_chrome": CWICRItem(
        cwicr_code="P-603.1", canonical_id="tub_spout.diverter_chrome",
        name="Tub spout with diverter, chrome, 1/2\" FIP",
        category="plumbing.fixtures.tub_shower", unit="ea",
        unit_cost_usd=24.50, cost_low=19.00, cost_high=30.00,
    ),
    "tub_spout.nipple_half": CWICRItem(
        cwicr_code="P-603.2", canonical_id="tub_spout.nipple_half",
        name="Nipple, 1/2\" x 3\" MIP, brass",
        category="plumbing.fixtures.tub_shower", unit="ea",
        unit_cost_usd=3.50, cost_low=2.75, cost_high=4.75,
    ),

    # ── Disposal ──────────────────────────────────────────────────────────────
    "disposal.power_cord_3prong": CWICRItem(
        cwicr_code="P-701.1", canonical_id="disposal.power_cord_3prong",
        name="Power cord, 3-prong, 32\" for garbage disposal",
        category="plumbing.fixtures.disposal", unit="ea",
        unit_cost_usd=12.50, cost_low=9.75, cost_high=15.50,
    ),
    "disposal.mounting_ring_kit": CWICRItem(
        cwicr_code="P-701.2", canonical_id="disposal.mounting_ring_kit",
        name="Mounting ring kit, universal, for disposals",
        category="plumbing.fixtures.disposal", unit="kit",
        unit_cost_usd=14.50, cost_low=11.00, cost_high=18.00,
    ),
    "disposal.drain_elbow_90": CWICRItem(
        cwicr_code="P-701.3", canonical_id="disposal.drain_elbow_90",
        name="Drain elbow, 90°, 1-1/2\" for disposal outlet",
        category="plumbing.fixtures.disposal", unit="ea",
        unit_cost_usd=8.50, cost_low=6.75, cost_high=10.50,
    ),

    # ── Water softener ────────────────────────────────────────────────────────
    "softener.unit_48k_grain": CWICRItem(
        cwicr_code="P-801.1", canonical_id="softener.unit_48k_grain",
        name="Water softener, 48,000 grain, metered, twin tank",
        category="plumbing.treatment.softener", unit="ea",
        unit_cost_usd=650.00, cost_low=580.00, cost_high=750.00,
    ),
    "softener.bypass_valve_1in": CWICRItem(
        cwicr_code="P-801.2", canonical_id="softener.bypass_valve_1in",
        name="Bypass valve assembly, 1\" for water softener",
        category="plumbing.treatment.softener", unit="ea",
        unit_cost_usd=28.50, cost_low=23.00, cost_high=35.00,
    ),
    "softener.supply_line_pair_1in": CWICRItem(
        cwicr_code="P-801.3", canonical_id="softener.supply_line_pair_1in",
        name="Supply lines, 1\" braided SS, 24\", pair",
        category="plumbing.treatment.softener", unit="pr",
        unit_cost_usd=32.50, cost_low=26.00, cost_high=40.00,
    ),
    "softener.brine_line_kit": CWICRItem(
        cwicr_code="P-801.4", canonical_id="softener.brine_line_kit",
        name="Brine line and fittings kit, 3/8\" poly tubing",
        category="plumbing.treatment.softener", unit="kit",
        unit_cost_usd=12.50, cost_low=9.75, cost_high=15.50,
    ),
}


# ─── Lookup helpers ───────────────────────────────────────────────────────────

def lookup(canonical_id: str) -> Optional[CWICRItem]:
    """Return CWICR reference item for the given canonical ID, or None."""
    return CWICR_PLUMBING.get(canonical_id)


def lookup_cost(canonical_id: str) -> Optional[float]:
    """Return the unit cost for a canonical ID, or None if not in reference."""
    item = lookup(canonical_id)
    return item.unit_cost_usd if item else None


def all_canonical_ids() -> list[str]:
    """Return all canonical IDs in the reference dataset."""
    return list(CWICR_PLUMBING.keys())
