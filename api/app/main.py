from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.database import init_db, AsyncSessionLocal as async_session_maker
from app.routers import chat, estimates, suppliers, blueprints, proposals, auth, admin, projects

logger = structlog.get_logger()


async def _sync_runtime_config():
    """Load markup rules and tax rates from DB into the in-memory dicts used by PricingEngine."""
    from sqlalchemy import select
    from app.models.labor import MarkupRule
    from app.models.tax import TaxRate
    from app.services.pricing_engine import MARKUP_RULES, TAX_RATES

    try:
        async with async_session_maker() as db:
            # Markup rules
            result = await db.execute(select(MarkupRule).where(MarkupRule.is_active == True))
            db_rules = result.scalars().all()
            for rule in db_rules:
                MARKUP_RULES[rule.job_type] = {
                    "labor_markup_pct":    rule.labor_markup_pct,
                    "materials_markup_pct": rule.materials_markup_pct,
                    "misc_flat":           rule.misc_flat,
                }

            # Tax rates
            result = await db.execute(select(TaxRate).where(TaxRate.is_active == True))
            db_rates = result.scalars().all()
            for rate in db_rates:
                TAX_RATES[rate.county.lower()] = rate.rate

            markup_count = len(db_rules)
            tax_count    = len(db_rates)
            logger.info("Runtime config synced from DB",
                        markup_rules=markup_count, tax_rates=tax_count)
    except Exception as e:
        logger.warning("Could not sync runtime config from DB, using defaults", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PlumbPrice AI API", version=settings.version, env=settings.environment)
    await init_db()
    await _sync_runtime_config()
    logger.info("Database ready")
    yield
    logger.info("Shutting down PlumbPrice AI API")


app = FastAPI(
    title="PlumbPrice AI API",
    description="Autonomous plumbing pricing and estimating platform for DFW contractors",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/v1/auth",       tags=["auth"])
app.include_router(chat.router,      prefix="/api/v1/chat",        tags=["chat"])
app.include_router(estimates.router, prefix="/api/v1/estimates",   tags=["estimates"])
app.include_router(projects.router,  prefix="/api/v1/projects",    tags=["projects"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers",   tags=["suppliers"])
app.include_router(blueprints.router,prefix="/api/v1/blueprints",  tags=["blueprints"])
app.include_router(proposals.router, prefix="/api/v1/proposals",   tags=["proposals"])
app.include_router(admin.router,     prefix="/api/v1/admin",       tags=["admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.version, "environment": settings.environment}


@app.get("/")
async def root():
    return {"message": "PlumbPrice AI API", "docs": "/docs"}
