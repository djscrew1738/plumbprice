"""Celery task inspection helpers.

Exposes helpers for reading task state via Celery's result backend so admin
endpoints can surface observability data without requiring worker access.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


def _get_celery_app():
    """Import the Celery app lazily so API imports don't require Celery worker deps."""
    from worker import celery_app

    return celery_app


def get_task_state(task_id: str) -> dict[str, Any]:
    """Return a serializable snapshot of Celery task state.

    Fields:
        task_id: the requested id (echoed back)
        state:   Celery state string (PENDING, STARTED, SUCCESS, FAILURE, RETRY, ...)
        retries: number of retries (0 when unknown)
        result_summary: short string representation of the task result (None if absent)
        traceback_excerpt: last ~20 lines of the traceback on FAILURE (None otherwise)

    When no result backend is configured (or the id is unknown) Celery returns
    PENDING with an empty result; we handle that gracefully.
    """
    try:
        app = _get_celery_app()
        result = app.AsyncResult(task_id)
        state = result.state or "PENDING"

        retries = 0
        try:
            info = result.info  # may raise if result payload is the exception itself
            if isinstance(info, dict):
                retries = int(info.get("retries", 0) or 0)
        except Exception:
            info = None

        result_summary: str | None = None
        traceback_excerpt: str | None = None

        if state == "FAILURE":
            tb = getattr(result, "traceback", None)
            if tb:
                lines = str(tb).splitlines()
                traceback_excerpt = "\n".join(lines[-20:])
            if info is not None:
                result_summary = repr(info)[:500]
        elif state == "SUCCESS":
            try:
                payload = result.result
                result_summary = repr(payload)[:500] if payload is not None else None
            except Exception as exc:
                result_summary = f"<unreadable result: {exc}>"

        return {
            "task_id": task_id,
            "state": state,
            "retries": retries,
            "result_summary": result_summary,
            "traceback_excerpt": traceback_excerpt,
        }
    except Exception as exc:
        logger.warning("celery_inspect.get_task_state_failed", task_id=task_id, error=str(exc))
        return {
            "task_id": task_id,
            "state": "UNKNOWN",
            "retries": 0,
            "result_summary": None,
            "traceback_excerpt": f"inspection error: {exc}",
        }
