"""Broker adapter interface and implementations for trade execution."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from ..core.errors import (
    ExternalServiceError,
    InsufficientFundsError,
    ResourceNotFoundError,
    TradingAgentsError,
    ValidationError,
)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from .market_data import MarketDataService


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderAction(str, Enum):
    """Order action enumeration."""

    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"


@dataclass
class OrderRequest:
    """Order request data structure."""

    symbol: str
    action: OrderAction
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"

    # Optional metadata
    portfolio_id: Optional[int] = None
    session_id: Optional[int] = None
    decision_rationale: Optional[str] = None
    confidence_score: Optional[float] = None


@dataclass
class OrderResponse:
    """Order response data structure."""

    order_id: str
    status: OrderStatus
    symbol: str
    action: OrderAction
    quantity: float
    filled_quantity: float
    average_fill_price: Optional[float]

    # Execution details
    commission: float = 0.0
    fees: float = 0.0
    message: Optional[str] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


@dataclass
class MarketPrice:
    """Market price data structure."""

    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: datetime


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""

    @abstractmethod
    async def submit_order(self, order: OrderRequest) -> OrderResponse:
        """Submit an order to the broker.

        Args:
            order: Order request

        Returns:
            Order response with execution details
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel an existing order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Order response with updated status
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get the status of an order.

        Args:
            order_id: Order ID

        Returns:
            Order response with current status
        """
        pass

    @abstractmethod
    async def get_market_price(self, symbol: str) -> MarketPrice:
        """Get current market price for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Market price data
        """
        pass

    @abstractmethod
    async def get_buying_power(self) -> float:
        """Get available buying power.

        Returns:
            Available buying power
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get all current positions.
        
        Returns:
            List of positions, each containing:
            - symbol: Stock symbol
            - quantity: Position quantity (absolute value)
            - average_cost: Average entry price
            - current_price: Current market price
            - market_value: Current market value
            - unrealized_pnl: Unrealized profit/loss
            - unrealized_pnl_percent: Unrealized P&L percentage
            - position_type: Position type (LONG/SHORT)
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position dict or None if no position exists
            Fields are the same as get_positions()
        """
        pass


class SimulatedBroker(BrokerAdapter):
    """Simulated broker for paper trading."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_per_trade: float = 0.0,
        slippage_percent: float = 0.001,
        market_data_service: Optional["MarketDataService"] = None,
    ):
        """Initialize simulated broker.

        Args:
            initial_capital: Initial capital for simulation
            commission_per_trade: Commission per trade
            slippage_percent: Slippage as percentage (0.001 = 0.1%)
            market_data_service: Service used to source deterministic market quotes.
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_per_trade = commission_per_trade
        self.slippage_percent = slippage_percent

        if market_data_service is None:
            from .market_data import MarketDataService

            self.market_data_service = MarketDataService()
        else:
            self.market_data_service = market_data_service

        self.orders = {}
        self.order_counter = 0

        logger.info(
            f"Initialized SimulatedBroker with capital=${initial_capital:,.2f}, "
            f"commission=${commission_per_trade}, slippage={slippage_percent * 100}%"
        )

    async def submit_order(self, order: OrderRequest) -> OrderResponse:
        """Submit an order for simulated execution.

        Args:
            order: Order request

        Returns:
            Order response with simulated execution
        """
        self.order_counter += 1
        order_id = f"SIM{self.order_counter:06d}"

        logger.info(
            f"Submitting simulated order {order_id}: {order.action.value} "
            f"{order.quantity} {order.symbol} @ {order.order_type.value}"
        )

        try:
            # Get market price
            market_price = await self.get_market_price(order.symbol)

            # Pre-trade capital check for buy-side orders
            if order.action in [OrderAction.BUY, OrderAction.COVER]:
                estimated_price = market_price.ask if order.order_type != OrderType.LIMIT else (
                    order.limit_price or market_price.ask
                )
                required_capital = order.quantity * estimated_price
                if required_capital > self.current_capital:
                    raise InsufficientFundsError(
                        f"Insufficient capital to execute order {order_id}.",
                        details={
                            "symbol": order.symbol,
                            "required": round(required_capital, 2),
                            "available": round(self.current_capital, 2),
                            "order_type": order.order_type.value,
                        },
                    )

            # Determine fill price based on order type
            if order.order_type == OrderType.MARKET:
                # Market orders execute immediately with slippage
                if order.action in [OrderAction.BUY, OrderAction.COVER]:
                    fill_price = market_price.ask * (1 + self.slippage_percent)
                else:
                    fill_price = market_price.bid * (1 - self.slippage_percent)

                status = OrderStatus.FILLED
                filled_quantity = order.quantity
                filled_at = datetime.utcnow()

            elif order.order_type == OrderType.LIMIT:
                # Limit orders require price to be met
                # For simulation, we'll execute if limit price is reasonable
                if order.limit_price is None:
                    raise ValidationError(
                        "Limit price required for LIMIT orders",
                        details={"symbol": order.symbol, "order_type": order.order_type.value},
                    )

                if order.action in [OrderAction.BUY, OrderAction.COVER]:
                    if order.limit_price >= market_price.ask:
                        fill_price = min(order.limit_price, market_price.ask)
                        status = OrderStatus.FILLED
                        filled_quantity = order.quantity
                        filled_at = datetime.utcnow()
                    else:
                        fill_price = None
                        status = OrderStatus.PENDING
                        filled_quantity = 0.0
                        filled_at = None
                else:
                    if order.limit_price <= market_price.bid:
                        fill_price = max(order.limit_price, market_price.bid)
                        status = OrderStatus.FILLED
                        filled_quantity = order.quantity
                        filled_at = datetime.utcnow()
                    else:
                        fill_price = None
                        status = OrderStatus.PENDING
                        filled_quantity = 0.0
                        filled_at = None

            else:
                # For other order types, default to market-like behavior
                if order.action in [OrderAction.BUY, OrderAction.COVER]:
                    fill_price = market_price.ask * (1 + self.slippage_percent)
                else:
                    fill_price = market_price.bid * (1 - self.slippage_percent)

                status = OrderStatus.FILLED
                filled_quantity = order.quantity
                filled_at = datetime.utcnow()

            # Calculate commission
            commission = self.commission_per_trade

            # Update capital if filled
            if status == OrderStatus.FILLED and fill_price is not None:
                trade_value = filled_quantity * fill_price
                if order.action in [OrderAction.BUY, OrderAction.COVER]:
                    self.current_capital -= trade_value + commission
                else:
                    self.current_capital += trade_value - commission

                logger.info(
                    f"Order {order_id} FILLED: {filled_quantity} @ ${fill_price:.2f}, "
                    f"capital now ${self.current_capital:,.2f}"
                )

            response = OrderResponse(
                order_id=order_id,
                status=status,
                symbol=order.symbol,
                action=order.action,
                quantity=order.quantity,
                filled_quantity=filled_quantity,
                average_fill_price=fill_price,
                commission=commission,
                fees=0.0,
                message="Simulated execution",
                submitted_at=datetime.utcnow(),
                filled_at=filled_at,
            )

            self.orders[order_id] = response
            return response

        except TradingAgentsError:
            raise
        except Exception as e:  # pragma: no cover - defensive
            logger.error(
                f"Error submitting order {order_id}: {e}",
                exc_info=True,
            )
            raise ExternalServiceError(
                f"Broker failed to submit order {order_id}",
                details={
                    "symbol": order.symbol,
                    "action": order.action.value,
                    "order_type": order.order_type.value,
                },
            ) from e

    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Updated order response
        """
        if order_id not in self.orders:
            raise ResourceNotFoundError(
                f"Order {order_id} not found",
                details={"order_id": order_id},
            )

        order = self.orders[order_id]

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"Cannot cancel order {order_id} with status {order.status}")
            return order

        order.status = OrderStatus.CANCELLED
        order.message = "Cancelled by user"

        logger.info(f"Order {order_id} cancelled")
        return order

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status.

        Args:
            order_id: Order ID

        Returns:
            Order response
        """
        if order_id not in self.orders:
            raise ResourceNotFoundError(
                f"Order {order_id} not found",
                details={"order_id": order_id},
            )

        return self.orders[order_id]

    async def get_market_price(self, symbol: str) -> MarketPrice:
        """Get the current market price using the market data service."""
        try:
            return await self.market_data_service.get_latest_price(symbol)
        except ValueError as exc:
            raise ValidationError(str(exc), details={"symbol": symbol}) from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to retrieve market data for %s: %s", symbol, exc)
            raise ExternalServiceError(
                f"Broker failed to fetch market data for {symbol}",
                details={"symbol": symbol},
            ) from exc

    async def get_buying_power(self) -> float:
        """Get available buying power.

        Returns:
            Available buying power
        """
        return self.current_capital
    
    async def get_positions(self) -> List[Dict]:
        """Get all current positions from simulated portfolio.
        
        For simulated broker, this requires tracking positions separately.
        Currently returns empty list as position tracking is not implemented.
        
        Returns:
            Empty list (position tracking not implemented in simulator)
        """
        logger.warning("SimulatedBroker.get_positions() not fully implemented - returns empty list")
        return []
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            None (position tracking not implemented in simulator)
        """
        logger.warning(f"SimulatedBroker.get_position({symbol}) not fully implemented - returns None")
        return None
