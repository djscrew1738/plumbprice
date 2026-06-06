"""Web Push notification service using VAPID (E6.5).

Sends browser push notifications to subscribed users via the Web Push standard.
VAPID keys must be set in environment: VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY.

Usage:
    from app.services.push_service import push_service

    await push_service.send(db, user_id=42, title="New Job", body="1234 Oak Lane assigned")
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.pricing_intelligence import PushSubscription

logger = structlog.get_logger()


class PushService:
    """Send Web Push notifications to subscribed users."""

    def _is_configured(self) -> bool:
        return bool(settings.vapid_public_key and settings.vapid_private_key)

    async def send(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        title: str,
        body: str,
        url: Optional[str] = None,
        icon: str = "/icons/icon-192.png",
    ) -> int:
        """Send a push notification to all active subscriptions for a user.

        Returns the number of subscriptions successfully notified.
        """
        if not self._is_configured():
            logger.debug("push_service.vapid_not_configured")
            return 0

        subscriptions = (
            await db.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id == user_id,
                    PushSubscription.is_active == True,  # noqa: E712
                )
            )
        ).scalars().all()

        if not subscriptions:
            return 0

        success_count = 0
        for sub in subscriptions:
            try:
                sent = await self._send_to_subscription(sub, title=title, body=body, url=url, icon=icon)
                if sent:
                    sub.last_push_at = datetime.now(timezone.utc)
                    success_count += 1
                else:
                    # Mark as inactive on permanent failure
                    sub.is_active = False
            except Exception as exc:
                logger.warning("push_service.send_failed", user_id=user_id, error=str(exc))

        await db.commit()
        return success_count

    async def send_to_many(
        self,
        db: AsyncSession,
        *,
        user_ids: list[int],
        title: str,
        body: str,
        url: Optional[str] = None,
    ) -> int:
        """Send a push notification to multiple users."""
        total = 0
        for uid in user_ids:
            total += await self.send(db, user_id=uid, title=title, body=body, url=url)
        return total

    async def _send_to_subscription(
        self,
        sub: PushSubscription,
        *,
        title: str,
        body: str,
        url: Optional[str],
        icon: str,
    ) -> bool:
        """Send a single push to one subscription endpoint."""
        try:
            from pywebpush import webpush
            import json

            payload = json.dumps({
                "title": title,
                "body": body,
                "icon": icon,
                "url": url or "/field",
            })

            sub_info = {
                "endpoint": sub.endpoint,
                "keys": sub.keys_json,
            }

            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{settings.vapid_subscriber_email}",
                },
            )
            return True

        except Exception as exc:
            error_str = str(exc)
            if "410" in error_str or "404" in error_str:
                # Subscription expired or deleted — deactivate
                return False
            logger.warning("push_service.webpush_error", error=error_str)
            return False


push_service = PushService()
