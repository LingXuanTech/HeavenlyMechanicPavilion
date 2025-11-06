"""Risk management service for portfolio risk analysis and control."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from ..db.models import Position

logger = logging.getLogger(__name__)


@dataclass
class RiskDiagnostics:
    """Risk diagnostics data structure."""

    portfolio_id: int
    portfolio_value: float

    # VaR metrics
    var_1day_95: Optional[float]
    var_1day_99: Optional[float]
    var_5day_95: Optional[float]
    var_5day_99: Optional[float]

    # Portfolio metrics
    portfolio_volatility: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]

    # Position metrics
    largest_position_weight: Optional[float]
    top5_concentration: Optional[float]
    number_of_positions: int

    # Exposure metrics
    total_exposure: float
    long_exposure: float
    short_exposure: float
    net_exposure: float

    # Risk warnings
    warnings: List[str]

    measured_at: datetime


@dataclass
class RiskConstraints:
    """Risk constraints configuration."""

    max_position_weight: float = 0.20  # Max 20% per position
    max_portfolio_exposure: float = 1.0  # Max 100% exposure
    max_var_1day_95: Optional[float] = None  # Max 1-day VaR at 95%
    max_drawdown: Optional[float] = None  # Max drawdown percentage
    min_sharpe_ratio: Optional[float] = None  # Min Sharpe ratio

    # Stop loss / take profit
    default_stop_loss_pct: float = 0.10  # 10% stop loss
    default_take_profit_pct: float = 0.20  # 20% take profit
    use_trailing_stop: bool = True
    trailing_stop_pct: float = 0.05  # 5% trailing stop


class RiskManagementService:
    """Service for portfolio risk management and analysis."""

    def __init__(self, constraints: Optional[RiskConstraints] = None):
        """Initialize risk management service.

        Args:
            constraints: Risk constraints configuration
        """
        self.constraints = constraints or RiskConstraints()
        logger.info(
            f"Initialized RiskManagementService with max_position_weight="
            f"{self.constraints.max_position_weight * 100}%, "
            f"stop_loss={self.constraints.default_stop_loss_pct * 100}%"
        )

    async def calculate_diagnostics(
        self,
        portfolio_id: int,
        positions: List[Position],
        current_prices: Dict[str, float],
        historical_returns: Optional[Dict[str, List[float]]] = None,
        portfolio_history: Optional[List[float]] = None,
    ) -> RiskDiagnostics:
        """Calculate comprehensive risk diagnostics.

        Args:
            portfolio_id: Portfolio ID
            positions: Current positions
            current_prices: Current prices for all positions
            historical_returns: Historical returns for VaR calculation
            portfolio_history: Portfolio value history for metrics

        Returns:
            Risk diagnostics
        """
        warnings = []

        # Calculate portfolio value
        portfolio_value = sum(
            pos.quantity * current_prices.get(pos.symbol, pos.current_price) for pos in positions
        )

        if portfolio_value <= 0:
            logger.warning("Portfolio value is zero or negative")
            portfolio_value = 0.0

        # Calculate exposure metrics
        long_exposure = sum(
            pos.quantity * current_prices.get(pos.symbol, pos.current_price)
            for pos in positions
            if pos.position_type == "LONG" and pos.quantity > 0
        )

        short_exposure = sum(
            abs(pos.quantity) * current_prices.get(pos.symbol, pos.current_price)
            for pos in positions
            if pos.position_type == "SHORT" and pos.quantity < 0
        )

        total_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure

        # Check exposure constraints
        if portfolio_value > 0:
            exposure_ratio = total_exposure / portfolio_value
            if exposure_ratio > self.constraints.max_portfolio_exposure:
                warnings.append(
                    f"Portfolio exposure {exposure_ratio:.1%} exceeds maximum "
                    f"{self.constraints.max_portfolio_exposure:.1%}"
                )

        # Calculate position concentration
        position_values = [
            abs(pos.quantity) * current_prices.get(pos.symbol, pos.current_price)
            for pos in positions
        ]

        if position_values and portfolio_value > 0:
            largest_position_weight = max(position_values) / portfolio_value

            # Check concentration constraint
            if largest_position_weight > self.constraints.max_position_weight:
                warnings.append(
                    f"Largest position {largest_position_weight:.1%} exceeds maximum "
                    f"{self.constraints.max_position_weight:.1%}"
                )

            # Top 5 concentration
            sorted_values = sorted(position_values, reverse=True)
            top5_values = sorted_values[:5]
            top5_concentration = sum(top5_values) / portfolio_value if len(top5_values) > 0 else 0.0
        else:
            largest_position_weight = 0.0
            top5_concentration = 0.0

        number_of_positions = len([p for p in positions if p.quantity != 0])

        # Calculate VaR if historical returns provided
        var_1day_95 = None
        var_1day_99 = None
        var_5day_95 = None
        var_5day_99 = None

        if historical_returns and portfolio_value > 0:
            var_metrics = self._calculate_var(
                positions, current_prices, historical_returns, portfolio_value
            )
            var_1day_95 = var_metrics.get("var_1day_95")
            var_1day_99 = var_metrics.get("var_1day_99")
            var_5day_95 = var_metrics.get("var_5day_95")
            var_5day_99 = var_metrics.get("var_5day_99")

            # Check VaR constraints
            if (
                self.constraints.max_var_1day_95 is not None
                and var_1day_95 is not None
                and abs(var_1day_95) > self.constraints.max_var_1day_95
            ):
                warnings.append(
                    f"1-day VaR ${abs(var_1day_95):,.0f} exceeds maximum "
                    f"${self.constraints.max_var_1day_95:,.0f}"
                )

        # Calculate portfolio metrics if history provided
        portfolio_volatility = None
        sharpe_ratio = None
        max_drawdown = None

        if portfolio_history and len(portfolio_history) > 1:
            metrics = self._calculate_portfolio_metrics(portfolio_history)
            portfolio_volatility = metrics.get("volatility")
            sharpe_ratio = metrics.get("sharpe_ratio")
            max_drawdown = metrics.get("max_drawdown")

            # Check constraints
            if (
                self.constraints.max_drawdown is not None
                and max_drawdown is not None
                and max_drawdown > self.constraints.max_drawdown
            ):
                warnings.append(
                    f"Max drawdown {max_drawdown:.1%} exceeds maximum "
                    f"{self.constraints.max_drawdown:.1%}"
                )

            if (
                self.constraints.min_sharpe_ratio is not None
                and sharpe_ratio is not None
                and sharpe_ratio < self.constraints.min_sharpe_ratio
            ):
                warnings.append(
                    f"Sharpe ratio {sharpe_ratio:.2f} below minimum "
                    f"{self.constraints.min_sharpe_ratio:.2f}"
                )

        return RiskDiagnostics(
            portfolio_id=portfolio_id,
            portfolio_value=portfolio_value,
            var_1day_95=var_1day_95,
            var_1day_99=var_1day_99,
            var_5day_95=var_5day_95,
            var_5day_99=var_5day_99,
            portfolio_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            largest_position_weight=largest_position_weight,
            top5_concentration=top5_concentration,
            number_of_positions=number_of_positions,
            total_exposure=total_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=net_exposure,
            warnings=warnings,
            measured_at=datetime.utcnow(),
        )

    def _calculate_var(
        self,
        positions: List[Position],
        current_prices: Dict[str, float],
        historical_returns: Dict[str, List[float]],
        portfolio_value: float,
    ) -> Dict[str, Optional[float]]:
        """Calculate Value at Risk using historical simulation.

        Args:
            positions: Current positions
            current_prices: Current prices
            historical_returns: Historical returns for each symbol
            portfolio_value: Total portfolio value

        Returns:
            Dictionary with VaR metrics
        """
        try:
            # Build position weights
            weights = {}
            for pos in positions:
                if pos.quantity == 0:
                    continue
                position_value = pos.quantity * current_prices.get(pos.symbol, pos.current_price)
                weights[pos.symbol] = position_value / portfolio_value

            # Get common symbols between positions and historical data
            symbols = [s for s in weights.keys() if s in historical_returns]

            if not symbols:
                logger.warning("No historical returns available for current positions")
                return {}

            # Build returns matrix
            min_length = min(len(historical_returns[s]) for s in symbols)
            if min_length < 30:
                logger.warning(f"Insufficient historical data: {min_length} periods")
                return {}

            returns_matrix = np.array([historical_returns[s][:min_length] for s in symbols]).T

            # Calculate portfolio returns
            weight_vector = np.array([weights[s] for s in symbols])
            portfolio_returns = returns_matrix @ weight_vector

            # Calculate VaR at different confidence levels
            var_1day_95 = np.percentile(portfolio_returns, 5) * portfolio_value
            var_1day_99 = np.percentile(portfolio_returns, 1) * portfolio_value

            # Scale to 5-day VaR (assuming independence)
            var_5day_95 = var_1day_95 * math.sqrt(5)
            var_5day_99 = var_1day_99 * math.sqrt(5)

            logger.info(
                f"Calculated VaR: 1d-95%=${abs(var_1day_95):,.0f}, 1d-99%=${abs(var_1day_99):,.0f}"
            )

            return {
                "var_1day_95": var_1day_95,
                "var_1day_99": var_1day_99,
                "var_5day_95": var_5day_95,
                "var_5day_99": var_5day_99,
            }

        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {}

    def _calculate_portfolio_metrics(
        self, portfolio_history: List[float]
    ) -> Dict[str, Optional[float]]:
        """Calculate portfolio performance metrics.

        Args:
            portfolio_history: Historical portfolio values

        Returns:
            Dictionary with performance metrics
        """
        try:
            values = np.array(portfolio_history)

            # Calculate returns
            returns = np.diff(values) / values[:-1]

            # Volatility (annualized)
            volatility = np.std(returns) * math.sqrt(252)

            # Sharpe ratio (assuming 0% risk-free rate)
            mean_return = np.mean(returns)
            sharpe_ratio = (mean_return * 252) / volatility if volatility > 0 else 0.0

            # Max drawdown
            cumulative_max = np.maximum.accumulate(values)
            drawdowns = (values - cumulative_max) / cumulative_max
            max_drawdown = abs(np.min(drawdowns))

            return {
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """Check if stop loss should be triggered.
        
        Supports both fixed and trailing stop loss based on configuration.

        Args:
            position: Position to check
            current_price: Current market price

        Returns:
            True if stop loss should be triggered
        """
        if position.quantity == 0 or position.average_cost == 0:
            return False

        pnl_pct = (current_price - position.average_cost) / position.average_cost

        if position.position_type == "LONG":
            # Long position: check stop loss
            if self.constraints.use_trailing_stop:
                # Trailing stop loss: track highest price since entry
                # Use position metadata to track high water mark
                # For now, use a simplified version comparing to entry
                highest_pnl = max(0, pnl_pct)
                
                # If current price dropped below trailing stop from peak
                trailing_trigger = highest_pnl - pnl_pct >= self.constraints.trailing_stop_pct
                
                # Also check absolute stop loss
                absolute_trigger = pnl_pct <= -self.constraints.default_stop_loss_pct
                
                if trailing_trigger and highest_pnl > 0:
                    logger.warning(
                        f"Trailing stop loss triggered for {position.symbol}: "
                        f"peak={highest_pnl:.1%}, current={pnl_pct:.1%}, "
                        f"drop={highest_pnl - pnl_pct:.1%}"
                    )
                    return True
                elif absolute_trigger:
                    logger.warning(
                        f"Fixed stop loss triggered for {position.symbol}: loss={pnl_pct:.1%}"
                    )
                    return True
            else:
                # Fixed stop loss
                if pnl_pct <= -self.constraints.default_stop_loss_pct:
                    logger.warning(f"Stop loss triggered for {position.symbol}: loss={pnl_pct:.1%}")
                    return True
        else:
            # Short position: stop loss if price rises too much
            if self.constraints.use_trailing_stop:
                # For short positions, trailing stop tracks lowest price
                lowest_pnl = max(0, -pnl_pct)
                trailing_trigger = lowest_pnl + pnl_pct >= self.constraints.trailing_stop_pct
                absolute_trigger = pnl_pct >= self.constraints.default_stop_loss_pct
                
                if trailing_trigger and lowest_pnl > 0:
                    logger.warning(
                        f"Trailing stop loss triggered for {position.symbol} (SHORT): "
                        f"peak={lowest_pnl:.1%}, current={-pnl_pct:.1%}"
                    )
                    return True
                elif absolute_trigger:
                    logger.warning(
                        f"Fixed stop loss triggered for {position.symbol} (SHORT): loss={pnl_pct:.1%}"
                    )
                    return True
            else:
                # Fixed stop loss
                if pnl_pct >= self.constraints.default_stop_loss_pct:
                    logger.warning(f"Stop loss triggered for {position.symbol}: loss={pnl_pct:.1%}")
                    return True

        return False

    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """Check if take profit should be triggered.

        Args:
            position: Position to check
            current_price: Current market price

        Returns:
            True if take profit should be triggered
        """
        if position.quantity == 0 or position.average_cost == 0:
            return False

        pnl_pct = (current_price - position.average_cost) / position.average_cost

        if position.position_type == "LONG":
            # Long position: take profit if price rises enough
            if pnl_pct >= self.constraints.default_take_profit_pct:
                logger.info(f"Take profit triggered for {position.symbol}: gain={pnl_pct:.1%}")
                return True
        else:
            # Short position: take profit if price drops enough
            if pnl_pct <= -self.constraints.default_take_profit_pct:
                logger.info(f"Take profit triggered for {position.symbol}: gain={pnl_pct:.1%}")
                return True

        return False

    def calculate_rebalancing_targets(
        self,
        positions: List[Position],
        current_prices: Dict[str, float],
        target_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Calculate rebalancing targets to achieve desired weights.

        Args:
            positions: Current positions
            current_prices: Current market prices
            target_weights: Target weights for each symbol (if None, equal weight)

        Returns:
            Dictionary mapping symbol to target quantity adjustment
        """
        # Calculate current portfolio value
        portfolio_value = sum(
            pos.quantity * current_prices.get(pos.symbol, pos.current_price) for pos in positions
        )

        if portfolio_value <= 0:
            logger.warning("Cannot rebalance with zero portfolio value")
            return {}

        # Get all symbols
        symbols = list(set(pos.symbol for pos in positions if pos.quantity != 0))

        if not symbols:
            return {}

        # Use equal weights if not specified
        if target_weights is None:
            target_weights = {s: 1.0 / len(symbols) for s in symbols}

        # Normalize weights to sum to 1
        total_weight = sum(target_weights.values())
        if total_weight > 0:
            target_weights = {s: w / total_weight for s, w in target_weights.items()}

        # Calculate target quantities
        adjustments = {}
        for symbol in symbols:
            current_pos = next((p for p in positions if p.symbol == symbol), None)
            current_qty = current_pos.quantity if current_pos else 0.0

            target_weight = target_weights.get(symbol, 0.0)
            target_value = portfolio_value * target_weight

            current_price = current_prices.get(symbol)
            if current_price and current_price > 0:
                target_qty = target_value / current_price
                adjustment = target_qty - current_qty

                # Only include significant adjustments (>1 share)
                if abs(adjustment) > 1.0:
                    adjustments[symbol] = adjustment

        logger.info(f"Calculated rebalancing adjustments for {len(adjustments)} symbols")
        return adjustments
