import json
import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "PlumbPrice AI"
    version: str = "0.1.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://plumbprice:plumbprice_dev@localhost:5432/plumbprice",
        env="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, env="MINIO_SECURE")
    minio_bucket_blueprints: str = "blueprints"
    minio_bucket_documents: str = "documents"
    minio_bucket_proposals: str = "proposals"

    # Auth
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # AI — cloud providers
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    default_llm_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="gpt-4o-mini", env="DEFAULT_LLM_MODEL")

    # AI — Hermes / Ollama (OpenAI-compatible local inference)
    hermes_endpoint_url: str = Field(
        default="http://localhost:11434/v1",
        env="HERMES_ENDPOINT_URL",
    )
    # Primary model: best quality (used first)
    llm_primary_model: str = Field(default="qwen2.5:7b-instruct", env="LLM_PRIMARY_MODEL")
    # Secondary model: fast fallback (used when primary circuit-breaks)
    llm_secondary_model: str = Field(default="hermes3:3b", env="LLM_SECONDARY_MODEL")
    # Legacy alias — kept for backward-compat; overridden by llm_primary_model when set
    hermes_model: str = Field(default="qwen2.5:7b-instruct", env="HERMES_MODEL")
    hermes_api_key: str = Field(default="ollama", env="HERMES_API_KEY")
    llm_timeout: float = Field(default=30.0, env="LLM_TIMEOUT")
    llm_classify_timeout: float = Field(default=20.0, env="LLM_CLASSIFY_TIMEOUT")
    llm_classify_threshold: float = Field(default=0.75, env="LLM_CLASSIFY_THRESHOLD")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3200", "https://pricing.ctlplumbingllc.com"],
        env="CORS_ORIGINS"
    )

    # External price data sources
    apify_token: Optional[str] = Field(default=None, env="APIFY_TOKEN")
    apify_actor_id: str = Field(default="apify/website-content-crawler", env="APIFY_ACTOR_ID")
    construct_api_url: Optional[str] = Field(default=None, env="CONSTRUCT_API_URL")
    price_cache_ttl_hours: int = Field(default=24, env="PRICE_CACHE_TTL_HOURS")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")

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
