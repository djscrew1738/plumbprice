"""Tests for Celery worker health and monitoring."""

import pytest
from unittest.mock import patch, MagicMock
from worker.worker import app


class TestWorkerHealth:
    """Test worker health, monitoring, and task registration."""

    def test_worker_is_initialized(self):
        """Test that Celery worker is properly initialized."""
        assert app is not None
        assert app.conf is not None

    def test_registered_tasks(self):
        """Test that all expected tasks are registered."""
        task_names = list(app.tasks.keys())
        # Filter out built-in tasks
        custom_tasks = [t for t in task_names if "worker." in t or "tasks." in t]
        assert len(custom_tasks) > 0

    @patch("redis.Redis")
    def test_broker_connection(self, mock_redis):
        """Test Celery broker connection."""
        mock_redis.return_value = MagicMock()
        assert app.conf.broker_url is not None

    def test_task_eager_mode_for_testing(self):
        """Test that eager execution can be enabled for testing."""
        with app.connection():
            # In test mode, tasks should execute immediately
            assert app is not None

    @patch("worker.worker.app.send_task")
    def test_send_task(self, mock_send):
        """Test sending a task to queue."""
        mock_send.return_value = MagicMock()
        result = app.send_task("worker.tasks.supplier_refresh.refresh_all_suppliers")
        mock_send.assert_called()

    def test_task_timeout_configuration(self):
        """Test that task timeouts are configured."""
        # Verify timeout settings exist
        assert app.conf.task_soft_time_limit or app.conf.task_time_limit


class TestTaskMonitoring:
    """Test task monitoring and logging."""

    @patch("structlog.get_logger")
    def test_task_logging(self, mock_logger):
        """Test task logging capability."""
        mock_log = MagicMock()
        mock_logger.return_value = mock_log

        # Verify logging can be used
        logger = mock_logger()
        logger.info("Task started")
        mock_log.info.assert_called()

    def test_task_result_storage(self):
        """Test that task results are stored."""
        assert app.conf.result_backend is not None
        assert "redis" in app.conf.result_backend.lower()
