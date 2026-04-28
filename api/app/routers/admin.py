from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func as sa_func
import structlog
import hashlib
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import get_db
from app.models.labor import LaborTemplate, MarkupRule
from app.models.suppliers import Supplier, SupplierProduct, SupplierPriceHistory
from app.models.blueprints import BlueprintJob
from app.models.documents import UploadedDocument
from app.models.users import User, Organization, UserInvite
from app.services.labor_engine import LABOR_TEMPLATES, list_template_codes, get_template
from app.core.auth import get_current_user, get_current_admin
from app.core.cache import cache_get, cache_set, cache_invalidate
from app.core.celery_inspect import get_task_state

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

    from app.services.pricing_defaults import MARKUP_RULES
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
    _=Depends(get_current_admin),
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
    from app.services.pricing_defaults import MARKUP_RULES
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


# ─── Worker task observability + manual retry ──────────────────────────────

_RETRY_LOCK_TTL_SECONDS = 60


def _retry_lock_key(kind: str, item_id: int) -> str:
    return f"retry_lock:{kind}:{item_id}"


async def _acquire_retry_lock(lock_key: str) -> bool:
    """Atomic SET NX EX via Redis. Returns True if we acquired the lock.

    Falls back to True (allow retry) if Redis is unreachable so local/dev
    environments without Redis don't block manual retries.
    """
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.celery_broker_url, socket_connect_timeout=1, socket_timeout=1
        )
        try:
            acquired = await client.set(
                lock_key, "1", nx=True, ex=_RETRY_LOCK_TTL_SECONDS
            )
            return bool(acquired)
        finally:
            await client.aclose()
    except Exception as exc:
        logger.warning("admin.retry_lock_unavailable", key=lock_key, error=str(exc))
        return True


@router.get("/tasks/{task_id}")
async def get_admin_task_state(
    task_id: str,
    current_user=Depends(get_current_admin),
):
    """Return Celery task state for a given task id."""
    return get_task_state(task_id)


