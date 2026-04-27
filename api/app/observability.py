"""
Optional Sentry + OpenTelemetry initialization (b1).

Both are no-ops unless their DSN/endpoint env vars are set, so the app
runs identically without observability infra in dev. When SENTRY_DSN is
configured, errors and traces ship; when OTEL_EXPORTER_OTLP_ENDPOINT is
set, traces export via OTLP.

Tier decision (developer/team/business) is still pending — the SDK is
free regardless and ingest cost is the only knob. Wire env vars when
the tier lands.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger()


def init_sentry() -> bool:
    """
    Initialize the Sentry SDK if SENTRY_DSN is set. Returns True if active.
    Safe to call repeatedly.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("observability.sentry.skipped", reason="no_dsn")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("ENVIRONMENT", "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("observability.sentry.initialized")
        return True
    except ImportError:
        logger.warning("observability.sentry.import_failed", note="install sentry-sdk to enable")
        return False
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("observability.sentry.init_failed", error=str(exc))
        return False


def init_otel(app: Any | None = None) -> bool:
    """
    Initialize OpenTelemetry tracing if OTEL_EXPORTER_OTLP_ENDPOINT is set.
    Returns True if active.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        logger.info("observability.otel.skipped", reason="no_endpoint")
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": "plumbprice-api"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)

        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)
            except ImportError:
                logger.warning("observability.otel.fastapi_instrumentation_missing")

        logger.info("observability.otel.initialized", endpoint=endpoint)
        return True
    except ImportError:
        logger.warning(
            "observability.otel.import_failed",
            note="install opentelemetry-{api,sdk,exporter-otlp} to enable",
        )
        return False
    except Exception as exc:  # pragma: no cover
        logger.warning("observability.otel.init_failed", error=str(exc))
        return False
