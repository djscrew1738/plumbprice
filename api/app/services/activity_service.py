"""Helpers to log project activity events.

Failures must never break the primary operation — callers rely on this service
being best-effort. All exceptions are swallowed and logged.
"""
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.projects import ProjectActivity

logger = structlog.get_logger()


async def log(
    db: AsyncSession,
    project_id: Optional[int],
    actor_user_id: Optional[int],
    kind: str,
    payload: Optional[dict] = None,
) -> None:
    """Append a project_activities row. Best-effort; never raises."""
    if project_id is None:
        return
    try:
        db.add(
            ProjectActivity(
                project_id=project_id,
                actor_user_id=actor_user_id,
                kind=kind,
                payload=payload or {},
            )
        )
        await db.flush()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(
            "activity.log_failed",
            project_id=project_id,
            kind=kind,
            error=str(e),
        )
