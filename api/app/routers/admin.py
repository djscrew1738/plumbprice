from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.labor import LaborTemplate, MarkupRule
from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.services.labor_engine import LABOR_TEMPLATES, list_template_codes, get_template
from app.core.auth import get_current_user, get_current_admin
from app.core.cache import cache_get, cache_set, cache_invalidate

logger = structlog.get_logger()
router = APIRouter()


@router.get("/labor-templates")
async def list_labor_templates(db: AsyncSession = Depends(get_db)):
    """List all labor templates (in-memory + DB overrides)."""
    cached = await cache_get("admin:labor-templates")
    if cached is not None:
        return cached

    templates = []
    for code, tmpl in LABOR_TEMPLATES.items():
        templates.append({
            "code": code,
            "name": tmpl.name,
            "category": tmpl.category,
            "base_hours": tmpl.base_hours,
            "lead_rate": tmpl.lead_rate,
            "helper_required": tmpl.helper_required,
            "helper_rate": tmpl.helper_rate,
            "disposal_hours": tmpl.disposal_hours,
            "notes": tmpl.notes,
            "applicable_assemblies": tmpl.applicable_assemblies,
            "access_multipliers": tmpl.access_multipliers,
            "urgency_multipliers": tmpl.urgency_multipliers,
        })
    response = {"count": len(templates), "templates": templates}
    await cache_set("admin:labor-templates", response, ttl=600)
    return response


@router.get("/labor-templates/{code}")
async def get_labor_template(code: str):
    """Get a specific labor template."""
    tmpl = get_template(code)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' not found")
    return {
        "code": tmpl.code,
        "name": tmpl.name,
        "category": tmpl.category,
        "base_hours": tmpl.base_hours,
        "lead_rate": tmpl.lead_rate,
        "helper_required": tmpl.helper_required,
        "helper_rate": tmpl.helper_rate,
        "helper_hours": tmpl.helper_hours,
        "disposal_hours": tmpl.disposal_hours,
        "access_multipliers": tmpl.access_multipliers,
        "urgency_multipliers": tmpl.urgency_multipliers,
        "notes": tmpl.notes,
        "applicable_assemblies": tmpl.applicable_assemblies,
    }


@router.get("/markup-rules")
async def get_markup_rules(db: AsyncSession = Depends(get_db)):
    """Get markup rules."""
    cached = await cache_get("admin:markup-rules")
    if cached is not None:
        return cached

    from app.services.pricing_engine import MARKUP_RULES
    result = await db.execute(select(MarkupRule).where(MarkupRule.is_active == True))
    db_rules = result.scalars().all()

    if db_rules:
        response = [
            {
                "id": r.id,
                "name": r.name,
                "job_type": r.job_type,
                "materials_markup_pct": r.materials_markup_pct,
                "labor_markup_pct": r.labor_markup_pct,
                "misc_flat": r.misc_flat,
            }
            for r in db_rules
        ]
    else:
        response = [
            {"id": None, "name": f"{jt.capitalize()} Default", "job_type": jt, **rules}
            for jt, rules in MARKUP_RULES.items()
        ]

    await cache_set("admin:markup-rules", response, ttl=300)
    return response


class MarkupRuleUpdate(BaseModel):
    materials_markup_pct: float
    misc_flat: float = 45.0