@router.get("/tasks")
async def list_admin_failed_tasks(
    status: str = Query("failed", description="Only 'failed' is supported today"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List failed blueprint jobs and document uploads."""
    if status != "failed":
        raise HTTPException(status_code=400, detail="Only status=failed is supported")

    bp_result = await db.execute(
        select(BlueprintJob)
        .where(BlueprintJob.status == "error")
        .order_by(desc(BlueprintJob.updated_at), desc(BlueprintJob.id))
        .limit(limit)
    )
    blueprint_jobs = bp_result.scalars().all()

    doc_result = await db.execute(
        select(UploadedDocument)
        .where(UploadedDocument.status == "error")
        .order_by(desc(UploadedDocument.updated_at), desc(UploadedDocument.id))
        .limit(limit)
    )
    document_uploads = doc_result.scalars().all()

    items = []
    for bp in blueprint_jobs:
        items.append({
            "type": "blueprint",
            "id": bp.id,
            "original_filename": bp.original_filename or bp.filename,
            "error": bp.processing_error,
            "updated_at": bp.updated_at.isoformat() if bp.updated_at else None,
            "task_id": None,
        })
    for doc in document_uploads:
        items.append({
            "type": "document",
            "id": doc.id,
            "original_filename": doc.original_filename or doc.filename,
            "error": doc.processing_error,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            "task_id": None,
        })

    items.sort(key=lambda x: x["updated_at"] or "", reverse=True)
    return {"count": len(items), "items": items[:limit]}


@router.post("/blueprints/{job_id}/retry")
async def retry_blueprint_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Reset a failed BlueprintJob and re-enqueue the analysis task."""
    result = await db.execute(select(BlueprintJob).where(BlueprintJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Blueprint job not found")
    if job.status != "error":
        raise HTTPException(
            status_code=409,
            detail=f"Blueprint job is not in error state (status={job.status})",
        )

    lock_key = _retry_lock_key("bp", job_id)
    acquired = await _acquire_retry_lock(lock_key)
    if not acquired:
        raise HTTPException(status_code=409, detail="Retry already in progress")

    job_id_local = job.id
    storage_path_local = job.storage_path
    job.status = "pending"
    job.processing_error = None
    await db.commit()

    from worker.tasks.blueprint_analysis import analyze_blueprint

    async_result = analyze_blueprint.delay(job_id_local, storage_path_local)
    task_id = getattr(async_result, "id", None)
    logger.info("admin.blueprint_retry", job_id=job_id_local, task_id=task_id)
    return {"task_id": task_id, "job_id": job_id_local, "status": "pending"}


@router.post("/documents/{document_id}/retry")
async def retry_document_upload(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Reset a failed UploadedDocument and re-enqueue the processing task."""
    result = await db.execute(
        select(UploadedDocument).where(UploadedDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "error":
        raise HTTPException(
            status_code=409,
            detail=f"Document is not in error state (status={doc.status})",
        )

    lock_key = _retry_lock_key("doc", document_id)
    acquired = await _acquire_retry_lock(lock_key)
    if not acquired:
        raise HTTPException(status_code=409, detail="Retry already in progress")

    doc_id_local = doc.id
    storage_path_local = doc.storage_path
    doc_type_local = doc.doc_type
    doc.status = "pending"
    doc.processing_error = None
    await db.commit()

    from worker.tasks.document_processing import process_document

    async_result = process_document.delay(doc_id_local, storage_path_local, doc_type_local)
    task_id = getattr(async_result, "id", None)
    logger.info("admin.document_retry", document_id=doc_id_local, task_id=task_id)
    return {"task_id": task_id, "document_id": doc_id_local, "status": "pending"}


# ─── User invite + management ─────────────────────────────────────────────────

_ALLOWED_ROLES = {"admin", "estimator", "viewer"}
_INVITE_TTL_DAYS = 7


class InviteRequest(BaseModel):
    email: str
    role: str = "estimator"
    full_name: Optional[str] = None


class PatchUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


async def _count_org_admins(db: AsyncSession, organization_id: Optional[int]) -> int:
    result = await db.execute(
        select(sa_func.count(User.id)).where(
            User.organization_id == organization_id,
            User.is_admin == True,
            User.is_active == True,
        )
    )
    return result.scalar_one() or 0


@router.post("/users/invite")
async def invite_user(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if body.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {sorted(_ALLOWED_ROLES)}")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    invite = UserInvite(
        id=uuid.uuid4(),
        email=body.email,
        role=body.role,
        full_name=body.full_name,
        token_hash=token_hash,
        invited_by=current_user.id,
        organization_id=current_user.organization_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.commit()

    try:
        from app.services.email_service import send_invite_email
        frontend_base = getattr(settings, "frontend_url", None) or "https://app.ctlplumbingllc.com"
        invite_url = f"{frontend_base.rstrip('/')}/accept-invite?token={raw_token}"
        await send_invite_email(body.email, invite_url, body.full_name)
    except Exception as exc:
        logger.warning("invite.email_failed", error=str(exc))

    logger.info("invite.created", email=body.email, invited_by=current_user.id)
    return {"message": "Invite sent", "email": body.email}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    body: PatchUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Cannot change own role
    if body.role is not None and target.id == current_user.id:
        raise HTTPException(status_code=409, detail="Cannot change your own role")

    # Cannot demote/deactivate the last admin in an org
    is_demoting = body.role is not None and body.role != "admin" and target.is_admin
    is_deactivating = body.is_active is False and target.is_active and target.is_admin
    if is_demoting or is_deactivating:
        admin_count = await _count_org_admins(db, target.organization_id)
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="Cannot demote or deactivate the last admin")

    if body.role is not None:
        if body.role not in _ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        target.role = body.role
        target.is_admin = body.role == "admin"
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.full_name is not None:
        target.full_name = body.full_name

    await db.commit()
    await db.refresh(target)
    return {
        "id": target.id,
        "email": target.email,
        "full_name": target.full_name,
        "role": target.role,
        "is_active": target.is_active,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_user.id:
        raise HTTPException(status_code=409, detail="Cannot deactivate your own account")

    if target.is_admin:
        admin_count = await _count_org_admins(db, target.organization_id)
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="Cannot deactivate the last admin")

    target.is_active = False
    await db.commit()
    return {"message": "User deactivated"}


@router.get("/invites")
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserInvite).where(
            UserInvite.organization_id == current_user.organization_id,
            UserInvite.accepted_at == None,
            UserInvite.expires_at > now,
        )
    )
    invites = result.scalars().all()
    return [
        {
            "id": str(inv.id),
            "email": inv.email,
            "role": inv.role,
            "full_name": inv.full_name,
            "expires_at": inv.expires_at.isoformat(),
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invites
    ]


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(UserInvite).where(UserInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Mark as consumed so it can't be accepted
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Invite revoked"}


# ─── Organization settings ────────────────────────────────────────────────────

class OrgPatchRequest(BaseModel):
    name: Optional[str] = None
    billing_email: Optional[str] = None
    logo_url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    default_tax_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    default_markup_percent: Optional[float] = Field(None, ge=0.0, le=10.0)


async def _get_or_create_org(db: AsyncSession, current_user: User) -> Organization:
    if current_user.organization_id:
        result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org = result.scalar_one_or_none()
        if org:
            return org

    # If user has no org, create one on the fly
    org = Organization(name=current_user.full_name or current_user.email)
    db.add(org)
    await db.flush()
    # Attach user
    result2 = await db.execute(select(User).where(User.id == current_user.id))
    u = result2.scalar_one_or_none()
    if u:
        u.organization_id = org.id
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/organizations/me")
async def get_my_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await _get_or_create_org(db, current_user)
    return {
        "id": org.id,
        "name": org.name,
        "phone": org.phone,
        "email": org.email,
        "address": org.address,
        "city": org.city,
        "state": org.state,
        "zip_code": org.zip_code,
        "billing_email": org.billing_email,
        "logo_url": org.logo_url,
        "default_tax_rate": org.default_tax_rate,
        "default_markup_percent": org.default_markup_percent,
    }


@router.patch("/organizations/me")
async def patch_my_organization(
    body: OrgPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    org = await _get_or_create_org(db, current_user)

    if body.name is not None:
        org.name = body.name
    if body.billing_email is not None:
        org.billing_email = body.billing_email
    if body.logo_url is not None:
        org.logo_url = body.logo_url
    if body.phone is not None:
        org.phone = body.phone
    if body.address is not None:
        org.address = body.address
    if body.default_tax_rate is not None:
        org.default_tax_rate = body.default_tax_rate
    if body.default_markup_percent is not None:
        org.default_markup_percent = body.default_markup_percent

    await db.commit()
    await db.refresh(org)
    return {
        "id": org.id,
        "name": org.name,
        "phone": org.phone,
        "email": org.email,
        "address": org.address,
        "city": org.city,
        "state": org.state,
        "zip_code": org.zip_code,
        "billing_email": org.billing_email,
        "logo_url": org.logo_url,
        "default_tax_rate": org.default_tax_rate,
        "default_markup_percent": org.default_markup_percent,
    }


@router.post("/organizations/me/logo")
async def upload_org_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    allowed_content_types = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=415, detail="Only image files are accepted")

    data = await file.read()
    ext = (file.filename or "logo.png").rsplit(".", 1)[-1].lower()
    object_name = f"org-logos/{current_user.organization_id or 'unknown'}/{uuid.uuid4()}.{ext}"

    from app.core.storage import storage_client
    try:
        storage_client.upload_file(
            bucket_name=settings.minio_bucket_documents,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=file.content_type,
        )
    except Exception as exc:
        logger.warning("admin.logo_upload_failed", error=str(exc))

    logo_url = f"/media/{object_name}"

    org = await _get_or_create_org(db, current_user)
    org.logo_url = logo_url
    await db.commit()

    return {"logo_url": logo_url}


# ─── Phase 3.5 — Vision-item to task-code mapping admin ────────────────────────

from app.models.vision_mappings import VisionItemMapping
from app.services.photo_quote import _ITEM_TO_TASK


class VisionMappingPayload(BaseModel):
    item_type: str = Field(..., min_length=1, max_length=80)
    default_task_code: str = Field(..., min_length=1, max_length=120)
    problem_task_code: Optional[str] = Field(default=None, max_length=120)
    enabled: bool = True
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("item_type")
    @classmethod
    def _normalize_type(cls, v: str) -> str:
        return v.strip().lower()


@router.get("/vision-mappings")
async def list_vision_mappings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """List vision-item mappings — both DB overrides and the static defaults."""
    rows = (await db.execute(select(VisionItemMapping).order_by(VisionItemMapping.item_type))).scalars().all()
    db_keys = {r.item_type for r in rows}

    overrides = [
        {
            "id": r.id,
            "item_type": r.item_type,
            "default_task_code": r.default_task_code,
            "problem_task_code": r.problem_task_code,
            "enabled": r.enabled,
            "note": r.note,
            "source": "db",
        }
        for r in rows
    ]
    static_only = [
        {
            "id": None,
            "item_type": k,
            "default_task_code": v[0],
            "problem_task_code": v[1],
            "enabled": True,
            "note": None,
            "source": "static",
        }
        for k, v in sorted(_ITEM_TO_TASK.items())
        if k not in db_keys
    ]
    valid_codes = {c.upper() for c in list_template_codes()}
    return {
        "mappings": overrides + static_only,
        "valid_task_codes": sorted(valid_codes),
    }


@router.post("/vision-mappings", status_code=201)
async def upsert_vision_mapping(
    body: VisionMappingPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create or update a mapping override (keyed on item_type)."""
    valid = {c.upper() for c in list_template_codes()}
    if body.default_task_code.upper() not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown task_code: {body.default_task_code}")
    if body.problem_task_code and body.problem_task_code.upper() not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown task_code: {body.problem_task_code}")

    existing = (
        await db.execute(select(VisionItemMapping).where(VisionItemMapping.item_type == body.item_type))
    ).scalar_one_or_none()
    if existing:
        existing.default_task_code = body.default_task_code
        existing.problem_task_code = body.problem_task_code
        existing.enabled = body.enabled
        existing.note = body.note
        existing.updated_by = current_user.id
        row = existing
    else:
        row = VisionItemMapping(
            item_type=body.item_type,
            default_task_code=body.default_task_code,
            problem_task_code=body.problem_task_code,
            enabled=body.enabled,
            note=body.note,
            organization_id=current_user.organization_id,
            updated_by=current_user.id,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("admin.vision_mapping_upsert", item_type=row.item_type, by=current_user.id)
    return {
        "id": row.id,
        "item_type": row.item_type,
        "default_task_code": row.default_task_code,
        "problem_task_code": row.problem_task_code,
        "enabled": row.enabled,
        "note": row.note,
    }


@router.delete("/vision-mappings/{item_type}", status_code=204)
async def delete_vision_mapping(
    item_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Remove an override (the static fallback then takes effect again)."""
    key = item_type.strip().lower()
    row = (
        await db.execute(select(VisionItemMapping).where(VisionItemMapping.item_type == key))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await db.delete(row)
    await db.commit()
    logger.info("admin.vision_mapping_delete", item_type=key, by=current_user.id)
    return None
