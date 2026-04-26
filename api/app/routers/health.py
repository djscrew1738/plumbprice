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
    """Check Celery worker health via async Redis ping."""
    redis_status = await _ping_redis()
    if redis_status == "ok":
        return {"status": "healthy", "celery_broker": "connected", "redis": "ok"}
    logger.error("worker_health_check_failed", redis=redis_status)
    return {"status": "unhealthy", "celery_broker": "disconnected", "redis": redis_status}


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
