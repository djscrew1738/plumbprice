from fastapi import APIRouter, Depends, status, UploadFile, File, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.core.auth import get_current_admin
from app.core.cache import cache_get, cache_set, cache_invalidate
from app.models.pricing_rules import PermitCostRule, CityZoneMultiplier, TripChargeRule
from app.models.tax import TaxRate
from app.models.suppliers import SupplierProduct, Supplier
from app.schemas import pricing_rules as schemas
from app.schemas import tax as tax_schemas
from app.services.pricing_config_service import pricing_config_service
from app.services.catalog_importer import (
    import_supplier_products,
    import_labor_templates,
    generate_product_csv_template,
    generate_labor_csv_template,
)
from app.services.price_feed_adapter import registry
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_pricing_cache(_=Depends(get_current_admin)):
    """Manually refresh the in-memory pricing cache from DB."""
    await pricing_config_service.refresh_cache()
    return {"status": "success", "message": "Pricing cache refreshed"}


# --- Tax Rates ---
@router.get("/tax-rates", response_model=list[tax_schemas.TaxRate])
async def list_tax_rates(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:tax-rates")
    if cached is not None:
        return cached
    result = await db.execute(select(TaxRate).order_by(TaxRate.county))
    rows = result.scalars().all()
    data = [tax_schemas.TaxRate.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:tax-rates", data, ttl=600)
    return rows


@router.post("/tax-rates", response_model=tax_schemas.TaxRate)
async def create_tax_rate(body: tax_schemas.TaxRateCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TaxRate(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:tax-rates")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/tax-rates/{tax_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tax_rate(tax_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TaxRate).where(TaxRate.id == tax_id))
    await db.commit()
    await cache_invalidate("admin:tax-rates")
    await pricing_config_service.refresh_cache()
    return None


# --- Permit Costs ---
@router.get("/permit-costs", response_model=list[schemas.PermitCostRule])
async def list_permit_costs(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:permit-costs")
    if cached is not None:
        return cached
    result = await db.execute(select(PermitCostRule).order_by(PermitCostRule.county, PermitCostRule.job_category))
    rows = result.scalars().all()
    data = [schemas.PermitCostRule.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:permit-costs", data, ttl=600)
    return rows


@router.post("/permit-costs", response_model=schemas.PermitCostRule)
async def create_permit_cost(body: schemas.PermitCostRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = PermitCostRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:permit-costs")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/permit-costs/{permit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permit_cost(permit_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(PermitCostRule).where(PermitCostRule.id == permit_id))
    await db.commit()
    await cache_invalidate("admin:permit-costs")
    await pricing_config_service.refresh_cache()
    return None


# --- City Multipliers ---
@router.get("/city-multipliers", response_model=list[schemas.CityZoneMultiplier])
async def list_city_multipliers(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:city-multipliers")
    if cached is not None:
        return cached
    result = await db.execute(select(CityZoneMultiplier).order_by(CityZoneMultiplier.city))
    rows = result.scalars().all()
    data = [schemas.CityZoneMultiplier.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:city-multipliers", data, ttl=600)
    return rows


@router.post("/city-multipliers", response_model=schemas.CityZoneMultiplier)
async def create_city_multiplier(body: schemas.CityZoneMultiplierCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = CityZoneMultiplier(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:city-multipliers")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/city-multipliers/{multiplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city_multiplier(multiplier_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(CityZoneMultiplier).where(CityZoneMultiplier.id == multiplier_id))
    await db.commit()
    await cache_invalidate("admin:city-multipliers")
    await pricing_config_service.refresh_cache()
    return None


# --- Trip Charges ---
@router.get("/trip-charges", response_model=list[schemas.TripChargeRule])
async def list_trip_charges(db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    cached = await cache_get("admin:trip-charges")
    if cached is not None:
        return cached
    result = await db.execute(select(TripChargeRule).order_by(TripChargeRule.county))
    rows = result.scalars().all()
    data = [schemas.TripChargeRule.model_validate(r).model_dump() for r in rows]
    await cache_set("admin:trip-charges", data, ttl=600)
    return rows


@router.post("/trip-charges", response_model=schemas.TripChargeRule)
async def create_trip_charge(body: schemas.TripChargeRuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    db_obj = TripChargeRule(**body.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await cache_invalidate("admin:trip-charges")
    await pricing_config_service.refresh_cache()
    return db_obj


@router.delete("/trip-charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip_charge(charge_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_admin)):
    await db.execute(delete(TripChargeRule).where(TripChargeRule.id == charge_id))
    await db.commit()
    await cache_invalidate("admin:trip-charges")
    await pricing_config_service.refresh_cache()
    return None


# ─── Bulk Import ─────────────────────────────────────────────────────────────

class BulkImportResponse(BaseModel):
    dry_run: bool
    total_rows: int
    created: int
    updated: int
    skipped: int
    errors: int
    rows: list[dict]


@router.post("/bulk-import/products", response_model=BulkImportResponse)
async def bulk_import_products(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Preview changes without writing to DB"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Bulk import supplier products from a CSV file.

    Required columns: canonical_item, supplier_slug, name, cost
    Optional columns: sku, unit, manufacturer, category, sub_category, tags, in_stock, lead_time, msrp, list_price
    """
    content = await file.read()
    result = await import_supplier_products(db, content, dry_run=dry_run)
    if not dry_run:
        await pricing_config_service.refresh_cache()
    return result.to_dict()


@router.post("/bulk-import/labor", response_model=BulkImportResponse)
async def bulk_import_labor(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="Preview changes without writing to DB"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Bulk import labor templates from a CSV file.

    Required columns: code, name, category, base_hours
    Optional columns: lead_rate, helper_required, helper_rate, helper_hours, disposal_hours, tags, difficulty_rating, required_certifications, min_hours, max_hours
    """
    content = await file.read()
    result = await import_labor_templates(db, content, dry_run=dry_run)
    if not dry_run:
        await pricing_config_service.refresh_cache()
    return result.to_dict()


@router.get("/bulk-import/products/template")
async def download_product_template(_=Depends(get_current_admin)):
    """Download a CSV template for supplier product imports."""
    csv_data = generate_product_csv_template()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_import_template.csv"},
    )


@router.get("/bulk-import/labor/template")
async def download_labor_template(_=Depends(get_current_admin)):
    """Download a CSV template for labor template imports."""
    csv_data = generate_labor_csv_template()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labor_import_template.csv"},
    )


# ─── Feed Health ─────────────────────────────────────────────────────────────

@router.get("/feeds/health")
async def get_feed_health(_=Depends(get_current_admin)):
    """Return health status for all registered price feed adapters."""
    health_map = await registry.health_all()
    return {
        "feeds": [
            {
                "name": h.name,
                "status": h.status,
                "last_sync": h.last_sync.isoformat() if h.last_sync else None,
                "items_synced": h.items_synced,
                "error_count": h.error_count,
                "error_message": h.error_message,
                "response_time_ms": h.response_time_ms,
            }
            for h in health_map.values()
        ]
    }


# ─── Catalog Browser ─────────────────────────────────────────────────────────

@router.get("/catalog")
async def list_catalog(
    search: str | None = None,
    category: str | None = None,
    supplier: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Searchable catalog of all supplier products with filters."""
    from sqlalchemy import select, func, or_

    stmt = (
        select(
            SupplierProduct,
            Supplier.slug.label("supplier_slug"),
            Supplier.name.label("supplier_name"),
        )
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(SupplierProduct.is_active == True)
    )

    if search:
        stmt = stmt.where(
            or_(
                SupplierProduct.canonical_item.ilike(f"%{search}%"),
                SupplierProduct.name.ilike(f"%{search}%"),
                SupplierProduct.sku.ilike(f"%{search}%"),
                SupplierProduct.manufacturer.ilike(f"%{search}%"),
            )
        )

    if category:
        stmt = stmt.where(SupplierProduct.category == category)

    if supplier:
        stmt = stmt.where(Supplier.slug == supplier)

    stmt = stmt.order_by(SupplierProduct.canonical_item, Supplier.slug)
    stmt = stmt.limit(500)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for product, slug, _ in rows:
        items.append({
            "id": product.id,
            "canonical_item": product.canonical_item,
            "name": product.name,
            "sku": product.sku,
            "supplier": slug,
            "cost": product.cost,
            "msrp": product.msrp,
            "manufacturer": product.manufacturer,
            "category": product.category,
            "sub_category": product.sub_category,
            "in_stock": product.in_stock,
            "lead_time": product.lead_time,
            "tags": product.tags,
            "confidence_score": product.confidence_score,
            "last_verified": product.last_verified.isoformat() if product.last_verified else None,
        })

    return {"count": len(items), "items": items}
