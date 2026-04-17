import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import structlog
import uuid

from app.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.environment,
        release=settings.version,
        send_default_pii=False,
    )
from app.database import init_db, AsyncSessionLocal
from app.routers import chat, estimates, suppliers, blueprints, proposals, auth, admin, projects, templates, health, documents
from app.core.exceptions import PricingError, SupplierError, BlueprintError, pricing_error_handler, supplier_error_handler, blueprint_error_handler
from app.core.auth import get_current_user
from app.models.users import User

logger = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address)


async def _ensure_seeded():
    """Seed DB with canonical data on first run if suppliers table is empty."""
    from sqlalchemy import select, func
    from app.models.suppliers import Supplier, SupplierProduct
    from app.models.labor import LaborTemplate, MaterialAssembly, MarkupRule
    from app.models.tax import TaxRate
    from app.services.supplier_service import CANONICAL_MAP, MATERIAL_ASSEMBLIES
    from app.services.labor_engine import LABOR_TEMPLATES
    from app.services.pricing_engine import _DEFAULT_MARKUP_RULES, _DEFAULT_TAX_RATES

    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count(Supplier.id)))).scalar()
        if count and count > 0:
            return  # already seeded

        logger.info("First run — seeding database")

        # Suppliers
        supplier_slugs = ["ferguson", "moore_supply", "apex"]
        supplier_meta = {
            "ferguson":    {"name": "Ferguson Enterprises", "city": "Dallas",     "phone": "972-555-0101"},
            "moore_supply":{"name": "Moore Supply Co.",     "city": "Dallas",     "phone": "214-555-0102"},
            "apex":        {"name": "Apex Supply",          "city": "Fort Worth", "phone": "817-555-0103"},
        }
        supplier_ids: dict[str, int] = {}
        for slug in supplier_slugs:
            meta = supplier_meta[slug]
            s = Supplier(slug=slug, type="wholesale", is_active=True, **meta)
            db.add(s)
            await db.flush()
            supplier_ids[slug] = s.id

        # Supplier products
        product_count = 0
        for canonical_item, supplier_prices in CANONICAL_MAP.items():
            for slug, data in supplier_prices.items():
                if slug not in supplier_ids:
                    continue
                db.add(SupplierProduct(
                    supplier_id=supplier_ids[slug],
                    canonical_item=canonical_item,
                    sku=data.get("sku"),
                    name=data["name"],
                    cost=data["cost"],
                    unit="ea",
                    is_active=True,
                    confidence_score=1.0,
                ))
                product_count += 1

        # Labor templates
        for code, tmpl in LABOR_TEMPLATES.items():
            db.add(LaborTemplate(
                code=code,
                name=tmpl.name,
                category=tmpl.category,
                base_hours=tmpl.base_hours,
                lead_rate=tmpl.lead_rate,
                helper_required=tmpl.helper_required,
                helper_rate=tmpl.helper_rate,
                helper_hours=tmpl.helper_hours,
                disposal_hours=tmpl.disposal_hours,
                is_active=True,
                config_json={
                    "access_multipliers": tmpl.access_multipliers,
                    "urgency_multipliers": tmpl.urgency_multipliers,
                    "applicable_assemblies": tmpl.applicable_assemblies,
                    "notes": tmpl.notes,
                },
            ))

        # Material assemblies
        for code, asm in MATERIAL_ASSEMBLIES.items():
            db.add(MaterialAssembly(
                code=code,
                name=asm["name"],
                labor_template_code=asm.get("labor_template"),
                canonical_items=list(asm["items"].keys()),
                item_quantities=asm["items"],
                is_active=True,
            ))

        # Markup rules
        for job_type, rules in _DEFAULT_MARKUP_RULES.items():
            db.add(MarkupRule(
                name=f"{job_type.capitalize()} Default",
                job_type=job_type,
                markup_type="percentage",
                labor_markup_pct=rules["labor_markup_pct"],
                materials_markup_pct=rules["materials_markup_pct"],
                misc_flat=rules["misc_flat"],
                is_active=True,
            ))

        # Tax rates
        for county, rate in _DEFAULT_TAX_RATES.items():
            db.add(TaxRate(county=county, rate=rate, is_active=True))

        await db.commit()
        logger.info("Database seeded",
                    suppliers=len(supplier_ids),
                    products=product_count,
                    templates=len(LABOR_TEMPLATES),
                    assemblies=len(MATERIAL_ASSEMBLIES))


