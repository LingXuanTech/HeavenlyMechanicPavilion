"""Integration tests for broker position API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.services.brokers.alpaca_adapter import AlpacaBrokerAdapter


class TestBrokerPositionsAPI:
    """Integration tests for /trading/broker/positions endpoints."""

    @pytest.fixture
    def mock_execution_service(self):
        """Create mock execution service with broker."""
        service = MagicMock()
        
        # Mock broker with position methods
        mock_broker = MagicMock(spec=AlpacaBrokerAdapter)
        mock_broker.get_positions = AsyncMock()
        mock_broker.get_position = AsyncMock()
        
        service.broker = mock_broker
        return service

    @pytest.fixture
    def mock_trading_session_service(self, mock_execution_service):
        """Mock the global trading session service."""
        with patch('app.api.trading.trading_session_service') as mock_service:
            mock_service.get_execution_service.return_value = mock_execution_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_get_broker_positions_success(self, mock_trading_session_service, mock_execution_service):
        """Test successful retrieval of all broker positions."""
        # Setup mock data
        mock_positions = [
            {
                "symbol": "AAPL",
                "quantity": 10.0,
                "average_cost": 150.0,
                "current_price": 155.0,
                "market_value": 1550.0,
                "unrealized_pnl": 50.0,
                "unrealized_pnl_percent": 0.0333,
                "position_type": "LONG",
                "side": "long"
            },
            {
                "symbol": "TSLA",
                "quantity": 5.0,
                "average_cost": 200.0,
                "current_price": 195.0,
                "market_value": 975.0,
                "unrealized_pnl": -25.0,
                "unrealized_pnl_percent": -0.025,
                "position_type": "LONG",
                "side": "long"
            }
        ]
        mock_execution_service.broker.get_positions.return_value = mock_positions
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions", params={"session_id": 1})
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "AAPL"
        assert data[1]["symbol"] == "TSLA"
        
        mock_execution_service.broker.get_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_broker_positions_empty(self, mock_trading_session_service, mock_execution_service):
        """Test retrieval when no positions exist."""
        mock_execution_service.broker.get_positions.return_value = []
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions", params={"session_id": 1})
        
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_broker_positions_session_not_found(self, mock_trading_session_service):
        """Test error when session is not found."""
        mock_trading_session_service.get_execution_service.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions", params={"session_id": 999})
        
        assert response.status_code == 404
        assert "not found or not active" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_broker_positions_broker_error(self, mock_trading_session_service, mock_execution_service):
        """Test error handling when broker API fails."""
        mock_execution_service.broker.get_positions.side_effect = Exception("Broker API error")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions", params={"session_id": 1})
        
        assert response.status_code == 500
        assert "无法从券商获取持仓" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_broker_position_success(self, mock_trading_session_service, mock_execution_service):
        """Test successful retrieval of a specific position."""
        mock_position = {
            "symbol": "AAPL",
            "quantity": 15.0,
            "average_cost": 148.5,
            "current_price": 152.0,
            "market_value": 2280.0,
            "unrealized_pnl": 52.5,
            "unrealized_pnl_percent": 0.0236,
            "position_type": "LONG",
            "side": "long"
        }
        mock_execution_service.broker.get_position.return_value = mock_position
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions/AAPL", params={"session_id": 1})
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["quantity"] == 15.0
        
        mock_execution_service.broker.get_position.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_broker_position_not_found(self, mock_trading_session_service, mock_execution_service):
        """Test retrieval of non-existent position."""
        mock_execution_service.broker.get_position.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions/NONEXIST", params={"session_id": 1})
        
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_broker_position_session_not_found(self, mock_trading_session_service):
        """Test error when session is not found."""
        mock_trading_session_service.get_execution_service.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions/AAPL", params={"session_id": 999})
        
        assert response.status_code == 404
        assert "not found or not active" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_broker_position_broker_error(self, mock_trading_session_service, mock_execution_service):
        """Test error handling when broker API fails."""
        mock_execution_service.broker.get_position.side_effect = Exception("Network error")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/trading/broker/positions/AAPL", params={"session_id": 1})
        
        assert response.status_code == 500
        assert "无法从券商获取持仓" in response.json()["detail"]


class TestBrokerPositionsEndToEnd:
    """End-to-end tests with real (mocked) broker flow."""

    @pytest.mark.asyncio
    async def test_positions_flow_with_active_session(self):
        """Test complete flow: start session, get positions."""
        # This would require full setup with database, etc.
        # For now, we'll mark it as a placeholder for future implementation
        pytest.skip("End-to-end test requires full application setup")

    @pytest.mark.asyncio
    async def test_compare_db_vs_broker_positions(self):
        """Test comparing database positions with broker positions."""
        # This would verify data consistency between DB and broker
        pytest.skip("Requires full integration setup")