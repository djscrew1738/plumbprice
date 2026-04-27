"""Health check endpoints for monitoring."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import settings
from app.database import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])


async def _ping_redis() -> str:
    """Non-blocking Redis ping using the async redis-py client."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        return "ok"
    except Exception as exc:
        logger.warning("health.check_failed", check="redis", error=str(exc))
        return f"error: {exc}"


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "plumbprice-api",
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies database is accessible."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        logger.warning("health.check_failed", check="database", error=str(e))
        return {"status": "not_ready", "database": "error", "error": str(e)}


@router.get("/live")
async def liveness_check():
    """Liveness check - simple health status."""
    return {"status": "alive"}


@router.get("/worker")
async def worker_health():
    """Check Celery worker health: broker reachable + at least one worker
    responsive via `celery inspect`. Reports active task counts per worker
    so monitoring can alert if no worker is consuming the queue."""
    redis_status = await _ping_redis()
    if redis_status != "ok":
        logger.error("worker_health_check_failed", redis=redis_status)
        return {"status": "unhealthy", "celery_broker": "disconnected",
                "redis": redis_status, "workers": []}

    # Probe Celery for live workers. The inspect call is synchronous + can
    # block on broker round-trips, so we time-bound it via run_in_executor.
    import asyncio as _aio
    workers: dict | None = None
    inspect_error: str | None = None

    def _probe() -> dict:
        try:
            from worker.worker import app as celery_app
            insp = celery_app.control.inspect(timeout=2.0)
            return {
                "ping": insp.ping() or {},
                "active": insp.active() or {},
                "stats": insp.stats() or {},
            }
        except Exception as e:  # pragma: no cover
            raise RuntimeError(str(e))

    try:
        loop = _aio.get_event_loop()
        workers = await _aio.wait_for(loop.run_in_executor(None, _probe), timeout=3.0)
    except _aio.TimeoutError:
        inspect_error = "celery inspect timed out"
    except Exception as e:
        inspect_error = str(e)

    if not workers or not workers.get("ping"):
        # Broker is up but nobody's listening — the most common silent failure mode.
        return {
            "status": "degraded",
            "celery_broker": "connected",
            "redis": "ok",
            "workers": [],
            "worker_count": 0,
            "error": inspect_error or "no workers responded to ping",
        }

    summary = []
    for name, _ in (workers["ping"] or {}).items():
        summary.append({
            "name": name,
            "active_tasks": len((workers.get("active") or {}).get(name) or []),
            "concurrency": ((workers.get("stats") or {}).get(name) or {})
                .get("pool", {}).get("max-concurrency"),
        })

    return {
        "status": "healthy",
        "celery_broker": "connected",
        "redis": "ok",
        "workers": summary,
        "worker_count": len(summary),
    }


@router.get("/llm")
async def llm_health():
    """LLM tier + cloud fallback cost snapshot."""
    from app.services.llm_service import llm_service
    return llm_service.get_status()


@router.get("/dependencies")
async def dependencies_check(db: AsyncSession = Depends(get_db)):
    """Check all external dependencies."""
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("health.check_failed", check="database", error=str(e))
        db_status = f"error: {e}"

    return {
        "database": db_status,
        "redis": await _ping_redis(),
        "version": "1.0.0",
    }


# ── External provider health probes (e1/e2/e3/e4/e5) ────────────────────────

@router.get("/esign")
async def esign_health():
    from app.services.external.esign import get_esign_provider
    return (await get_esign_provider().health()).as_dict()


@router.get("/comms")
async def comms_health():
    from app.services.external.comms import get_comms_provider
    return (await get_comms_provider().health()).as_dict()


@router.get("/billing")
async def billing_health():
    from app.services.external.billing import get_billing_provider
    return (await get_billing_provider().health()).as_dict()


@router.get("/calendar")
async def calendar_health():
    from app.services.external.calendar import get_calendar_provider
    return (await get_calendar_provider().health()).as_dict()


@router.get("/permits")
async def permits_health():
    from app.services.external.permits import get_permits_provider
    return (await get_permits_provider().health()).as_dict()
