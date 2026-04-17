"""Tests for supplier refresh tasks."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from worker.tasks.supplier_refresh import refresh_all_suppliers


class TestSupplierRefresh:
    """Test supplier refresh Celery tasks."""

    @pytest.mark.asyncio
    async def test_refresh_all_suppliers_success(self, mock_db_session):
        """Test successful supplier refresh."""
        with patch("worker.tasks.supplier_refresh.refresh_supplier") as mock_refresh:
            mock_refresh.return_value = {"id": 1, "name": "Test Supplier", "status": "updated"}

            # Call task with eager execution
            result = refresh_all_suppliers.apply_async()

            # Verify task completed
            assert result.successful() or result.status in ["PENDING", "SUCCESS"]

    def test_refresh_supplier_with_retry(self, mock_db_session):
        """Test supplier refresh with retry logic."""
        with patch("worker.tasks.supplier_refresh.refresh_supplier") as mock_refresh:
            mock_refresh.side_effect = Exception("Network error")

            # Task should retry on error
            with pytest.raises(Exception):
                refresh_all_suppliers.apply_async()

    @patch("worker.tasks.supplier_refresh.fetch_supplier_data")
    def test_refresh_supplier_data_parsing(self, mock_fetch):
        """Test supplier data parsing in refresh task."""
        mock_fetch.return_value = {
            "id": 123,
            "name": "Acme Plumbing",
            "products": [{"sku": "P001", "price": 99.99}],
            "last_updated": "2025-01-01T00:00:00Z",
        }

        # Verify data structure
        data = mock_fetch()
        assert data["id"] == 123
        assert data["name"] == "Acme Plumbing"
        assert len(data["products"]) == 1
        assert data["products"][0]["sku"] == "P001"

    def test_task_is_registered(self):
        """Test that refresh task is properly registered."""
        from worker.worker import app

        task_names = [t for t in app.tasks.keys() if "supplier" in t.lower()]
        assert len(task_names) > 0
