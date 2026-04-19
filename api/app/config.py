import json
import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "PlumbPrice AI"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://plumbprice:plumbprice_dev@localhost:5432/plumbprice"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_bucket_blueprints: str = "blueprints"
    minio_bucket_documents: str = "documents"
    minio_bucket_proposals: str = "proposals"

    # Auth
    secret_key: str = Field(...)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # AI — cloud providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"

    # AI — Hermes / Ollama (OpenAI-compatible local inference)
    hermes_endpoint_url: str = "http://localhost:11434/v1"
    # Primary model: best quality (used first)
    llm_primary_model: str = "qwen2.5:7b-instruct"
    # Secondary model: fast fallback (used when primary circuit-breaks)
    llm_secondary_model: str = "hermes3:3b"
    # Legacy alias — kept for backward-compat; overridden by llm_primary_model when set
    hermes_model: str = "qwen2.5:7b-instruct"
    hermes_api_key: str = "ollama"
    llm_timeout: float = 30.0
    llm_classify_timeout: float = 20.0
    llm_classify_threshold: float = 0.75
    llm_embedding_model: str = "nomic-embed-text"
    llm_vision_model: str = "llama3.2-vision"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3200", "https://app.ctlplumbingllc.com"]

    # External price data sources
    apify_token: Optional[str] = None
    apify_actor_id: str = "apify/website-content-crawler"
    construct_api_url: Optional[str] = None
    price_cache_ttl_hours: int = 24

    # Ferguson Trade API (Phase 2 live pricing)
    # Obtain via Ferguson Trade Partner Program: https://www.ferguson.com/content/website-info/api-overview
    ferguson_api_key: Optional[str] = None
    ferguson_api_base_url: str = "https://api.ferguson.com/v1"
    # Alert when live price deviates more than this fraction from stored cost
    price_change_alert_threshold: float = 0.10

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Observability
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1

    # Email (proposal delivery)
    resend_api_key: Optional[str] = None
    email_from: str = "estimates@ctlplumbingllc.com"

    # Public URL for customer-facing proposal links
    frontend_url: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env" if os.getenv("ENVIRONMENT") != "test" else None,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []

            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    pass
                else:
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]

            return [origin.strip() for origin in value.split(",") if origin.strip()]

        return value


settings = Settings()