@router.put("/markup-rules/{job_type}")
async def update_markup_rules(
    job_type: str,
    body: MarkupRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update markup rules for a job type."""
    if job_type not in ("service", "construction", "commercial"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    materials_markup_pct = body.materials_markup_pct
    misc_flat = body.misc_flat

    result = await db.execute(
        select(MarkupRule).where(MarkupRule.job_type == job_type, MarkupRule.is_active == True)
    )
    rule = result.scalar_one_or_none()

    if rule:
        rule.materials_markup_pct = materials_markup_pct
        rule.misc_flat = misc_flat
    else:
        rule = MarkupRule(
            name=f"{job_type.capitalize()} Default",
            job_type=job_type,
            materials_markup_pct=materials_markup_pct,
            misc_flat=misc_flat,
        )
        db.add(rule)

    await db.commit()

    # Invalidate markup-rules cache so next GET reflects the change
    await cache_invalidate("admin:markup-rules")

    # Immediately reflect change in the in-memory pricing dict
    from app.services.pricing_engine import MARKUP_RULES
    MARKUP_RULES[job_type] = {
        "labor_markup_pct":     getattr(rule, "labor_markup_pct", 0.0),
        "materials_markup_pct": materials_markup_pct,
        "misc_flat":            misc_flat,
    }

    return {"job_type": job_type, "materials_markup_pct": materials_markup_pct, "misc_flat": misc_flat}


@router.get("/assemblies")
async def list_assemblies():
    """List all material assemblies."""
    from app.services.supplier_service import MATERIAL_ASSEMBLIES
    return {
        "count": len(MATERIAL_ASSEMBLIES),
        "assemblies": {
            code: {
                "name": asm["name"],
                "labor_template": asm.get("labor_template"),
                "items": asm["items"],
            }
            for code, asm in MATERIAL_ASSEMBLIES.items()
        },
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get system stats."""
    from sqlalchemy import func
    from app.models.estimates import Estimate

    total_estimates = await db.execute(select(func.count(Estimate.id)))
    total_count = total_estimates.scalar()

    avg_total = await db.execute(select(func.avg(Estimate.grand_total)))
    avg_value = avg_total.scalar()

    from app.services.supplier_service import CANONICAL_MAP
    return {
        "total_estimates":       total_count or 0,
        "avg_estimate_value":    round(avg_value or 0, 2),
        "labor_templates_count": len(LABOR_TEMPLATES),
        "canonical_items_count": len(CANONICAL_MAP),
    }


@router.post('/import-templates')
async def import_pricing_templates(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_admin)):
    """Import pricing templates from web/templates/pricing into the database as PricingTemplate rows.
    Requires admin user.
    """
    from app.services.external_templates import list_pricing_templates, get_pricing_template
    from app.models.pricing_template import PricingTemplate

    templates = list_pricing_templates()
    processed = 0
    for t in templates:
        full = get_pricing_template(t.get('id'))
        if not full:
            continue
        # Upsert by template_id
        result = await db.execute(select(PricingTemplate).where(PricingTemplate.template_id == full.get('id')))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = full.get('name')
            existing.description = full.get('description')
            existing.sku = full.get('sku')
            existing.base_price = full.get('base_price')
            existing.parts_cost = full.get('parts_cost')
            existing.labor_cost = full.get('labor_cost')
            existing.tax_rate = full.get('tax_rate')
            existing.region = full.get('region')
            existing.tags = full.get('tags')
            existing.source_file = full.get('_source_file')
        else:
            pt = PricingTemplate(
                template_id=full.get('id'),
                name=full.get('name') or full.get('id'),
                description=full.get('description'),
                sku=full.get('sku'),
                base_price=full.get('base_price'),
                parts_cost=full.get('parts_cost'),
                labor_cost=full.get('labor_cost'),
                tax_rate=full.get('tax_rate'),
                region=full.get('region'),
                tags=full.get('tags'),
                source_file=full.get('_source_file'),
            )
            db.add(pt)
        processed += 1

    await db.commit()
    return {"imported": processed}


# ─── Canonical Item CRUD ──────────────────────────────────────────────────────

class SupplierPriceInput(BaseModel):
    sku: Optional[str] = None
    name: str
    cost: float
    unit: str = "ea"


