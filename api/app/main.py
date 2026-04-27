import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog
import uuid

from app.config import settings
from app.core.limiter import limiter

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
from app.routers import chat, estimates, suppliers, blueprints, proposals, auth, admin, projects, templates, health, documents, sessions, outcomes, public, notifications, analytics, memories, photos, voice, public_agent, feature_flags, addon_suggestions, jobcost, doc_generation, public_agent_audit, price_drift
from app.core.exceptions import PricingError, SupplierError, BlueprintError, pricing_error_handler, supplier_error_handler, blueprint_error_handler
from app.core.auth import get_current_user
from app.models.users import User

logger = structlog.get_logger()


# Dev-default secrets that must never be used in production. Fail fast if we
# detect any of these when ENVIRONMENT == "production".
_INSECURE_SECRET_DEFAULTS = {
    "",
    "change-me",
    "changeme",
    "secret",
    "dev-secret",
    "development",
    "plumbprice-dev",
}


def _validate_env() -> None:
    """Validate required config at startup.

    In production: fail fast if secrets are missing or use dev defaults, and
    warn loudly for optional-but-important keys (Resend, Sentry).
    In development: just log informational warnings.
    """
    is_prod = settings.environment.lower() in ("production", "prod")
    errors: list[str] = []
    warnings: list[str] = []

    secret_value = (settings.secret_key or "").strip().lower()
    if not settings.secret_key:
        errors.append("SECRET_KEY is not set")
    elif is_prod and (secret_value in _INSECURE_SECRET_DEFAULTS or len(settings.secret_key) < 32):
        errors.append("SECRET_KEY appears to be a default/dev value; must be a strong random string in production")

    if not settings.database_url:
        errors.append("DATABASE_URL is not set")
    elif is_prod and "localhost" in settings.database_url:
        warnings.append("DATABASE_URL points at localhost in a production environment")

    if is_prod:
        if not settings.resend_api_key:
            warnings.append("RESEND_API_KEY not set — proposal emails will not be delivered")
        if not settings.sentry_dsn:
            warnings.append("SENTRY_DSN not set — error telemetry disabled")
        if settings.debug:
            warnings.append("DEBUG is enabled in production")

    for msg in warnings:
        logger.warning("env.validation_warning", message=msg)

    if errors:
        for msg in errors:
            logger.error("env.validation_error", message=msg)
        if is_prod:
            raise RuntimeError(
                "Startup aborted due to environment misconfiguration: "
                + "; ".join(errors)
            )
        logger.warning(
            "env.validation_errors_ignored_in_dev",
            count=len(errors),
            note="would abort startup in production",
        )


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
    _validate_env()
    from app.core.storage import storage_client
    try:
        storage_client.ensure_buckets()
        logger.info("MinIO buckets ready")
    except Exception as exc:
        logger.warning("MinIO bucket init failed — storage unavailable", error=str(exc))
    await init_db()
    await _ensure_seeded()
    await _sync_runtime_config()
    logger.info("Database ready")

    # Probe Hermes / Ollama availability — non-blocking, just logs the result
    from app.services.llm_service import llm_service
    import asyncio as _asyncio
    try:
        llm_ok = await _asyncio.wait_for(llm_service.check_available(), timeout=5.0)
    except _asyncio.TimeoutError:
        llm_ok = False
        logger.warning("Hermes LLM probe timed out — keyword-only classification active")
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
    description=(
        "Autonomous plumbing pricing and estimating platform for DFW contractors. "
        "Built by Cory Nichols / CTL Plumbing."
    ),
    version=settings.version,
    contact={"name": "Cory Nichols / CTL Plumbing"},
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Optional observability — Sentry + OTel are no-ops without DSN/endpoint.
from app.observability import init_sentry, init_otel
init_sentry()
init_otel(app)

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
async def logging_middleware(request: Request, call_next):
    """Inject X-Request-ID and emit a structured access log for every request."""
    import time as _time
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    # Best-effort decode of the auth token to enrich logs with user/org
    # context. Failures here are silent — auth is enforced by route deps.
    user_id: int | None = None
    org_id: int | None = None
    auth_header = request.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        try:
            from app.core.auth import decode_token
            payload = decode_token(auth_header[7:])
            sub = payload.get("sub")
            if sub is not None:
                try:
                    user_id = int(sub)
                except (TypeError, ValueError):
                    user_id = None
            org_raw = payload.get("org_id") or payload.get("organization_id")
            if org_raw is not None:
                try:
                    org_id = int(org_raw)
                except (TypeError, ValueError):
                    org_id = None
        except Exception:
            pass

    t0 = _time.monotonic()
    response = await call_next(request)
    latency_ms = round((_time.monotonic() - t0) * 1000, 1)

    response.headers["X-Request-ID"] = request_id

    # Skip noisy health-check probes from the access log
    path = request.url.path
    if path not in ("/health", "/health/live", "/health/ready"):
        log = logger.bind(
            request_id=request_id,
            method=request.method,
            path=path,
            status=response.status_code,
            latency_ms=latency_ms,
            client=request.client.host if request.client else None,
            user_id=user_id,
            org_id=org_id,
        )
        if response.status_code >= 500:
            log.error("request_error")
        elif response.status_code >= 400:
            log.warning("request_warning")
        else:
            log.info("request")

    return response

