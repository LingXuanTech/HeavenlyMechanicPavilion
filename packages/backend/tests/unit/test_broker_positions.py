"""Unit tests for broker position query methods."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.broker_adapter import OrderAction, OrderType
from app.services.brokers.alpaca_adapter import AlpacaBrokerAdapter
from app.core.errors import ExternalServiceError, ResourceNotFoundError, ValidationError


class TestAlpacaBrokerPositions:
    """Test AlpacaBrokerAdapter position query methods."""

    @pytest.fixture
    def mock_trading_client(self):
        """Create mock Alpaca trading client."""
        mock_client = MagicMock()
        
        # Mock account info for initialization
        mock_account = MagicMock()
        mock_account.status = "ACTIVE"
        mock_account.buying_power = "100000.00"
        mock_client.get_account.return_value = mock_account
        
        return mock_client

    @pytest.fixture
    def mock_data_client(self):
        """Create mock Alpaca data client."""
        return MagicMock()

    @pytest.fixture
    def broker_adapter(self, mock_trading_client, mock_data_client):
        """Create AlpacaBrokerAdapter with mocked clients."""
        with patch('app.services.brokers.alpaca_adapter.TradingClient', return_value=mock_trading_client):
            with patch('app.services.brokers.alpaca_adapter.StockHistoricalDataClient', return_value=mock_data_client):
                adapter = AlpacaBrokerAdapter(
                    api_key="test_key",
                    secret_key="test_secret",
                    paper_trading=True
                )
                return adapter

    @pytest.mark.asyncio
    async def test_get_positions_success(self, broker_adapter, mock_trading_client):
        """Test successful retrieval of all positions."""
        # Mock position data
        mock_pos1 = MagicMock()
        mock_pos1.symbol = "AAPL"
        mock_pos1.qty = "10"
        mock_pos1.side = "long"
        mock_pos1.avg_entry_price = "150.00"
        mock_pos1.current_price = "155.00"
        mock_pos1.market_value = "1550.00"
        mock_pos1.unrealized_pl = "50.00"
        mock_pos1.unrealized_plpc = "0.0333"
        
        mock_pos2 = MagicMock()
        mock_pos2.symbol = "TSLA"
        mock_pos2.qty = "-5"  # Short position
        mock_pos2.side = "short"
        mock_pos2.avg_entry_price = "200.00"
        mock_pos2.current_price = "195.00"
        mock_pos2.market_value = "-975.00"
        mock_pos2.unrealized_pl = "25.00"
        mock_pos2.unrealized_plpc = "0.025"
        
        mock_trading_client.get_all_positions.return_value = [mock_pos1, mock_pos2]
        
        # Call method
        positions = await broker_adapter.get_positions()
        
        # Assertions
        assert len(positions) == 2
        
        # Check first position (LONG)
        assert positions[0]["symbol"] == "AAPL"
        assert positions[0]["quantity"] == 10.0
        assert positions[0]["average_cost"] == 150.0
        assert positions[0]["current_price"] == 155.0
        assert positions[0]["market_value"] == 1550.0
        assert positions[0]["unrealized_pnl"] == 50.0
        assert positions[0]["position_type"] == "LONG"
        
        # Check second position (SHORT)
        assert positions[1]["symbol"] == "TSLA"
        assert positions[1]["quantity"] == 5.0  # Absolute value
        assert positions[1]["average_cost"] == 200.0
        assert positions[1]["position_type"] == "SHORT"
        
        mock_trading_client.get_all_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, broker_adapter, mock_trading_client):
        """Test retrieval when no positions exist."""
        mock_trading_client.get_all_positions.return_value = []
        
        positions = await broker_adapter.get_positions()
        
        assert positions == []
        mock_trading_client.get_all_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_positions_api_error(self, broker_adapter, mock_trading_client):
        """Test error handling when Alpaca API fails."""
        mock_trading_client.get_all_positions.side_effect = Exception("API Error")
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await broker_adapter.get_positions()
        
        assert "无法获取持仓列表" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_position_success(self, broker_adapter, mock_trading_client):
        """Test successful retrieval of a specific position."""
        mock_pos = MagicMock()
        mock_pos.symbol = "AAPL"
        mock_pos.qty = "15"
        mock_pos.side = "long"
        mock_pos.avg_entry_price = "148.50"
        mock_pos.current_price = "152.00"
        mock_pos.market_value = "2280.00"
        mock_pos.unrealized_pl = "52.50"
        mock_pos.unrealized_plpc = "0.0236"
        
        mock_trading_client.get_open_position.return_value = mock_pos
        
        position = await broker_adapter.get_position("AAPL")
        
        assert position is not None
        assert position["symbol"] == "AAPL"
        assert position["quantity"] == 15.0
        assert position["average_cost"] == 148.5
        assert position["current_price"] == 152.0
        assert position["position_type"] == "LONG"
        
        mock_trading_client.get_open_position.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, broker_adapter, mock_trading_client):
        """Test retrieval of non-existent position."""
        mock_trading_client.get_open_position.side_effect = Exception("position does not exist")
        
        position = await broker_adapter.get_position("NONEXIST")
        
        assert position is None

    @pytest.mark.asyncio
    async def test_get_position_empty_symbol(self, broker_adapter):
        """Test error handling for empty symbol."""
        with pytest.raises(ValidationError) as exc_info:
            await broker_adapter.get_position("")
        
        assert "股票代码不能为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_position_whitespace_symbol(self, broker_adapter):
        """Test error handling for whitespace-only symbol."""
        with pytest.raises(ValidationError) as exc_info:
            await broker_adapter.get_position("   ")
        
        assert "股票代码不能为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_position_case_insensitive(self, broker_adapter, mock_trading_client):
        """Test that symbol is converted to uppercase."""
        mock_pos = MagicMock()
        mock_pos.symbol = "AAPL"
        mock_pos.qty = "10"
        mock_pos.side = "long"
        mock_pos.avg_entry_price = "150.00"
        mock_pos.current_price = "155.00"
        mock_pos.market_value = "1550.00"
        mock_pos.unrealized_pl = "50.00"
        mock_pos.unrealized_plpc = "0.0333"
        
        mock_trading_client.get_open_position.return_value = mock_pos
        
        position = await broker_adapter.get_position("aapl")
        
        assert position is not None
        mock_trading_client.get_open_position.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_position_api_error(self, broker_adapter, mock_trading_client):
        """Test error handling for general API errors."""
        mock_trading_client.get_open_position.side_effect = Exception("Network error")
        
        with pytest.raises(ExternalServiceError) as exc_info:
            await broker_adapter.get_position("AAPL")
        
        assert "无法获取持仓信息" in str(exc_info.value)


class TestSimulatedBrokerPositions:
    """Test SimulatedBroker position query methods."""

    @pytest.fixture
    def simulated_broker(self):
        """Create SimulatedBroker instance."""
        from app.services.broker_adapter import SimulatedBroker
        return SimulatedBroker(initial_capital=100000.0)

    @pytest.mark.asyncio
    async def test_simulated_get_positions_returns_empty(self, simulated_broker):
        """Test that simulated broker returns empty list (not implemented)."""
        positions = await simulated_broker.get_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_simulated_get_position_returns_none(self, simulated_broker):
        """Test that simulated broker returns None (not implemented)."""
        position = await simulated_broker.get_position("AAPL")
        assert position is None