@router.get("/canonical-items")
async def list_canonical_items(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List all distinct canonical items with their per-supplier prices from DB."""
    result = await db.execute(
        select(SupplierProduct, Supplier.slug)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(SupplierProduct.is_active == True)
        .order_by(SupplierProduct.canonical_item, Supplier.slug)
    )
    rows = result.all()

    items: dict[str, dict] = {}
    for product, slug in rows:
        ci = product.canonical_item
        if ci not in items:
            items[ci] = {"canonical_item": ci, "suppliers": {}}
        items[ci]["suppliers"][slug] = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "cost": product.cost,
            "unit": product.unit,
            "confidence_score": product.confidence_score,
            "last_verified": product.last_verified,
        }

    return {"count": len(items), "items": list(items.values())}


@router.get("/canonical-items/{canonical_item:path}")
async def get_canonical_item(
    canonical_item: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Get all supplier prices for a single canonical item."""
    result = await db.execute(
        select(SupplierProduct, Supplier.slug)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(
            SupplierProduct.canonical_item == canonical_item,
            SupplierProduct.is_active == True,
        )
    )
    rows = result.all()
    if not rows:
        # Fall back to CANONICAL_MAP for items not yet in DB
        from app.services.supplier_service import CANONICAL_MAP
        if canonical_item not in CANONICAL_MAP:
            raise HTTPException(status_code=404, detail=f"Canonical item '{canonical_item}' not found")
        return {
            "canonical_item": canonical_item,
            "source": "in_memory",
            "suppliers": CANONICAL_MAP[canonical_item],
        }

    suppliers = {}
    for product, slug in rows:
        suppliers[slug] = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "cost": product.cost,
            "unit": product.unit,
            "confidence_score": product.confidence_score,
            "last_verified": product.last_verified,
        }
    return {"canonical_item": canonical_item, "source": "database", "suppliers": suppliers}


@router.put("/canonical-items/{canonical_item:path}/{supplier_slug}")
async def upsert_canonical_item_price(
    canonical_item: str,
    supplier_slug: str,
    body: SupplierPriceInput,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Create or update the price for a specific (canonical_item, supplier) pair.
    Records a price history entry when cost changes.
    """
    # Resolve supplier
    sup_result = await db.execute(select(Supplier).where(Supplier.slug == supplier_slug))
    supplier = sup_result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_slug}' not found")

    # Get existing product
    prod_result = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.canonical_item == canonical_item,
        )
    )
    product = prod_result.scalar_one_or_none()

    if product:
        old_cost = product.cost
        product.sku = body.sku or product.sku
        product.name = body.name
        product.cost = round(body.cost, 2)
        product.unit = body.unit
        if abs(old_cost - body.cost) > 0.001:
            db.add(SupplierPriceHistory(product_id=product.id, cost=body.cost, source="admin"))
        action = "updated"
    else:
        product = SupplierProduct(
            supplier_id=supplier.id,
            canonical_item=canonical_item,
            sku=body.sku,
            name=body.name,
            cost=round(body.cost, 2),
            unit=body.unit,
            confidence_score=1.0,
            is_active=True,
        )
        db.add(product)
        await db.flush()
        db.add(SupplierPriceHistory(product_id=product.id, cost=body.cost, source="admin"))
        action = "created"

    await db.commit()
    await db.refresh(product)

    logger.info(
        "canonical_item.price_updated",
        canonical_item=canonical_item,
        supplier=supplier_slug,
        action=action,
        cost=body.cost,
        admin_id=current_user.id,
    )
    return {
        "action": action,
        "canonical_item": canonical_item,
        "supplier": supplier_slug,
        "id": product.id,
        "cost": product.cost,
        "sku": product.sku,
    }


@router.delete("/canonical-items/{canonical_item:path}/{supplier_slug}")
async def deactivate_canonical_item_price(
    canonical_item: str,
    supplier_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Soft-delete (deactivate) a supplier price for a canonical item."""
    sup_result = await db.execute(select(Supplier).where(Supplier.slug == supplier_slug))
    supplier = sup_result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_slug}' not found")

    prod_result = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.canonical_item == canonical_item,
            SupplierProduct.is_active == True,
        )
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Price not found")

    product.is_active = False
    await db.commit()
    logger.info("canonical_item.deactivated", canonical_item=canonical_item, supplier=supplier_slug)
    return {"deactivated": True, "canonical_item": canonical_item, "supplier": supplier_slug}