app.add_exception_handler(PricingError, pricing_error_handler)
app.add_exception_handler(SupplierError, supplier_error_handler)
app.add_exception_handler(BlueprintError, blueprint_error_handler)

app.include_router(auth.router,      prefix="/api/v1/auth",       tags=["auth"])
app.include_router(chat.router,      prefix="/api/v1/chat",        tags=["chat"])
app.include_router(outcomes.router,  prefix="/api/v1/estimates",   tags=["outcomes"])
app.include_router(estimates.router, prefix="/api/v1/estimates",   tags=["estimates"])
app.include_router(projects.router,  prefix="/api/v1/projects",    tags=["projects"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers",   tags=["suppliers"])
app.include_router(blueprints.router,prefix="/api/v1/blueprints",  tags=["blueprints"])
app.include_router(proposals.router, prefix="/api/v1/proposals",   tags=["proposals"])
app.include_router(documents.router, prefix="/api/v1/documents",   tags=["documents"])
app.include_router(sessions.router,  prefix="/api/v1/sessions",    tags=["sessions"])
app.include_router(admin.router,     prefix="/api/v1/admin",       tags=["admin"])
app.include_router(templates.router,  prefix="/api/v1/templates", tags=["templates"])
app.include_router(public.router,    prefix="/api/v1/public",     tags=["public"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(analytics.router,     prefix="/api/v1/analytics",     tags=["analytics"])
app.include_router(memories.router,      prefix="/api/v1/memories",      tags=["memories"])
app.include_router(photos.router,        prefix="/api/v1/photos",        tags=["photos"])
app.include_router(voice.router,         prefix="/api/v1/voice",         tags=["voice"])
app.include_router(public_agent.router,  prefix="/api/v1/public-agent",  tags=["public-agent"])
app.include_router(public_agent_audit.router, prefix="/api/v1/admin/public-agent", tags=["admin"])
app.include_router(feature_flags.router, prefix="/api/v1",               tags=["feature-flags"])
app.include_router(addon_suggestions.router, prefix="/api/v1/estimates", tags=["estimates"])
app.include_router(jobcost.router,           prefix="/api/v1/estimates", tags=["jobcost"])
app.include_router(doc_generation.router,    prefix="/api/v1/estimates", tags=["docs"])
app.include_router(price_drift.router,       prefix="/api/v1/admin/supplier-prices", tags=["admin"])
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
    if llm_ok is None:
        llm_ok = await llm_service.check_available()
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
