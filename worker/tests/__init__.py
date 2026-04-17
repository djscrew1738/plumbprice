"""Celery test fixtures and mocks."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from worker.worker import app as celery_app


@pytest.fixture
def celery_config():
    """Configure Celery for testing."""
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        broker_url="redis://localhost:6379/0",
        result_backend="redis://localhost:6379/1",
    )
    return celery_app


@pytest.fixture
def celery_worker():
    """Create a Celery worker instance for testing."""
    yield celery_app


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch("redis.Redis") as mock:
        yield mock


@pytest.fixture
def mock_s3_client():
    """Mock S3/MinIO client."""
    with patch("boto3.client") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    mock = MagicMock()
    yield mock
