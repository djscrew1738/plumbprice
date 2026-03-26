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

# ─── Canonical Item → Supplier Mapping ───────────────────────────────────────
# Fallback seed data for when DB is empty. Full DB seed in seed_db.py

CANONICAL_MAP: dict[str, dict[str, dict]] = {

    # ── Toilets ───────────────────────────────────────────────────────────────
    "toilet.elongated.standard": {
        "ferguson": {"sku": "PROFLO-EL-STDWH", "name": "ProFlo Elongated Standard 1.28gpf", "cost": 125.00},
        "moore_supply": {"sku": "MS-TOTO-DRAKE-EL", "name": "Toto Drake Elongated 1.28gpf", "cost": 142.00},
        "apex": {"sku": "APX-GER-EL-STD", "name": "Gerber Elongated Standard", "cost": 118.50},
    },
    "toilet.elongated.comfort_height": {
        "ferguson": {"sku": "PROFLO-EL-CHWH", "name": "ProFlo Elongated Comfort Height", "cost": 145.00},
        "moore_supply": {"sku": "MS-TOTO-DRAKE-CH", "name": "Toto Drake Comfort Height", "cost": 168.00},
        "apex": {"sku": "APX-GER-CH", "name": "Gerber Elongated Comfort Height", "cost": 138.00},
    },
    "toilet.round.standard": {
        "ferguson": {"sku": "PROFLO-RD-STDWH", "name": "ProFlo Round Standard", "cost": 109.00},
        "moore_supply": {"sku": "MS-TOTO-RD-STD", "name": "Toto Entrada Round", "cost": 119.00},
        "apex": {"sku": "APX-GER-RD-STD", "name": "Gerber Round Standard", "cost": 105.00},
    },
    "wax_ring.standard": {
        "ferguson": {"sku": "FER-WAX-STD", "name": "Wax Ring Standard", "cost": 6.50},
        "moore_supply": {"sku": "MS-WAX-STD", "name": "Wax Ring Standard", "cost": 7.00},
        "apex": {"sku": "APX-WAX-STD", "name": "Wax Ring Standard", "cost": 6.25},
    },
    "wax_ring.horn": {
        "ferguson": {"sku": "FER-WAX-HORN", "name": "Wax Ring with Horn", "cost": 9.50},
        "moore_supply": {"sku": "MS-WAX-HORN", "name": "Wax Ring with Horn", "cost": 10.00},
        "apex": {"sku": "APX-WAX-HORN", "name": "Wax Ring with Horn", "cost": 9.00},
    },
    "closet_bolts.standard": {
        "ferguson": {"sku": "FER-CB-STD", "name": "Closet Bolts 5/16x2.25\"", "cost": 4.25},
        "moore_supply": {"sku": "MS-CB-STD", "name": "Closet Bolts Standard", "cost": 4.50},
        "apex": {"sku": "APX-CB-STD", "name": "Closet Bolts Standard", "cost": 4.00},
    },

    # ── Water Heaters ─────────────────────────────────────────────────────────
    "water_heater.gas.50gal.standard": {
        "ferguson": {"sku": "RHEEM-PRO50-STD", "name": "Rheem Professional 50G Gas 9yr", "cost": 485.00},
        "moore_supply": {"sku": "MS-AO-50G-STD", "name": "AO Smith Signature 50G Gas", "cost": 498.00},
        "apex": {"sku": "APX-BRAW-50G", "name": "Bradford White 50G Gas", "cost": 512.00},
    },
    "water_heater.gas.50gal.power_vent": {
        "ferguson": {"sku": "RHEEM-PRO50-PV", "name": "Rheem Professional 50G Power Vent", "cost": 645.00},
        "moore_supply": {"sku": "MS-AO-50G-PV", "name": "AO Smith 50G Power Vent", "cost": 668.00},
        "apex": {"sku": "APX-BW-50G-PV", "name": "Bradford White 50G Power Vent", "cost": 679.00},
    },
    "water_heater.gas.40gal.standard": {
        "ferguson": {"sku": "RHEEM-PRO40-STD", "name": "Rheem Professional 40G Gas 9yr", "cost": 425.00},
        "moore_supply": {"sku": "MS-AO-40G-STD", "name": "AO Smith Signature 40G Gas", "cost": 438.00},
        "apex": {"sku": "APX-BRAW-40G", "name": "Bradford White 40G Gas", "cost": 445.00},
    },
    "water_heater.electric.50gal.standard": {
        "ferguson": {"sku": "RHEEM-EL50-STD", "name": "Rheem Performance 50G Electric", "cost": 365.00},
        "moore_supply": {"sku": "MS-AO-EL50-STD", "name": "AO Smith Voltex 50G Electric", "cost": 378.00},
        "apex": {"sku": "APX-BW-EL50", "name": "Bradford White 50G Electric", "cost": 355.00},
    },
    "water_heater.tankless.gas.standard": {
        "ferguson": {"sku": "NAVIIEN-NPE240S", "name": "Navien NPE-240S Condensing Tankless", "cost": 895.00},
        "moore_supply": {"sku": "MS-RINNAI-RU180", "name": "Rinnai RU180iN Indoor Tankless", "cost": 945.00},
        "apex": {"sku": "APX-RHEM-TK75", "name": "Rheem RTGH-95DVLN Tankless", "cost": 875.00},
    },

    # ── WH Accessories ────────────────────────────────────────────────────────
    "expansion_tank.2gal": {
        "ferguson": {"sku": "AMTROL-ST5", "name": "Amtrol ST-5 2G Expansion Tank", "cost": 28.50},
        "moore_supply": {"sku": "MS-WATTS-ET5", "name": "Watts PLT-5 2G Expansion Tank", "cost": 31.00},
        "apex": {"sku": "APX-THERM-ET2G", "name": "Thermal Expansion Tank 2G", "cost": 27.00},
    },
    "wh_flex_connector.18in": {
        "ferguson": {"sku": "FER-FLEX-18G", "name": "Gas Flex Connector 3/4\" x 18\"", "cost": 14.50},
        "moore_supply": {"sku": "MS-FLEX-18G", "name": "Gas Flex Connector 18\"", "cost": 15.00},
        "apex": {"sku": "APX-FLEX-18G", "name": "Gas Flex 18\"", "cost": 13.75},
    },
    "tp_valve.standard": {
        "ferguson": {"sku": "WATTS-100XL", "name": "Watts 100XL T&P Valve 3/4\"", "cost": 18.00},
        "moore_supply": {"sku": "MS-WATTS-TP", "name": "Watts T&P Relief Valve", "cost": 19.50},
        "apex": {"sku": "APX-TP-34", "name": "T&P Valve 3/4\"", "cost": 17.50},
    },
    "drain_pan.wh": {
        "ferguson": {"sku": "FER-DPAN-24", "name": "Water Heater Drain Pan 24\"", "cost": 22.00},
        "moore_supply": {"sku": "MS-DPAN-24", "name": "WH Drain Pan 24\"", "cost": 24.00},
        "apex": {"sku": "APX-DPAN-24", "name": "Drain Pan 24\"", "cost": 21.00},
    },

    # ── PRV ───────────────────────────────────────────────────────────────────
    "prv.3quarter": {
        "ferguson": {"sku": "WATTS-25AUB-3/4", "name": "Watts 25AUB 3/4\" PRV", "cost": 68.00},
        "moore_supply": {"sku": "MS-WATTS-PRV34", "name": "Watts 3/4\" Pressure Reducing Valve", "cost": 72.00},
        "apex": {"sku": "APX-CASH-PRV34", "name": "Cash Acme PRV 3/4\"", "cost": 65.00},
    },
    "prv.1inch": {
        "ferguson": {"sku": "WATTS-25AUB-1", "name": "Watts 25AUB 1\" PRV", "cost": 95.00},
        "moore_supply": {"sku": "MS-WATTS-PRV1", "name": "Watts 1\" Pressure Reducing Valve", "cost": 99.00},
        "apex": {"sku": "APX-CASH-PRV1", "name": "Cash Acme PRV 1\"", "cost": 89.00},
    },

    # ── Hose Bibs ─────────────────────────────────────────────────────────────
    "hose_bib.frost_free.8in": {
        "ferguson": {"sku": "WOODFORD-B14-8", "name": "Woodford B14 Frost Free 8\"", "cost": 24.00},
        "moore_supply": {"sku": "MS-WOOD-FF8", "name": "Woodford Frost Free Sillcock 8\"", "cost": 26.50},
        "apex": {"sku": "APX-AMSRD-FF8", "name": "American Standard Frost Free 8\"", "cost": 22.50},
    },
    "hose_bib.frost_free.12in": {
        "ferguson": {"sku": "WOODFORD-B14-12", "name": "Woodford B14 Frost Free 12\"", "cost": 27.00},
        "moore_supply": {"sku": "MS-WOOD-FF12", "name": "Woodford Frost Free 12\"", "cost": 29.00},
        "apex": {"sku": "APX-AMSRD-FF12", "name": "American Standard Frost Free 12\"", "cost": 25.50},
    },

    # ── Faucets ───────────────────────────────────────────────────────────────
    "faucet.kitchen.standard": {
        "ferguson": {"sku": "MOEN-7594BL", "name": "Moen Arbor 1-Handle Pull-Down", "cost": 185.00},
        "moore_supply": {"sku": "MS-DELTA-9159-DST", "name": "Delta Trinsic Single Handle", "cost": 195.00},
        "apex": {"sku": "APX-PRCE-SOAP-KIT", "name": "Price Pfister Stainless Kit", "cost": 175.00},
    },
    "faucet.lavatory.standard": {
        "ferguson": {"sku": "MOEN-6410BN", "name": "Moen Boardwalk 2-Handle Lav", "cost": 78.00},
        "moore_supply": {"sku": "MS-DELTA-3538-MPU", "name": "Delta Foundations 2-Handle Lav", "cost": 82.00},
        "apex": {"sku": "APX-PRCE-LAV-STD", "name": "Price Pfister 2-Handle Lav", "cost": 74.00},
    },
    "faucet.lavatory.single_handle": {
        "ferguson": {"sku": "MOEN-6100BN", "name": "Moen Adler Single Handle Lav", "cost": 68.00},
        "moore_supply": {"sku": "MS-DELTA-563-DST", "name": "Delta Foundations Single Handle Lav", "cost": 72.00},
        "apex": {"sku": "APX-PRCE-LAV-SH", "name": "Price Pfister Single Lav", "cost": 65.00},
    },

    # ── Shower Valves ─────────────────────────────────────────────────────────
    "shower_valve.pressure_balance": {
        "ferguson": {"sku": "MOEN-2510", "name": "Moen Posi-Temp Pressure Balance Valve", "cost": 68.00},
        "moore_supply": {"sku": "MS-DELTA-R10000-UNBX", "name": "Delta R10000 Universal Valve", "cost": 72.00},
        "apex": {"sku": "APX-KOHLER-K-304-K", "name": "Kohler Rite-Temp Pressure Balance", "cost": 75.00},
    },
    "shower_cartridge.moen": {
        "ferguson": {"sku": "MOEN-1225", "name": "Moen 1225 Cartridge", "cost": 24.00},
        "moore_supply": {"sku": "MS-MOEN-1225", "name": "Moen 1225 Replacement Cartridge", "cost": 26.00},
        "apex": {"sku": "APX-MOEN-1225", "name": "Moen Cartridge 1225", "cost": 22.50},
    },

    # ── Garbage Disposal ─────────────────────────────────────────────────────
    "garbage_disposal.0.5hp": {
        "ferguson": {"sku": "INSINKERATOR-BADGER5", "name": "InSinkErator Badger 5 1/2HP", "cost": 95.00},
        "moore_supply": {"sku": "MS-ISE-B5", "name": "InSinkErator Badger 5", "cost": 98.00},
        "apex": {"sku": "APX-WASTE-K50", "name": "WasteKing 1/2HP Disposal", "cost": 88.00},
    },
    "garbage_disposal.0.75hp": {
        "ferguson": {"sku": "INSINKERATOR-E100", "name": "InSinkErator Evolution 100 3/4HP", "cost": 142.00},
        "moore_supply": {"sku": "MS-ISE-E100", "name": "InSinkErator Evolution 100", "cost": 148.00},
        "apex": {"sku": "APX-WASTE-K75", "name": "WasteKing 3/4HP Disposal", "cost": 135.00},
    },
    "garbage_disposal.1hp": {
        "ferguson": {"sku": "INSINKERATOR-E200", "name": "InSinkErator Evolution 200 1HP", "cost": 185.00},
        "moore_supply": {"sku": "MS-ISE-E200", "name": "InSinkErator Evolution 200", "cost": 192.00},
        "apex": {"sku": "APX-WASTE-K100", "name": "WasteKing 1HP Disposal", "cost": 175.00},
    },

    # ── Angle Stops ───────────────────────────────────────────────────────────
    "angle_stop.standard.3_8": {
        "ferguson": {"sku": "FER-AS-38-STD", "name": "Angle Stop 3/8\" Comp x 1/2\" IPS", "cost": 8.50},
        "moore_supply": {"sku": "MS-AS-38-STD", "name": "Angle Stop 3/8\" Compression", "cost": 9.00},
        "apex": {"sku": "APX-AS-38-STD", "name": "Angle Stop Valve 3/8\"", "cost": 7.75},
    },
    "angle_stop.quarter_turn.3_8": {
        "ferguson": {"sku": "FER-AS-38-QT", "name": "Quarter Turn Angle Stop 3/8\"", "cost": 12.50},
        "moore_supply": {"sku": "MS-AS-38-QT", "name": "Ball Valve Angle Stop 3/8\"", "cost": 13.50},
        "apex": {"sku": "APX-AS-38-QT", "name": "Quarter Turn Stop 3/8\"", "cost": 11.75},
    },

    # ── Supply Lines ──────────────────────────────────────────────────────────
    "supply_line.12in": {
        "ferguson": {"sku": "FER-SL-12SS", "name": "Stainless Braided Supply Line 12\"", "cost": 6.50},
        "moore_supply": {"sku": "MS-SL-12SS", "name": "Stainless Supply Line 12\"", "cost": 7.00},
        "apex": {"sku": "APX-SL-12", "name": "Supply Line 12\"", "cost": 6.00},
    },
    "supply_line.16in": {
        "ferguson": {"sku": "FER-SL-16SS", "name": "Stainless Braided Supply Line 16\"", "cost": 7.25},
        "moore_supply": {"sku": "MS-SL-16SS", "name": "Stainless Supply Line 16\"", "cost": 7.75},
        "apex": {"sku": "APX-SL-16", "name": "Supply Line 16\"", "cost": 6.75},
    },
    "supply_line.20in": {
        "ferguson": {"sku": "FER-SL-20SS", "name": "Stainless Braided Supply Line 20\"", "cost": 8.00},
        "moore_supply": {"sku": "MS-SL-20SS", "name": "Stainless Supply Line 20\"", "cost": 8.50},
        "apex": {"sku": "APX-SL-20", "name": "Supply Line 20\"", "cost": 7.50},
    },

    # ── P-Traps ───────────────────────────────────────────────────────────────
    "ptrap.pvc.1_5in": {
        "ferguson": {"sku": "FER-PTRAP-PVC-15", "name": "PVC P-Trap 1-1/2\"", "cost": 5.50},
        "moore_supply": {"sku": "MS-PTRAP-PVC-15", "name": "PVC P-Trap 1-1/2\"", "cost": 5.75},
        "apex": {"sku": "APX-PTRAP-15", "name": "P-Trap PVC 1-1/2\"", "cost": 5.25},
    },
    "ptrap.abs.1_5in": {
        "ferguson": {"sku": "FER-PTRAP-ABS-15", "name": "ABS P-Trap 1-1/2\"", "cost": 5.25},
        "moore_supply": {"sku": "MS-PTRAP-ABS-15", "name": "ABS P-Trap 1-1/2\"", "cost": 5.50},
        "apex": {"sku": "APX-PTRAP-ABS-15", "name": "P-Trap ABS 1-1/2\"", "cost": 5.00},
    },

    # ── Misc Fittings ─────────────────────────────────────────────────────────
    "misc_fittings.toilet_replace": {
        "ferguson": {"sku": "FER-MISC-TOIL", "name": "Misc Fittings — Toilet Replace", "cost": 8.00},
        "moore_supply": {"sku": "MS-MISC-TOIL", "name": "Misc Fittings — Toilet", "cost": 8.00},
        "apex": {"sku": "APX-MISC-TOIL", "name": "Misc Fittings — Toilet", "cost": 8.00},
    },
    "misc_fittings.wh_replace": {
        "ferguson": {"sku": "FER-MISC-WH", "name": "Misc Fittings — Water Heater", "cost": 22.00},
        "moore_supply": {"sku": "MS-MISC-WH", "name": "Misc Fittings — WH", "cost": 22.00},
        "apex": {"sku": "APX-MISC-WH", "name": "Misc Fittings — WH", "cost": 22.00},
    },
}


