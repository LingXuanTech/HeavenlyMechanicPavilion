"""Unit tests for risk management service."""

from typing import Any

import pytest

from app.services.risk_management import (
    RiskConstraints,
    RiskManagementService,
)


@pytest.mark.unit
class TestRiskConstraints:
    """Test risk constraints configuration."""

    def test_default_constraints(self):
        """Test default risk constraints."""
        constraints = RiskConstraints()
        
        assert constraints.max_position_weight == 0.20
        assert constraints.default_stop_loss_pct == 0.10
        assert constraints.default_take_profit_pct == 0.20

    def test_custom_constraints(self):
        """Test custom risk constraints."""
        constraints = RiskConstraints(
            max_position_weight=0.15,
            default_stop_loss_pct=0.05,
            max_drawdown=0.20,
        )
        
        assert constraints.max_position_weight == 0.15
        assert constraints.default_stop_loss_pct == 0.05
        assert constraints.max_drawdown == 0.20


@pytest.mark.unit
class TestRiskManagementService:
    """Test risk management service."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = RiskManagementService()
        
        assert service.constraints is not None
        assert isinstance(service.constraints, RiskConstraints)

    def test_service_with_custom_constraints(self):
        """Test service with custom constraints."""
        constraints = RiskConstraints(max_position_weight=0.10)
        service = RiskManagementService(constraints)
        
        assert service.constraints.max_position_weight == 0.10


@pytest.mark.unit
class TestRiskMetricsCalculations:
    """Test various risk metric calculations."""

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation logic."""
        returns = [0.01, 0.02, -0.01, 0.03, 0.01]
        risk_free_rate = 0.02
        
        avg_return = sum(returns) / len(returns)
        excess_return = avg_return - risk_free_rate
        
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        sharpe_ratio = excess_return / std_dev if std_dev > 0 else 0
        
        assert isinstance(sharpe_ratio, float)

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        portfolio_values = [100000, 105000, 102000, 108000, 95000, 98000, 110000]
        
        peak = portfolio_values[0]
        max_drawdown = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        assert max_drawdown > 0
        assert max_drawdown < 1.0

    def test_var_calculation(self):
        """Test Value at Risk (VaR) calculation."""
        returns = [-0.05, -0.02, 0.01, 0.03, -0.01, 0.02, -0.03]
        confidence_level = 0.95
        
        sorted_returns = sorted(returns)
        var_index = int((1 - confidence_level) * len(sorted_returns))
        var = abs(sorted_returns[var_index])
        
        assert var >= 0
        assert isinstance(var, float)

    def test_beta_calculation(self):
        """Test beta calculation logic."""
        stock_returns = [0.02, -0.01, 0.03, 0.01, -0.02]
        market_returns = [0.015, -0.005, 0.025, 0.008, -0.015]
        
        avg_stock = sum(stock_returns) / len(stock_returns)
        avg_market = sum(market_returns) / len(market_returns)
        
        covariance = sum(
            (s - avg_stock) * (m - avg_market)
            for s, m in zip(stock_returns, market_returns)
        ) / len(stock_returns)
        
        market_variance = sum(
            (m - avg_market) ** 2 for m in market_returns
        ) / len(market_returns)
        
        beta = covariance / market_variance if market_variance > 0 else 1.0
        
        assert isinstance(beta, float)


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
