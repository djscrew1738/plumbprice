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
        """Look up material cost. Tries DB first, falls back to canonical map."""

        # Try DB first if session provided
        if db:
            result = await self._db_lookup(db, canonical_item, preferred_supplier)
            if result:
                return result

        # Fallback to in-memory canonical map
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

    async def get_assembly_costs(
        self,
        assembly_code: str,
        preferred_supplier: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[MaterialItem]:
        """Get all material costs for an assembly."""

        assembly = MATERIAL_ASSEMBLIES.get(assembly_code)
        if not assembly:
            logger.warning("Assembly not found", assembly_code=assembly_code)
            return []

        items = []
        for canonical_item, quantity in assembly["items"].items():
            result = await self.get_material_cost(canonical_item, preferred_supplier, db)
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
