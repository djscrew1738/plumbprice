import pytest
from httpx import AsyncClient
from starlette import status

pytestmark = pytest.mark.asyncio

from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """Test the health check endpoint."""
    with patch("app.services.llm_service.llm_service") as mock_service:
        mock_service._available = True
        response = await test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"

    assert "version" in data
    assert "environment" in data
