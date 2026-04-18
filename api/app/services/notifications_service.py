"""Helpers for writing per-user notifications.

Callers use ``notify(...)`` for a best-effort insert — failures are logged but
never propagated, since notifications should never break the primary op.
"""
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification

logger = structlog.get_logger()


async def notify(
    db: AsyncSession,
    user_id: Optional[int],
    kind: str,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
) -> Optional[Notification]:
    """Insert a Notification row for ``user_id``. Best-effort; never raises.

    The caller is responsible for committing the surrounding transaction.
    """
    if user_id is None:
        return None
    try:
        n = Notification(
            user_id=user_id,
            kind=kind,
            title=title[:200],
            body=body,
            link=link[:500] if link else None,
        )
        db.add(n)
        await db.flush()
        return n
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(
            "notifications.notify_failed",
            user_id=user_id,
            kind=kind,
            error=str(e),
        )
        return None
