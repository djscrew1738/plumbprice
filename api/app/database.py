from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.config import settings
import structlog
import time

logger = structlog.get_logger()

SLOW_QUERY_THRESHOLD_MS = 200

engine_kwargs = {
    "echo": settings.debug,
}

if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_pre_ping": True,    # discard stale connections before each use
            "pool_size": 10,          # base pool
            "max_overflow": 20,       # burst capacity
            "pool_timeout": 30,       # seconds to wait for a connection
            "pool_recycle": 1800,     # recycle connections every 30 min
            "connect_args": {
                "server_settings": {"application_name": "plumbprice-api"},
                "command_timeout": 30,
            },
        }
    )

engine = create_async_engine(settings.database_url, **engine_kwargs)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    elapsed_ms = (time.perf_counter() - conn.info["query_start_time"].pop()) * 1000
    if elapsed_ms >= SLOW_QUERY_THRESHOLD_MS:
        logger.warning("slow_query", elapsed_ms=round(elapsed_ms, 1), statement=statement[:200])

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


from app import models  # noqa: F401,E402


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
