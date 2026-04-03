from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.routers import chat, estimates, suppliers, blueprints, proposals, auth, admin, projects
from app.core.exceptions import PricingError, SupplierError, BlueprintError, pricing_error_handler, supplier_error_handler, blueprint_error_handler

logger = structlog.get_logger()


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
app.include_router(admin.router,     prefix="/api/v1/admin",       tags=["admin"])


@app.get("/health")
async def health_check():
    from app.services.llm_service import llm_service
    return {
        "status": "ok",
        "version": settings.version,
        "environment": settings.environment,
        "llm": {
            "provider": "hermes3/ollama",
            "endpoint": settings.hermes_endpoint_url,
            "model": settings.hermes_model,
            "available": llm_service._available,
        },
    }


@app.get("/")
async def root():
    return {"message": "PlumbPrice AI API", "docs": "/docs"}
