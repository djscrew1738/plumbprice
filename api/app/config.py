import json
import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "PlumbPrice AI"
    version: str = "2.5.1"
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
    minio_bucket_photos: str = "photos"

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
    # Cloud fallback (used when both local Ollama tiers circuit-break)
    llm_cloud_fallback_enabled: bool = True
    llm_cloud_fallback_provider: str = "openai"  # openai | anthropic
    llm_cloud_fallback_model: str = "gpt-4o-mini"
    # Cost ceiling: max USD spent on cloud calls per UTC day
    llm_cloud_daily_cap_usd: float = 5.0
    # Approximate cost per 1k tokens for the fallback model (input+output blended)
    llm_cloud_cost_per_1k_tokens_usd: float = 0.0006

    # AI — Hermes / Ollama (OpenAI-compatible local inference)
    hermes_endpoint_url: str = "http://localhost:11434/v1"
    # Primary model: best quality (used first)
    llm_primary_model: str = "qwen3:8b"
    # Secondary model: fast fallback (used when primary circuit-breaks)
    llm_secondary_model: str = "hermes3:3b"
    # Legacy alias — kept for backward-compat; overridden by llm_primary_model when set
    hermes_model: str = "qwen3:8b"
    hermes_api_key: str = "ollama"
    llm_timeout: float = 30.0
    llm_classify_timeout: float = 20.0
    llm_classify_threshold: float = 0.75
    llm_embedding_model: str = "mxbai-embed-large"
    llm_vision_model: str = "llama3.2-vision"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3200", "https://app.ctlplumbingllc.com"]

    # Privacy / data retention
    # How long uploaded user content (blueprints, photos, audio, docs) is kept
    # before being purged.  Soft-deleted records are hard-deleted after this
    # window via the `purge_expired_uploads` celery beat task.
    data_retention_days: int = 90
    # How long after soft-delete to wait before hard-delete (grace period)
    soft_delete_grace_days: int = 7

    # Phase 4 — Voice (Whisper STT)
    # Cloud STT settings — uses OPENAI_API_KEY via the existing openai client.
    voice_stt_enabled: bool = True
    voice_stt_model: str = "whisper-1"
    # Per-minute Whisper cost (OpenAI list price as of 2025).
    voice_stt_cost_per_minute_usd: float = 0.006
    # Daily ceiling for STT spend, separate from LLM budget.
    voice_stt_daily_cap_usd: float = 2.0
    # Hard upload cap for a single voice clip.
    voice_stt_max_seconds: int = 90
    voice_stt_max_bytes: int = 15 * 1024 * 1024

    # Cloud TTS — optional spoken reply on /voice/quote. Off by default.
    voice_tts_enabled: bool = False
    voice_tts_model: str = "gpt-4o-mini-tts"
    voice_tts_voice: str = "alloy"
    voice_tts_format: str = "mp3"
    voice_tts_cost_per_1k_chars_usd: float = 0.015
    voice_tts_daily_cap_usd: float = 1.0
    voice_tts_max_chars: int = 600

    # Phase 2 — Blueprint review
    # Detections below this confidence are flagged for manual review.
    blueprint_review_threshold: float = 0.65

    # Phase 5 — Public customer agent (autonomous widget)
    # Master switch for the public quote widget.
    public_agent_enabled: bool = True
    # Maximum draft total this agent will hand back to a customer; jobs
    # priced above this fall back to "we'll call you" lead capture.
    public_agent_max_total_usd: float = 7500.0
    # Only these task_codes are quotable by the public widget — anything
    # else triggers lead-capture fallback. Keep this conservative; expand
    # via env: PUBLIC_AGENT_ALLOWED_TASKS="A,B,C".
    public_agent_allowed_tasks: str = (
        "TOILET_REPLACE,LAV_FAUCET_REPLACE,KITCHEN_FAUCET_REPLACE,"
        "ANGLE_STOP_REPLACE,ANGLE_STOP_REPLACE_PAIR,HOSE_BIB_REPLACE,"
        "WATER_HEATER_REPLACE_50G_GAS,WATER_HEATER_REPLACE_40G_GAS,"
        "WATER_HEATER_REPLACE_50G_ELEC,DISPOSAL_REPLACE,"
        "DRAIN_CLEAN_STANDARD,DRAIN_CLEAN_KITCHEN,DRAIN_CLEAN_BATHTUB,"
        "DRAIN_CLEAN_SHOWER,P_TRAP_REPLACE,SUPPLY_LINE_REPLACE,"
        "SHOWER_HEAD_REPLACE,TUB_SPOUT_REPLACE,DISHWASHER_HOOKUP"
    )
    # IP-based rate ceiling: stops a single visitor abusing the widget.
    public_agent_rate_per_minute: int = 10
    public_agent_rate_per_day: int = 80

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
