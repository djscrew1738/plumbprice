from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.schemas.suppliers import (
    SupplierResponse, SupplierCompareRequest, SupplierCompareResponse,
    SupplierProductUpdate, BulkPriceUpload
)
from app.services.supplier_service import supplier_service, CANONICAL_MAP
from app.core.cache import cache_get, cache_set, cache_invalidate

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    """List all active suppliers."""
    cached = await cache_get("suppliers:list")
    if cached is not None:
        return [SupplierResponse(**s) for s in cached]

    result = await db.execute(select(Supplier).where(Supplier.is_active == True))
    suppliers = result.scalars().all()
    if not suppliers:
        # Return seed data if DB empty
        seed = [
            SupplierResponse(id=1, name="Ferguson Enterprises", slug="ferguson", type="wholesale",
                           website="https://www.ferguson.com", phone="972-555-0101",
                           city="Dallas", is_active=True),
            SupplierResponse(id=2, name="Moore Supply Co.", slug="moore_supply", type="wholesale",
                           website="https://www.mooresupply.com", phone="214-555-0102",
                           city="Dallas", is_active=True),
            SupplierResponse(id=3, name="Apex Supply", slug="apex", type="wholesale",
                           website="https://www.apexsupply.com", phone="817-555-0103",
                           city="Fort Worth", is_active=True),
        ]
        await cache_set("suppliers:list", [s.model_dump() for s in seed], ttl=300)
        return seed

    response = [
        SupplierResponse(
            id=s.id, name=s.name, slug=s.slug, type=s.type,
            website=s.website, phone=s.phone, city=s.city, is_active=s.is_active
        )
        for s in suppliers
    ]
    await cache_set("suppliers:list", [s.model_dump() for s in response], ttl=300)
    return response


@router.get("/compare")
async def compare_suppliers(
    items: list[str] = Query(alias="items[]"),
    county: str = Query(default="Dallas"),
    db: AsyncSession = Depends(get_db),
):
    """Compare supplier costs for a list of canonical items."""
    if not items:
        raise HTTPException(status_code=400, detail="At least one item required")

    result = await supplier_service.compare_suppliers(items, db=db)
    return result


@router.get("/catalog")
async def get_catalog(
    category: str = Query(None),
    search: str = Query(None),
):
    """Get canonical item catalog with all supplier prices."""
    items = {}
    for canonical_item, supplier_map in CANONICAL_MAP.items():
        if category and not canonical_item.startswith(category):
            continue
        if search and search.lower() not in canonical_item.lower():
            continue
        items[canonical_item] = supplier_map

    return {
        "count": len(items),
        "items": items,
    }


@router.put("/products/{product_id}")
async def update_product_price(
    product_id: int,
    update: SupplierProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Manually override a supplier product price."""
    result = await db.execute(select(SupplierProduct).where(SupplierProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_cost = product.cost
    product.cost = update.cost
    if update.notes:
        product.notes = update.notes

    # Log price history
    history = SupplierPriceHistory(product_id=product_id, cost=update.cost, source="manual_override")
    db.add(history)
    await db.commit()

    return {"id": product_id, "old_cost": old_cost, "new_cost": update.cost}


@router.post("/{supplier_id}/prices")
async def bulk_upload_prices(
    supplier_id: int,
    payload: BulkPriceUpload,
    db: AsyncSession = Depends(get_db),
):
    """Bulk upload prices for a supplier."""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Collect all canonical items from the payload
    items_by_canonical = {
        p["canonical_item"]: p
        for p in payload.products
        if p.get("canonical_item")
    }
    if not items_by_canonical:
        return {"supplier_id": supplier_id, "updated": 0, "created": 0}

    # Single batch query for all existing products — replaces N per-item queries
    existing_result = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.canonical_item.in_(items_by_canonical.keys()),
        )
    )
    existing_by_canonical = {
        p.canonical_item: p for p in existing_result.scalars().all()
    }

    updated = 0
    created = 0
    for canonical, p in items_by_canonical.items():
        if canonical in existing_by_canonical:
            product = existing_by_canonical[canonical]
            product.cost = p["cost"]
            if p.get("sku"):
                product.sku = p["sku"]
            updated += 1
        else:
            db.add(SupplierProduct(
                supplier_id=supplier_id,
                canonical_item=canonical,
                sku=p.get("sku"),
                name=p.get("name", canonical),
                cost=p["cost"],
            ))
            created += 1

    await db.commit()
    await cache_invalidate("suppliers:list")
    return {"supplier_id": supplier_id, "updated": updated, "created": created}
