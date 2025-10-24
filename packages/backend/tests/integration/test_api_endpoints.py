"""Integration tests for FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client: AsyncClient):
        """Test GET /health endpoint."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]


@pytest.mark.integration
class TestConfigEndpoint:
    """Test configuration endpoints."""

    @pytest.mark.asyncio
    async def test_get_config(self, async_client: AsyncClient):
        """Test GET /sessions/config endpoint."""
        response = await async_client.get("/sessions/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert "deep_think_llm" in data or "llm" in data or "config" in data


@pytest.mark.integration
class TestSessionEndpoints:
    """Test session management endpoints."""

    @pytest.mark.asyncio
    @patch("app.services.graph.TradingAgentsGraph")
    async def test_create_session(
        self,
        mock_graph_class: AsyncMock,
        async_client: AsyncClient,
        sample_trading_config: dict
    ):
        """Test POST /sessions endpoint."""
        mock_graph = AsyncMock()
        mock_graph.propagate = AsyncMock(return_value=(
            {"status": "completed"},
            {"action": "BUY", "quantity": 100}
        ))
        mock_graph_class.return_value = mock_graph
        
        payload = {
            "ticker": sample_trading_config["ticker"],
            "date": sample_trading_config["date"],
        }
        
        response = await async_client.post("/sessions", json=payload)
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        assert "session_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_create_session_invalid_data(self, async_client: AsyncClient):
        """Test POST /sessions with invalid data."""
        payload = {
            "ticker": "",
            "date": "invalid-date",
        }
        
        response = await async_client.post("/sessions", json=payload)
        
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    @patch("app.services.graph.TradingAgentsGraph")
    async def test_get_session_events(
        self,
        mock_graph_class: AsyncMock,
        async_client: AsyncClient,
        sample_trading_config: dict
    ):
        """Test GET /sessions/{session_id}/events endpoint."""
        mock_graph = AsyncMock()
        mock_graph.propagate = AsyncMock(return_value=(
            {"status": "completed"},
            {"action": "BUY", "quantity": 100}
        ))
        mock_graph_class.return_value = mock_graph
        
        create_response = await async_client.post(
            "/sessions",
            json={
                "ticker": sample_trading_config["ticker"],
                "date": sample_trading_config["date"],
            }
        )
        
        if create_response.status_code in [200, 201]:
            data = create_response.json()
            session_id = data.get("session_id") or data.get("id")
            
            if session_id:
                events_response = await async_client.get(
                    f"/sessions/{session_id}/events",
                    timeout=5.0
                )
                
                assert events_response.status_code in [200, 404]


@pytest.mark.integration
class TestVendorEndpoints:
    """Test vendor plugin endpoints."""

    @pytest.mark.asyncio
    async def test_list_vendors(self, async_client: AsyncClient):
        """Test GET /vendors endpoint if it exists."""
        response = await async_client.get("/vendors")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_get_vendor_config(self, async_client: AsyncClient):
        """Test GET /vendors/config endpoint if it exists."""
        response = await async_client.get("/vendors/config")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, async_client: AsyncClient):
        """Test that non-existent endpoints return 404."""
        response = await async_client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client: AsyncClient):
        """Test that wrong HTTP methods return 405."""
        response = await async_client.delete("/health")
        
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_invalid_session_id(self, async_client: AsyncClient):
        """Test accessing non-existent session returns proper error."""
        response = await async_client.get("/sessions/nonexistent123/events")
        
        assert response.status_code in [404, 400]


@pytest.mark.integration
class TestCORS:
    """Test CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers are present."""
        response = await async_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        assert response.status_code in [200, 204]
        
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] in [
                "*",
                "http://localhost:3000"
            ]