# ─── Material Assemblies ──────────────────────────────────────────────────────

MATERIAL_ASSEMBLIES: dict[str, dict] = {

    "TOILET_INSTALL_KIT": {
        "name": "Toilet Install Kit — Standard Elongated",
        "labor_template": "TOILET_REPLACE_STANDARD",
        "items": {
            "toilet.elongated.standard": 1,
            "wax_ring.standard": 1,
            "closet_bolts.standard": 1,
            "supply_line.12in": 1,
            "misc_fittings.toilet_replace": 1,
        },
    },

    "TOILET_COMFORT_HEIGHT_KIT": {
        "name": "Toilet Install Kit — Comfort Height Elongated",
        "labor_template": "TOILET_REPLACE_STANDARD",
        "items": {
            "toilet.elongated.comfort_height": 1,
            "wax_ring.standard": 1,
            "closet_bolts.standard": 1,
            "supply_line.12in": 1,
            "misc_fittings.toilet_replace": 1,
        },
    },

    "WH_50G_GAS_KIT": {
        "name": "Water Heater 50G Gas — Standard Kit",
        "labor_template": "WH_50G_GAS_STANDARD",
        "items": {
            "water_heater.gas.50gal.standard": 1,
            "expansion_tank.2gal": 1,
            "wh_flex_connector.18in": 2,
            "tp_valve.standard": 1,
            "misc_fittings.wh_replace": 1,
        },
    },

    "WH_50G_GAS_ATTIC_KIT": {
        "name": "Water Heater 50G Gas — Attic Kit",
        "labor_template": "WH_50G_GAS_ATTIC",
        "items": {
            "water_heater.gas.50gal.standard": 1,
            "expansion_tank.2gal": 1,
            "wh_flex_connector.18in": 2,
            "tp_valve.standard": 1,
            "drain_pan.wh": 1,
            "misc_fittings.wh_replace": 1,
        },
    },

    "WH_40G_GAS_KIT": {
        "name": "Water Heater 40G Gas — Standard Kit",
        "labor_template": "WH_40G_GAS_STANDARD",
        "items": {
            "water_heater.gas.40gal.standard": 1,
            "expansion_tank.2gal": 1,
            "wh_flex_connector.18in": 2,
            "tp_valve.standard": 1,
            "misc_fittings.wh_replace": 1,
        },
    },

    "WH_50G_ELECTRIC_KIT": {
        "name": "Water Heater 50G Electric Kit",
        "labor_template": "WH_50G_ELECTRIC_STANDARD",
        "items": {
            "water_heater.electric.50gal.standard": 1,
            "expansion_tank.2gal": 1,
            "supply_line.16in": 2,
            "tp_valve.standard": 1,
            "misc_fittings.wh_replace": 1,
        },
    },

    "WH_TANKLESS_GAS_KIT": {
        "name": "Tankless Gas Water Heater Kit",
        "labor_template": "WH_TANKLESS_GAS",
        "items": {
            "water_heater.tankless.gas.standard": 1,
            "misc_fittings.wh_replace": 1,
        },
    },

    "PRV_KIT": {
        "name": "PRV Replace Kit — 3/4\"",
        "labor_template": "PRV_REPLACE",
        "items": {
            "prv.3quarter": 1,
            "supply_line.12in": 2,
        },
    },

    "HOSE_BIB_KIT": {
        "name": "Hose Bib Frost Free Replace Kit",
        "labor_template": "HOSE_BIB_REPLACE",
        "items": {
            "hose_bib.frost_free.8in": 1,
        },
    },

    "SHOWER_VALVE_KIT": {
        "name": "Shower Valve Replace Kit",
        "labor_template": "SHOWER_VALVE_REPLACE",
        "items": {
            "shower_valve.pressure_balance": 1,
        },
    },

    "KITCHEN_FAUCET_KIT": {
        "name": "Kitchen Faucet Replace Kit",
        "labor_template": "KITCHEN_FAUCET_REPLACE",
        "items": {
            "faucet.kitchen.standard": 1,
            "supply_line.16in": 2,
            "angle_stop.quarter_turn.3_8": 2,
        },
    },

    "LAV_FAUCET_KIT": {
        "name": "Lavatory Faucet Replace Kit",
        "labor_template": "LAV_FAUCET_REPLACE",
        "items": {
            "faucet.lavatory.standard": 1,
            "supply_line.12in": 2,
            "angle_stop.quarter_turn.3_8": 2,
        },
    },

    "DISPOSAL_KIT": {
        "name": "Garbage Disposal Install Kit — 1/2HP",
        "labor_template": "GARBAGE_DISPOSAL_INSTALL",
        "items": {
            "garbage_disposal.0.5hp": 1,
            "ptrap.pvc.1_5in": 1,
        },
    },

    "ANGLE_STOP_KIT": {
        "name": "Angle Stop Replace Kit",
        "labor_template": "ANGLE_STOP_REPLACE",
        "items": {
            "angle_stop.quarter_turn.3_8": 1,
            "supply_line.12in": 1,
        },
    },

    "PTRAP_KIT": {
        "name": "P-Trap Replace Kit",
        "labor_template": "PTRAP_REPLACE",
        "items": {
            "ptrap.pvc.1_5in": 1,
        },
    },

    "LAV_SINK_KIT": {
        "name": "Lavatory Sink Replace Kit",
        "labor_template": "LAV_SINK_REPLACE",
        "items": {
            "faucet.lavatory.standard": 1,
            "ptrap.pvc.1_5in": 1,
            "supply_line.12in": 2,
            "angle_stop.quarter_turn.3_8": 2,
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
