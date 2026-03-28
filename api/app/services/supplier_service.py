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
# This map is now loaded from the database via the seed script.
# Keeping the structure for reference and potential fallback logic if needed.
CANONICAL_MAP: dict[str, dict[str, dict]] = {}


# ─── Material Assemblies ──────────────────────────────────────────────────────
# This map is now loaded from the database via the seed script.
MATERIAL_ASSEMBLIES: dict[str, dict] = {}


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
