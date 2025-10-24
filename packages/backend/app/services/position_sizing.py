"""Position sizing service for calculating order quantities."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PositionSizingMethod(str, Enum):
    """Position sizing methods."""
    
    FIXED_DOLLAR = "FIXED_DOLLAR"  # Fixed dollar amount per position
    FIXED_PERCENTAGE = "FIXED_PERCENTAGE"  # Fixed percentage of portfolio
    RISK_BASED = "RISK_BASED"  # Based on risk per trade
    VOLATILITY_BASED = "VOLATILITY_BASED"  # Inverse volatility weighting
    KELLY_CRITERION = "KELLY_CRITERION"  # Kelly criterion optimization


class PositionSizingService:
    """Service for calculating position sizes."""
    
    def __init__(
        self,
        method: PositionSizingMethod = PositionSizingMethod.FIXED_PERCENTAGE,
        default_percentage: float = 0.05,  # 5% of portfolio
        default_dollar_amount: float = 5000.0,
        max_position_size: float = 0.20,  # Max 20% per position
        risk_per_trade: float = 0.02,  # Max 2% risk per trade
    ):
        """Initialize position sizing service.
        
        Args:
            method: Position sizing method to use
            default_percentage: Default percentage of portfolio per position
            default_dollar_amount: Default dollar amount per position
            max_position_size: Maximum position size as percentage of portfolio
            risk_per_trade: Maximum risk per trade as percentage of portfolio
        """
        self.method = method
        self.default_percentage = default_percentage
        self.default_dollar_amount = default_dollar_amount
        self.max_position_size = max_position_size
        self.risk_per_trade = risk_per_trade
        
        logger.info(
            f"Initialized PositionSizingService with method={method}, "
            f"default_percentage={default_percentage*100}%, "
            f"max_position_size={max_position_size*100}%"
        )
    
    def calculate_quantity(
        self,
        symbol: str,
        action: str,
        current_price: float,
        portfolio_value: float,
        confidence_score: Optional[float] = None,
        volatility: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
    ) -> float:
        """Calculate order quantity based on position sizing method.
        
        Args:
            symbol: Stock symbol
            action: Trade action (BUY, SELL, etc.)
            current_price: Current market price
            portfolio_value: Total portfolio value
            confidence_score: Agent confidence score (0-1)
            volatility: Historical volatility
            stop_loss_price: Stop loss price for risk-based sizing
            
        Returns:
            Calculated quantity
        """
        if action in ["SELL", "COVER"]:
            # For sell/cover orders, quantity should be determined by existing position
            # This should be handled by the execution service
            logger.warning(
                f"Position sizing called for {action} order - "
                "quantity should be determined by existing position"
            )
            return 0.0
        
        if current_price <= 0:
            logger.error(f"Invalid price {current_price} for {symbol}")
            return 0.0
        
        if portfolio_value <= 0:
            logger.error(f"Invalid portfolio value {portfolio_value}")
            return 0.0
        
        # Calculate base quantity
        if self.method == PositionSizingMethod.FIXED_DOLLAR:
            quantity = self._calculate_fixed_dollar(current_price)
            
        elif self.method == PositionSizingMethod.FIXED_PERCENTAGE:
            quantity = self._calculate_fixed_percentage(current_price, portfolio_value)
            
        elif self.method == PositionSizingMethod.RISK_BASED:
            if stop_loss_price is None:
                logger.warning("Stop loss price not provided for risk-based sizing, using fixed percentage")
                quantity = self._calculate_fixed_percentage(current_price, portfolio_value)
            else:
                quantity = self._calculate_risk_based(
                    current_price, portfolio_value, stop_loss_price
                )
        
        elif self.method == PositionSizingMethod.VOLATILITY_BASED:
            if volatility is None:
                logger.warning("Volatility not provided for volatility-based sizing, using fixed percentage")
                quantity = self._calculate_fixed_percentage(current_price, portfolio_value)
            else:
                quantity = self._calculate_volatility_based(
                    current_price, portfolio_value, volatility
                )
        
        elif self.method == PositionSizingMethod.KELLY_CRITERION:
            if confidence_score is None:
                logger.warning("Confidence score not provided for Kelly criterion, using fixed percentage")
                quantity = self._calculate_fixed_percentage(current_price, portfolio_value)
            else:
                quantity = self._calculate_kelly(
                    current_price, portfolio_value, confidence_score
                )
        
        else:
            logger.warning(f"Unknown position sizing method {self.method}, using fixed percentage")
            quantity = self._calculate_fixed_percentage(current_price, portfolio_value)
        
        # Apply maximum position size constraint
        max_quantity = (portfolio_value * self.max_position_size) / current_price
        if quantity > max_quantity:
            logger.info(
                f"Quantity {quantity} exceeds max position size, capping at {max_quantity}"
            )
            quantity = max_quantity
        
        # Round to avoid fractional shares (could make this configurable)
        quantity = round(quantity)
        
        logger.info(
            f"Calculated quantity for {symbol}: {quantity} shares @ ${current_price:.2f} "
            f"(total value: ${quantity * current_price:,.2f})"
        )
        
        return quantity
    
    def _calculate_fixed_dollar(self, current_price: float) -> float:
        """Calculate quantity based on fixed dollar amount.
        
        Args:
            current_price: Current market price
            
        Returns:
            Calculated quantity
        """
        return self.default_dollar_amount / current_price
    
    def _calculate_fixed_percentage(
        self, current_price: float, portfolio_value: float
    ) -> float:
        """Calculate quantity based on fixed percentage of portfolio.
        
        Args:
            current_price: Current market price
            portfolio_value: Total portfolio value
            
        Returns:
            Calculated quantity
        """
        position_value = portfolio_value * self.default_percentage
        return position_value / current_price
    
    def _calculate_risk_based(
        self,
        current_price: float,
        portfolio_value: float,
        stop_loss_price: float,
    ) -> float:
        """Calculate quantity based on risk per trade.
        
        Args:
            current_price: Current market price
            portfolio_value: Total portfolio value
            stop_loss_price: Stop loss price
            
        Returns:
            Calculated quantity
        """
        # Calculate risk per share
        risk_per_share = abs(current_price - stop_loss_price)
        
        if risk_per_share <= 0:
            logger.warning("Invalid stop loss price, using fixed percentage")
            return self._calculate_fixed_percentage(current_price, portfolio_value)
        
        # Calculate maximum risk amount
        max_risk_amount = portfolio_value * self.risk_per_trade
        
        # Calculate quantity based on risk
        quantity = max_risk_amount / risk_per_share
        
        return quantity
    
    def _calculate_volatility_based(
        self,
        current_price: float,
        portfolio_value: float,
        volatility: float,
    ) -> float:
        """Calculate quantity based on inverse volatility.
        
        Higher volatility = smaller position size
        
        Args:
            current_price: Current market price
            portfolio_value: Total portfolio value
            volatility: Historical volatility (e.g., 30-day)
            
        Returns:
            Calculated quantity
        """
        if volatility <= 0:
            logger.warning("Invalid volatility, using fixed percentage")
            return self._calculate_fixed_percentage(current_price, portfolio_value)
        
        # Adjust position size inversely to volatility
        # Normalize volatility to a reasonable range (e.g., 10-50%)
        normalized_volatility = max(0.10, min(0.50, volatility))
        
        # Scale percentage inversely with volatility
        adjusted_percentage = self.default_percentage * (0.20 / normalized_volatility)
        
        # Cap at max position size
        adjusted_percentage = min(adjusted_percentage, self.max_position_size)
        
        position_value = portfolio_value * adjusted_percentage
        return position_value / current_price
    
    def _calculate_kelly(
        self,
        current_price: float,
        portfolio_value: float,
        confidence_score: float,
    ) -> float:
        """Calculate quantity using Kelly Criterion.
        
        Kelly % = W - [(1 - W) / R]
        where W = win probability, R = win/loss ratio
        
        Args:
            current_price: Current market price
            portfolio_value: Total portfolio value
            confidence_score: Win probability (0-1)
            
        Returns:
            Calculated quantity
        """
        # Simplified Kelly with assumed win/loss ratio of 2:1
        win_loss_ratio = 2.0
        
        # Kelly percentage
        kelly_pct = confidence_score - ((1 - confidence_score) / win_loss_ratio)
        
        # Use fractional Kelly (50%) to reduce risk
        kelly_pct = kelly_pct * 0.5
        
        # Ensure non-negative and cap at max
        kelly_pct = max(0.0, min(kelly_pct, self.max_position_size))
        
        if kelly_pct <= 0:
            logger.warning("Kelly criterion suggests no position, using minimum")
            kelly_pct = self.default_percentage * 0.1
        
        position_value = portfolio_value * kelly_pct
        return position_value / current_price
