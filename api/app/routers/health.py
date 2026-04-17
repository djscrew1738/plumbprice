"""Health check endpoints for monitoring."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from app.database import get_db
import redis
import os

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])


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
        # Test database connection
        await db.execute("SELECT 1")
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return {"status": "not_ready", "database": "error", "error": str(e)}


@router.get("/live")
async def liveness_check():
    """Liveness check - simple health status."""
    return {"status": "alive"}


@router.get("/worker")
async def worker_health():
    """Check Celery worker health."""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()

        return {
            "status": "healthy",
            "celery_broker": "connected",
            "redis": "ok",
        }
    except Exception as e:
        logger.error("worker_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "celery_broker": "disconnected",
            "error": str(e),
        }


@router.get("/dependencies")
async def dependencies_check(db: AsyncSession = Depends(get_db)):
    """Check all external dependencies."""
    checks = {
        "database": "ok",
        "redis": "unknown",
        "version": "1.0.0",
    }

    try:
        await db.execute("SELECT 1")
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    return checks
