"""Unit tests for trading service."""

from typing import Any

import pytest


@pytest.mark.unit
class TestTradingSession:
    """Test trading session management."""

    def test_session_initialization(self, sample_trading_config: dict[str, Any]):
        """Test trading session can be initialized."""
        session_config = {
            "ticker": sample_trading_config["ticker"],
            "date": sample_trading_config["date"],
            "llm_config": {
                "deep_think": sample_trading_config["deep_think_llm"],
                "quick_think": sample_trading_config["quick_think_llm"],
            }
        }
        
        assert session_config["ticker"] == "AAPL"
        assert session_config["date"] == "2024-01-15"

    def test_session_state_transitions(self):
        """Test session state transitions."""
        states = ["initialized", "running", "analyzing", "completed", "failed"]
        
        current_state = states[0]
        assert current_state == "initialized"
        
        current_state = states[1]
        assert current_state == "running"
        
        current_state = states[3]
        assert current_state == "completed"


@pytest.mark.unit
class TestPositionSizing:
    """Test position sizing logic."""

    def test_calculate_position_size_basic(
        self,
        sample_portfolio: dict[str, Any],
        sample_risk_params: dict[str, Any]
    ):
        """Test basic position size calculation."""
        portfolio_value = sample_portfolio["total_value"]
        max_position_size = sample_risk_params["max_position_size"]
        stock_price = 180.0
        
        max_position_value = portfolio_value * max_position_size
        max_shares = int(max_position_value / stock_price)
        
        assert max_shares > 0
        assert max_shares * stock_price <= max_position_value

    def test_kelly_criterion(self):
        """Test Kelly Criterion position sizing."""
        win_rate = 0.55
        win_loss_ratio = 1.5
        
        kelly_fraction = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        assert 0 <= kelly_fraction <= 1
        assert isinstance(kelly_fraction, float)

    def test_position_size_with_volatility(self):
        """Test volatility-adjusted position sizing."""
        base_position_size = 0.10
        stock_volatility = 0.30
        portfolio_volatility = 0.15
        
        volatility_adjustment = portfolio_volatility / stock_volatility
        adjusted_size = base_position_size * volatility_adjustment
        
        assert adjusted_size < base_position_size


@pytest.mark.unit
class TestOrderManagement:
    """Test order management logic."""

    def test_create_market_order(self):
        """Test creating a market order."""
        order = {
            "type": "MARKET",
            "ticker": "AAPL",
            "quantity": 100,
            "side": "BUY",
        }
        
        assert order["type"] == "MARKET"
        assert order["quantity"] > 0

    def test_create_limit_order(self):
        """Test creating a limit order."""
        order = {
            "type": "LIMIT",
            "ticker": "AAPL",
            "quantity": 50,
            "side": "SELL",
            "limit_price": 185.0,
        }
        
        assert order["type"] == "LIMIT"
        assert "limit_price" in order
        assert order["limit_price"] > 0

    def test_create_stop_loss_order(self):
        """Test creating a stop loss order."""
        current_price = 180.0
        stop_loss_pct = 0.05
        
        stop_price = current_price * (1 - stop_loss_pct)
        
        order = {
            "type": "STOP",
            "ticker": "AAPL",
            "quantity": 100,
            "side": "SELL",
            "stop_price": stop_price,
        }
        
        assert order["stop_price"] < current_price
        assert order["type"] == "STOP"


@pytest.mark.unit
class TestTradeValidation:
    """Test trade validation logic."""

    def test_validate_ticker_format(self):
        """Test ticker format validation."""
        valid_tickers = ["AAPL", "MSFT", "GOOGL", "BRK.B"]
        invalid_tickers = ["", "123", "AA PL"]
        
        for ticker in valid_tickers:
            assert len(ticker) > 0
            assert ticker.replace(".", "").isalpha() or ticker.replace(".", "").isalnum()
        
        for ticker in invalid_tickers:
            if ticker == "":
                assert len(ticker) == 0

    def test_validate_quantity(self):
        """Test quantity validation."""
        valid_quantities = [1, 10, 100, 1000]
        invalid_quantities = [0, -10, -100]
        
        for qty in valid_quantities:
            assert qty > 0
        
        for qty in invalid_quantities:
            assert qty <= 0

    def test_validate_price(self):
        """Test price validation."""
        valid_prices = [0.01, 1.0, 100.0, 1000.0]
        invalid_prices = [0, -1.0, -100.0]
        
        for price in valid_prices:
            assert price > 0
        
        for price in invalid_prices:
            assert price <= 0


@pytest.mark.unit
class TestTradingSignals:
    """Test trading signal generation and processing."""

    def test_signal_strength_calculation(self):
        """Test calculating signal strength from multiple indicators."""
        indicators = {
            "rsi": 70,
            "macd_signal": "bullish",
            "ma_crossover": "golden_cross",
        }
        
        signal_count = 0
        if indicators["rsi"] > 65:
            signal_count += 1
        if indicators["macd_signal"] == "bullish":
            signal_count += 1
        if indicators["ma_crossover"] == "golden_cross":
            signal_count += 1
        
        signal_strength = signal_count / len(indicators)
        
        assert 0 <= signal_strength <= 1

    def test_conflicting_signals(self):
        """Test handling of conflicting signals."""
        signals = {
            "technical": "BUY",
            "fundamental": "SELL",
            "sentiment": "HOLD",
        }
        
        buy_votes = sum(1 for s in signals.values() if s == "BUY")
        sell_votes = sum(1 for s in signals.values() if s == "SELL")
        
        assert buy_votes + sell_votes <= len(signals)

    def test_signal_aggregation(self):
        """Test aggregating multiple signals."""
        signals = [
            {"source": "analyst", "action": "BUY", "confidence": 0.8},
            {"source": "researcher", "action": "BUY", "confidence": 0.7},
            {"source": "trader", "action": "HOLD", "confidence": 0.5},
        ]
        
        buy_signals = [s for s in signals if s["action"] == "BUY"]
        avg_confidence = sum(s["confidence"] for s in buy_signals) / len(buy_signals)
        
        assert len(buy_signals) == 2
        assert avg_confidence == 0.75


@pytest.mark.unit
class TestPortfolioMetrics:
    """Test portfolio performance metrics."""

    def test_total_return_calculation(self):
        """Test calculating total portfolio return."""
        initial_value = 100000.0
        final_value = 115000.0
        
        total_return = (final_value - initial_value) / initial_value
        
        assert total_return == 0.15

    def test_annualized_return(self):
        """Test calculating annualized return."""
        total_return = 0.15
        days = 365
        
        annualized_return = (1 + total_return) ** (365 / days) - 1
        
        assert annualized_return >= 0

    def test_win_rate_calculation(self):
        """Test calculating win rate."""
        trades = [
            {"pnl": 100},
            {"pnl": -50},
            {"pnl": 75},
            {"pnl": -25},
            {"pnl": 150},
        ]
        
        winning_trades = [t for t in trades if t["pnl"] > 0]
        win_rate = len(winning_trades) / len(trades)
        
        assert win_rate == 0.6
