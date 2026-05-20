"""
Suppliers API v3 — Webhook endpoints and supplier health monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import structlog

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.suppliers import Supplier
from app.models.supplier_webhooks import SupplierWebhook
from app.schemas.v3.suppliers import WebhookEvent, SupplierWebhookCreate, SupplierWebhookResponse
from app.services.data_sources.price_enrichment import get_enrichment_service

logger = structlog.get_logger()
router = APIRouter()


def _verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/{supplier_slug}")
async def receive_webhook(
    supplier_slug: str,
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Receive and process a supplier webhook event.

    Validates HMAC signature, updates pricing, and invalidates enrichment cache.
    """
    # Find supplier
    stmt = select(Supplier).where(Supplier.slug == supplier_slug)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Find active webhook config
    stmt = select(SupplierWebhook).where(
        SupplierWebhook.supplier_id == supplier.id,
        SupplierWebhook.is_active == True,
    )
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="No active webhook config for this supplier")

    # Verify signature
    payload = await request.body()
    if not _verify_webhook(payload, x_signature, webhook.secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse event
    try:
        event = WebhookEvent.model_validate_json(payload)
    except Exception as exc:
        logger.warning("webhook.parse_failed", supplier=supplier_slug, error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Process event
    if event.type == "price_change" and event.new_cost is not None:
        from app.models.suppliers import SupplierProduct
        from app.models.suppliers import SupplierPriceHistory

        # Find product by SKU
        stmt = select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.sku == event.sku,
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if product:
            old_cost = product.cost
            product.cost = event.new_cost
            product.last_verified = datetime.now(timezone.utc)

            # Record history
            db.add(SupplierPriceHistory(
                product_id=product.id,
                cost=event.new_cost,
                source=f"webhook:{supplier_slug}",
            ))

            # Invalidate enrichment cache
            enrichment = get_enrichment_service()
            enrichment.invalidate(product.canonical_item)

            logger.info(
                "webhook.price_change_processed",
                supplier=supplier_slug,
                sku=event.sku,
                canonical_item=product.canonical_item,
                old_cost=old_cost,
                new_cost=event.new_cost,
            )
        else:
            logger.warning("webhook.product_not_found", supplier=supplier_slug, sku=event.sku)

    elif event.type == "stock_update":
        from app.models.suppliers import SupplierProduct
        stmt = select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.sku == event.sku,
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product and event.in_stock is not None:
            product.is_active = event.in_stock
            logger.info("webhook.stock_updated", supplier=supplier_slug, sku=event.sku, in_stock=event.in_stock)

    # Update delivery tracking
    webhook.last_delivered_at = datetime.now(timezone.utc)
    webhook.failure_count = 0
    await db.commit()

    return {"status": "ok"}


@router.get("/{supplier_id}/webhooks", response_model=list[SupplierWebhookResponse])
async def list_webhooks(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List webhook configurations for a supplier. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt = select(SupplierWebhook).where(SupplierWebhook.supplier_id == supplier_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{supplier_id}/webhooks", response_model=SupplierWebhookResponse)
async def create_webhook(
    supplier_id: int,
    req: SupplierWebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a webhook configuration for a supplier. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    import secrets
    webhook = SupplierWebhook(
        supplier_id=supplier_id,
        event_type=req.event_type,
        secret=secrets.token_urlsafe(32),
        endpoint_url=req.endpoint_url,
        is_active=req.is_active,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.get("/health")
async def supplier_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get supplier health summary — last refresh, webhook status, product counts."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from sqlalchemy import func
    from app.models.suppliers import SupplierProduct

    stmt = select(Supplier)
    result = await db.execute(stmt)
    suppliers = result.scalars().all()

    health = []
    for s in suppliers:
        product_count = (
            await db.execute(
                select(func.count(SupplierProduct.id)).where(SupplierProduct.supplier_id == s.id)
            )
        ).scalar() or 0

        webhook_stmt = select(SupplierWebhook).where(
            SupplierWebhook.supplier_id == s.id,
            SupplierWebhook.is_active == True,
        )
        webhook_result = await db.execute(webhook_stmt)
        webhooks = webhook_result.scalars().all()

        health.append({
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "is_active": s.is_active,
            "product_count": product_count,
            "active_webhooks": len(webhooks),
            "webhook_last_delivery": max([w.last_delivered_at for w in webhooks if w.last_delivered_at], default=None),
        })

    return {"suppliers": health}


from datetime import datetime, timezone
