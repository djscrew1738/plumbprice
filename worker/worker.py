"""Celery application configuration."""

from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "plumbprice",
    broker=REDIS_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=[
        "tasks.supplier_refresh",
        "tasks.document_processing",
        "tasks.blueprint_analysis",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Chicago",
    enable_utc=True,
    beat_schedule={
        "refresh-supplier-prices-daily": {
            "task": "tasks.supplier_refresh.refresh_all_suppliers",
            "schedule": 86400.0,  # every 24 hours
        },
    },
)

if __name__ == "__main__":
    app.start()