async def _sync_runtime_config():
    """Load markup rules and tax rates from DB into in-memory dicts used by PricingEngine."""
    from sqlalchemy import select
    from app.models.labor import MarkupRule
    from app.models.tax import TaxRate
    from app.services.pricing_engine import MARKUP_RULES, TAX_RATES

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(MarkupRule).where(MarkupRule.is_active == True))
            for rule in result.scalars().all():
                MARKUP_RULES[rule.job_type] = {
                    "labor_markup_pct":    rule.labor_markup_pct,
                    "materials_markup_pct": rule.materials_markup_pct,
                    "misc_flat":           rule.misc_flat,
                }

            result = await db.execute(select(TaxRate).where(TaxRate.is_active == True))
            for rate in result.scalars().all():
                TAX_RATES[rate.county.lower()] = rate.rate

            logger.info("Runtime config synced",
                        markup_rules=len(MARKUP_RULES), tax_rates=len(TAX_RATES))
    except Exception as e:
        logger.warning("Runtime config sync failed — using defaults", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PlumbPrice AI API", version=settings.version, env=settings.environment)
    await init_db()
    await _ensure_seeded()
    await _sync_runtime_config()
    logger.info("Database ready")

    # Probe Hermes / Ollama availability — non-blocking, just logs the result
    from app.services.llm_service import llm_service
    llm_ok = await llm_service.check_available()
    if llm_ok:
        logger.info(
            "Hermes LLM ready",
            endpoint=settings.hermes_endpoint_url,
            model=settings.hermes_model,
        )
    else:
        logger.warning(
            "Hermes LLM not available — keyword-only classification active",
            endpoint=settings.hermes_endpoint_url,
        )

    # Warm the price enrichment cache, then schedule periodic auto-refresh
    import asyncio as _asyncio
    from app.services.data_sources.price_enrichment import get_enrichment_service

    enrichment_svc = get_enrichment_service()
    _asyncio.ensure_future(enrichment_svc.refresh())
    logger.info("Price enrichment cache warming started in background")

    async def _periodic_enrichment_refresh():
        """Re-warm price cache every price_cache_ttl_hours so prices stay current."""
        interval = settings.price_cache_ttl_hours * 3600
        while True:
            await _asyncio.sleep(interval)
            logger.info("Scheduled price enrichment refresh starting",
                        interval_hours=settings.price_cache_ttl_hours)
            try:
                await enrichment_svc.refresh()
                logger.info("Scheduled price enrichment refresh complete",
                            stats=enrichment_svc.cache_stats())
            except Exception as exc:
                logger.warning("Scheduled price enrichment refresh failed", error=str(exc))

    refresh_task = _asyncio.ensure_future(_periodic_enrichment_refresh())

    yield

    refresh_task.cancel()
    logger.info("Shutting down PlumbPrice AI API")


app = FastAPI(
    title="PlumbPrice AI API",
    description="Autonomous plumbing pricing and estimating platform for DFW contractors",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Compress responses larger than 500 bytes — saves significant bandwidth on estimate payloads
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Inject X-Request-ID header for cross-log tracing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

app.add_exception_handler(PricingError, pricing_error_handler)
app.add_exception_handler(SupplierError, supplier_error_handler)
app.add_exception_handler(BlueprintError, blueprint_error_handler)

app.include_router(auth.router,      prefix="/api/v1/auth",       tags=["auth"])
app.include_router(chat.router,      prefix="/api/v1/chat",        tags=["chat"])
app.include_router(estimates.router, prefix="/api/v1/estimates",   tags=["estimates"])
app.include_router(projects.router,  prefix="/api/v1/projects",    tags=["projects"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers",   tags=["suppliers"])
app.include_router(blueprints.router,prefix="/api/v1/blueprints",  tags=["blueprints"])
app.include_router(proposals.router, prefix="/api/v1/proposals",   tags=["proposals"])
app.include_router(documents.router, prefix="/api/v1/documents",   tags=["documents"])
app.include_router(admin.router,     prefix="/api/v1/admin",       tags=["admin"])
app.include_router(templates.router,  prefix="/api/v1/templates", tags=["templates"])
app.include_router(health.router,    tags=["health"])


@app.get("/health")
async def health_check():
    import time as _time
    from sqlalchemy import text
    from app.services.llm_service import llm_service
    from app.services.data_sources.price_enrichment import get_enrichment_service

    checks: dict = {}
    overall = "ok"

    # Database check
    try:
        t0 = _time.monotonic()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "latency_ms": round((_time.monotonic() - t0) * 1000, 1)}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)[:200]}
        overall = "degraded"

    # LLM check
    llm_ok = llm_service._available
    checks["llm"] = {
        "provider": "hermes3/ollama",
        "endpoint": settings.hermes_endpoint_url,
        "model": settings.hermes_model,
        "available": llm_ok,
    }
    if not llm_ok:
        overall = "degraded"

    # Price cache check
    cache_stats = get_enrichment_service().cache_stats()
    checks["price_cache"] = cache_stats

    return {
        "status": overall,
        "version": settings.version,
        "environment": settings.environment,
        **checks,
    }


@app.get("/api/v1/prices/cache", tags=["admin"])
async def price_cache_stats(current_user: User = Depends(get_current_user)):
    """Return current state of the price enrichment cache. Requires authentication."""
    from app.services.data_sources.price_enrichment import get_enrichment_service
    return get_enrichment_service().cache_stats()


@app.post("/api/v1/prices/refresh", tags=["admin"])
async def price_cache_refresh(current_user: User = Depends(get_current_user)):
    """Trigger an immediate background refresh of the price enrichment cache. Admin only."""
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    import asyncio as _asyncio
    from app.services.data_sources.price_enrichment import get_enrichment_service
    _asyncio.ensure_future(get_enrichment_service().refresh())
    return {"status": "refresh_started"}


@app.get("/")
async def root():
    return {"message": "PlumbPrice AI API", "docs": "/docs"}
