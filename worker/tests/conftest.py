"""pytest configuration for worker tests."""

import pytest
import os
from unittest.mock import MagicMock

# Set test environment variables
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for testing."""
    return {
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/1",
        "task_always_eager": True,
        "task_eager_propagates": True,
    }


@pytest.fixture
def mock_task_context():
    """Mock Celery task context."""
    context = MagicMock()
    context.request.id = "test-task-id-12345"
    context.request.retries = 0
    return context
