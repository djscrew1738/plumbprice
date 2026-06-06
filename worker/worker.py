"""Celery application configuration.

Queues
------
default     — general tasks (document processing, blueprint analysis, privacy)
high        — latency-sensitive tasks (notifications, photo session finalisation)
ml          — compute-heavy ML tasks (fine-tuning, price forecast); concurrency=1
"""

from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "plumbprice",
    broker=REDIS_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    include=[
        "worker.tasks.supplier_refresh",
        "worker.tasks.document_processing",
        "worker.tasks.blueprint_analysis",
        "worker.tasks.privacy",
        "worker.tasks.finetune",
        "worker.tasks.price_forecast",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Chicago",
    enable_utc=True,
    # Route tasks to appropriate queues
    task_routes={
        "worker.tasks.finetune.*": {"queue": "ml"},
        "worker.tasks.price_forecast.*": {"queue": "ml"},
        "worker.tasks.supplier_refresh.*": {"queue": "default"},
        "worker.tasks.document_processing.*": {"queue": "default"},
        "worker.tasks.blueprint_analysis.*": {"queue": "default"},
        "worker.tasks.privacy.*": {"queue": "default"},
    },
    beat_schedule={
        "refresh-supplier-prices-daily": {
            "task": "worker.tasks.supplier_refresh.refresh_all_suppliers",
            "schedule": 86400.0,  # every 24 hours
        },
        "purge-expired-uploads-daily": {
            "task": "worker.tasks.privacy.purge_expired_uploads",
            "schedule": 86400.0,  # every 24 hours
        },
        "compute-price-forecast-weekly": {
            "task": "worker.tasks.price_forecast.compute_price_trends",
            "schedule": 7 * 86400.0,  # every 7 days
        },
    },
)

if __name__ == "__main__":
    app.start()
