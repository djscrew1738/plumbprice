from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
import structlog

logger = structlog.get_logger()

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
