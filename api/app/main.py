from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.database import init_db
from app.routers import chat, estimates, suppliers, blueprints, proposals, auth, admin

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PlumbPrice AI API", version=settings.version, env=settings.environment)
    await init_db()
    logger.info("Database connected")
    yield
    # Shutdown
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

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(estimates.router, prefix="/api/v1/estimates", tags=["estimates"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(blueprints.router, prefix="/api/v1/blueprints", tags=["blueprints"])
app.include_router(proposals.router, prefix="/api/v1/proposals", tags=["proposals"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.version, "environment": settings.environment}


@app.get("/")
async def root():
    return {"message": "PlumbPrice AI API", "docs": "/docs"}
