"""v4.1 Push Notification API — subscribe/unsubscribe and send (E6.5).

POST /api/v3/notifications/push/subscribe
DELETE /api/v3/notifications/push/subscribe
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from app.database import get_db
from app.core.auth import get_current_user
from app.models.users import User
from app.models.pricing_intelligence import PushSubscription
from app.config import settings

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict[str, Any]
    user_agent: str | None = None


class PushSubscribeResponse(BaseModel):
    status: str
    vapid_public_key: str | None


@router.post("/push/subscribe", response_model=PushSubscribeResponse)
async def subscribe_push(
    body: PushSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store a Web Push subscription for the current user."""
    # Upsert: if the endpoint already exists, reactivate it
    existing = (
        await db.execute(
            select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
        )
    ).scalar_one_or_none()

    if existing:
        existing.user_id = current_user.id
        existing.keys_json = body.keys
        existing.user_agent = body.user_agent
        existing.is_active = True
    else:
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=body.endpoint,
            keys_json=body.keys,
            user_agent=body.user_agent,
        )
        db.add(sub)

    await db.commit()
    return PushSubscribeResponse(
        status="subscribed",
        vapid_public_key=settings.vapid_public_key,
    )


@router.delete("/push/subscribe")
async def unsubscribe_push(
    endpoint: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a Web Push subscription."""
    sub = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint,
                PushSubscription.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if sub:
        sub.is_active = False
        await db.commit()

    return {"status": "unsubscribed"}


@router.get("/push/vapid-key")
async def get_vapid_public_key():
    """Return the VAPID public key for service worker registration."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": settings.vapid_public_key}
