"""Execution service for converting trading signals into executed orders."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import InsufficientFundsError, ResourceNotFoundError, RiskConstraintViolation
from ..db.models import Execution, Portfolio, Position, Trade
from ..repositories import (
    ExecutionRepository,
    PortfolioRepository,
    PositionRepository,
    TradeRepository,
)
from ..schemas.execution_events import (
    ExecutionEvent,
    ExecutionEventType,
    OrderEventData,
    PositionEventData,
    RiskEventData,
    PortfolioEventData,
)
from .broker_adapter import (
    BrokerAdapter,
    OrderAction,
    OrderRequest,
    OrderStatus,
    OrderType,
)
from .events import SessionEventManager
from .position_sizing import PositionSizingService
from .risk_management import RiskManagementService

logger = logging.getLogger(__name__)


class ExecutionService:
    """Service for executing trading signals."""

    def __init__(
        self,
        broker: BrokerAdapter,
        position_sizing_service: Optional[PositionSizingService] = None,
        risk_management_service: Optional[RiskManagementService] = None,
        event_manager: Optional[SessionEventManager] = None,
    ):
        """Initialize execution service.

        Args:
            broker: Broker adapter for order execution
            position_sizing_service: Position sizing service
            risk_management_service: Risk management service
            event_manager: Event manager for real-time streaming
        """
        self.broker = broker
        self.position_sizing = position_sizing_service or PositionSizingService()
        self.risk_management = risk_management_service or RiskManagementService()
        self.event_manager = event_manager

        logger.info("Initialized ExecutionService")

    async def execute_signal(
        self,
        session: AsyncSession,
        portfolio_id: int,
        symbol: str,
        signal: str,
        current_price: float,
        decision_rationale: Optional[str] = None,
        confidence_score: Optional[float] = None,
        session_id: Optional[int] = None,
    ) -> Optional[Trade]:
        """Execute a trading signal.

        Args:
            session: Database session
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            signal: Trading signal (BUY, SELL, HOLD)
            current_price: Current market price
            decision_rationale: Rationale for the decision
            confidence_score: Confidence score (0-1)
            session_id: Trading session ID

        Returns:
            Trade record if executed, None if held
        """
        signal = signal.strip().upper()

        if signal == "HOLD":
            logger.info(f"Signal is HOLD for {symbol}, no action taken")
            return None

        if signal not in ["BUY", "SELL"]:
            logger.warning(f"Unknown signal '{signal}' for {symbol}, treating as HOLD")
            return None

        # Get portfolio and current positions
        portfolio_repo = PortfolioRepository(session)
        position_repo = PositionRepository(session)

        portfolio = await portfolio_repo.get(portfolio_id)
        if not portfolio:
            raise ResourceNotFoundError(
                f"Portfolio {portfolio_id} not found",
                details={"portfolio_id": portfolio_id},
            )

        # Get current position
        current_position = await position_repo.get_by_symbol(portfolio_id, symbol)

        # Determine order action and quantity
        if signal == "BUY":
            order_action = OrderAction.BUY

            # Calculate position size
            quantity = self.position_sizing.calculate_quantity(
                symbol=symbol,
                action="BUY",
                current_price=current_price,
                portfolio_value=portfolio.current_capital,
                confidence_score=confidence_score,
            )

            if quantity <= 0:
                logger.warning(f"Calculated quantity is {quantity}, skipping order")
                return None

        elif signal == "SELL":
            # Check if we have a position to sell
            if not current_position or current_position.quantity <= 0:
                logger.info(f"No position in {symbol} to sell")
                return None

            order_action = OrderAction.SELL
            quantity = current_position.quantity

        else:
            logger.warning(f"Unhandled signal {signal}")
            return None

        # Pre-execution risk checks
        try:
            await self._check_risk_constraints(
                session, portfolio, order_action, symbol, quantity, current_price
            )
        except (RiskConstraintViolation, InsufficientFundsError) as exc:
            logger.warning(
                "Risk check failed for %s %s: %s",
                symbol,
                order_action.value,
                exc.message,
            )
            # Publish risk check failure event
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.RISK_CHECK_FAILED
                        if isinstance(exc, RiskConstraintViolation)
                        else ExecutionEventType.INSUFFICIENT_FUNDS,
                    portfolio_id=portfolio_id,
                    session_id=str(session_id) if session_id else None,
                    risk_data=RiskEventData(
                        symbol=symbol,
                        reason=exc.message,
                        details=exc.details if hasattr(exc, 'details') else None,
                    ),
                    message=f"Risk check failed: {exc.message}",
                )
            )
            raise

        # Create order request
        order_request = OrderRequest(
            symbol=symbol,
            action=order_action,
            quantity=quantity,
            order_type=OrderType.MARKET,
            portfolio_id=portfolio_id,
            session_id=session_id,
            decision_rationale=decision_rationale,
            confidence_score=confidence_score,
        )

        # Submit order to broker
        logger.info(f"Submitting order: {order_action.value} {quantity} {symbol} @ MARKET")
        
        # Publish order submitted event
        self._publish_event(
            session_id=str(session_id) if session_id else None,
            event=ExecutionEvent(
                event_type=ExecutionEventType.ORDER_SUBMITTED,
                portfolio_id=portfolio_id,
                session_id=str(session_id) if session_id else None,
                order_data=OrderEventData(
                    symbol=symbol,
                    action=order_action.value,
                    quantity=quantity,
                    order_type=OrderType.MARKET.value,
                    status="SUBMITTED",
                ),
                message=f"Order submitted: {order_action.value} {quantity} {symbol}",
            )
        )
        
        order_response = await self.broker.submit_order(order_request)

        # Create trade record
        trade_repo = TradeRepository(session)

        trade = Trade(
            portfolio_id=portfolio_id,
            symbol=symbol,
            action=order_action.value,
            quantity=quantity,
            order_type=order_response.status.value
            if hasattr(order_response.status, "value")
            else str(order_response.status),
            status=order_response.status.value
            if hasattr(order_response.status, "value")
            else str(order_response.status),
            filled_quantity=order_response.filled_quantity,
            average_fill_price=order_response.average_fill_price,
            decision_rationale=decision_rationale,
            confidence_score=confidence_score,
            created_at=order_response.submitted_at or datetime.utcnow(),
            filled_at=order_response.filled_at,
        )

        created_trade = await trade_repo.create(trade)

        # Publish order status event
        if order_response.status == OrderStatus.FILLED:
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.ORDER_FILLED,
                    portfolio_id=portfolio_id,
                    session_id=str(session_id) if session_id else None,
                    order_data=OrderEventData(
                        symbol=symbol,
                        action=order_action.value,
                        quantity=quantity,
                        order_type=order_response.status.value,
                        status=order_response.status.value,
                        order_id=order_response.order_id,
                        filled_quantity=order_response.filled_quantity,
                        average_fill_price=order_response.average_fill_price,
                        commission=order_response.commission,
                        fees=order_response.fees,
                    ),
                    message=f"Order filled: {order_action.value} {order_response.filled_quantity} {symbol} @ ${order_response.average_fill_price:.2f}",
                )
            )
            
            await self._handle_fill(
                session,
                created_trade,
                order_response,
                portfolio,
                current_position,
                session_id=session_id,
            )
        elif order_response.status == OrderStatus.REJECTED:
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.ORDER_REJECTED,
                    portfolio_id=portfolio_id,
                    session_id=str(session_id) if session_id else None,
                    order_data=OrderEventData(
                        symbol=symbol,
                        action=order_action.value,
                        quantity=quantity,
                        order_type=order_response.status.value,
                        status=order_response.status.value,
                        reason="Order rejected by broker",
                    ),
                    message=f"Order rejected: {order_action.value} {quantity} {symbol}",
                )
            )

        await session.commit()

        logger.info(
            f"Trade executed: {order_action.value} {order_response.filled_quantity} "
            f"{symbol} @ ${order_response.average_fill_price:.2f}, "
            f"status={order_response.status.value}"
        )

        return created_trade

    async def _check_risk_constraints(
        self,
        session: AsyncSession,
        portfolio: Portfolio,
        action: OrderAction,
        symbol: str,
        quantity: float,
        price: float,
    ) -> None:
        """Check if order meets risk constraints.

        Args:
            session: Database session
            portfolio: Portfolio
            action: Order action
            symbol: Stock symbol
            quantity: Order quantity
            price: Current price

        Raises:
            InsufficientFundsError: If the portfolio lacks buying power for the order.
            RiskConstraintViolation: If the trade breaches configured risk limits.
        """
        # Check if we have enough capital for buy orders
        if action in [OrderAction.BUY, OrderAction.COVER]:
            order_value = quantity * price
            buying_power = await self.broker.get_buying_power()

            if order_value > buying_power:
                raise InsufficientFundsError(
                    "Insufficient buying power for order.",
                    details={
                        "required": round(order_value, 2),
                        "available": round(buying_power, 2),
                        "symbol": symbol,
                        "action": action.value,
                    },
                )

        # Check position size constraints
        position_repo = PositionRepository(session)
        positions = await position_repo.get_by_portfolio(portfolio.id)

        # Calculate what the position would be after this order
        current_pos = next((p for p in positions if p.symbol == symbol), None)
        current_qty = current_pos.quantity if current_pos else 0.0

        if action == OrderAction.BUY:
            new_qty = current_qty + quantity
        elif action == OrderAction.SELL:
            new_qty = current_qty - quantity
        else:
            new_qty = current_qty

        new_position_value = abs(new_qty) * price

        # Check against max position size
        max_position_value = (
            portfolio.current_capital * self.risk_management.constraints.max_position_weight
        )

        if new_position_value > max_position_value:
            raise RiskConstraintViolation(
                "Position size would exceed configured maximum.",
                details={
                    "symbol": symbol,
                    "projected_value": round(new_position_value, 2),
                    "max_allowed": round(max_position_value, 2),
                    "portfolio_id": portfolio.id,
                },
            )

        return None

    async def _handle_fill(
        self,
        session: AsyncSession,
        trade: Trade,
        order_response,
        portfolio: Portfolio,
        current_position: Optional[Position],
        session_id: Optional[int] = None,
    ):
        """Handle a filled order by creating execution and updating position.

        Args:
            session: Database session
            trade: Trade record
            order_response: Order response from broker
            portfolio: Portfolio
            current_position: Current position (if exists)
            session_id: Trading session ID for event publishing
        """
        # Create execution record
        execution_repo = ExecutionRepository(session)

        execution = Execution(
            trade_id=trade.id,
            symbol=trade.symbol,
            quantity=order_response.filled_quantity,
            price=order_response.average_fill_price,
            execution_type="FILL",
            commission=order_response.commission,
            fees=order_response.fees,
            execution_id=order_response.order_id,
            executed_at=order_response.filled_at or datetime.utcnow(),
        )

        await execution_repo.create(execution)

        # Update or create position
        position_repo = PositionRepository(session)
        position_closed = False
        position_opened = False
        updated_position = None

        if current_position:
            # Update existing position
            if trade.action == "BUY":
                new_qty = current_position.quantity + order_response.filled_quantity
                new_cost = (
                    (current_position.quantity * current_position.average_cost)
                    + (order_response.filled_quantity * order_response.average_fill_price)
                ) / new_qty

                current_position.quantity = new_qty
                current_position.average_cost = new_cost
                current_position.current_price = order_response.average_fill_price
                current_position.updated_at = datetime.utcnow()

                updated_position = await position_repo.update(current_position)

            elif trade.action == "SELL":
                # Realize P&L
                realized_pnl = order_response.filled_quantity * (
                    order_response.average_fill_price - current_position.average_cost
                )

                current_position.quantity -= order_response.filled_quantity
                current_position.realized_pnl += realized_pnl
                current_position.current_price = order_response.average_fill_price
                current_position.updated_at = datetime.utcnow()

                # Delete position if fully closed
                if current_position.quantity <= 0:
                    await position_repo.delete(current_position.id)
                    position_closed = True
                else:
                    updated_position = await position_repo.update(current_position)

        else:
            # Create new position
            if trade.action == "BUY":
                new_position = Position(
                    portfolio_id=portfolio.id,
                    symbol=trade.symbol,
                    quantity=order_response.filled_quantity,
                    average_cost=order_response.average_fill_price,
                    current_price=order_response.average_fill_price,
                    position_type="LONG",
                    entry_date=datetime.utcnow(),
                )

                updated_position = await position_repo.create(new_position)
                position_opened = True

        # Update portfolio capital
        portfolio_repo = PortfolioRepository(session)

        if trade.action == "BUY":
            portfolio.current_capital -= (
                order_response.filled_quantity * order_response.average_fill_price
                + order_response.commission
                + order_response.fees
            )
        elif trade.action == "SELL":
            portfolio.current_capital += (
                order_response.filled_quantity * order_response.average_fill_price
                - order_response.commission
                - order_response.fees
            )

        portfolio.updated_at = datetime.utcnow()
        updated_portfolio = await portfolio_repo.update(portfolio)
        
        # Publish position events
        if position_opened and updated_position:
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.POSITION_OPENED,
                    portfolio_id=portfolio.id,
                    session_id=str(session_id) if session_id else None,
                    position_data=PositionEventData(
                        symbol=updated_position.symbol,
                        quantity=updated_position.quantity,
                        average_cost=updated_position.average_cost,
                        current_price=updated_position.current_price,
                        unrealized_pnl=updated_position.unrealized_pnl,
                        position_type=updated_position.position_type,
                    ),
                    message=f"Position opened: {updated_position.symbol} ({updated_position.quantity} shares)",
                )
            )
        elif position_closed:
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.POSITION_CLOSED,
                    portfolio_id=portfolio.id,
                    session_id=str(session_id) if session_id else None,
                    position_data=PositionEventData(
                        symbol=trade.symbol,
                        quantity=0,
                        average_cost=current_position.average_cost,
                        current_price=order_response.average_fill_price,
                        unrealized_pnl=0,
                        realized_pnl=current_position.realized_pnl,
                        position_type=current_position.position_type,
                    ),
                    message=f"Position closed: {trade.symbol}",
                )
            )
        elif updated_position:
            self._publish_event(
                session_id=str(session_id) if session_id else None,
                event=ExecutionEvent(
                    event_type=ExecutionEventType.POSITION_UPDATED,
                    portfolio_id=portfolio.id,
                    session_id=str(session_id) if session_id else None,
                    position_data=PositionEventData(
                        symbol=updated_position.symbol,
                        quantity=updated_position.quantity,
                        average_cost=updated_position.average_cost,
                        current_price=updated_position.current_price,
                        unrealized_pnl=updated_position.unrealized_pnl,
                        realized_pnl=updated_position.realized_pnl,
                        position_type=updated_position.position_type,
                    ),
                    message=f"Position updated: {updated_position.symbol} ({updated_position.quantity} shares)",
                )
            )
        
        # Publish portfolio update event
        positions_count = len(await position_repo.get_by_portfolio(portfolio.id))
        total_positions_value = sum(
            p.quantity * p.current_price
            for p in await position_repo.get_by_portfolio(portfolio.id)
        )
        
        self._publish_event(
            session_id=str(session_id) if session_id else None,
            event=ExecutionEvent(
                event_type=ExecutionEventType.PORTFOLIO_UPDATED,
                portfolio_id=portfolio.id,
                session_id=str(session_id) if session_id else None,
                portfolio_data=PortfolioEventData(
                    portfolio_id=portfolio.id,
                    current_capital=portfolio.current_capital,
                    total_value=portfolio.current_capital + total_positions_value,
                    unrealized_pnl=sum(p.unrealized_pnl for p in await position_repo.get_by_portfolio(portfolio.id)),
                    realized_pnl=sum(p.realized_pnl for p in await position_repo.get_by_portfolio(portfolio.id)),
                    positions_count=positions_count,
                ),
                message=f"Portfolio updated: ${portfolio.current_capital:.2f} cash, {positions_count} positions",
            )
        )

    async def force_exit_position(
        self,
        session: AsyncSession,
        portfolio_id: int,
        symbol: str,
        reason: str = "Force exit",
    ) -> Optional[Trade]:
        """Force exit a position.

        Args:
            session: Database session
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            reason: Reason for exit

        Returns:
            Trade record if executed
        """
        logger.info(f"Force exiting position in {symbol}: {reason}")

        # Get current market price
        market_price = await self.broker.get_market_price(symbol)

        return await self.execute_signal(
            session=session,
            portfolio_id=portfolio_id,
            symbol=symbol,
            signal="SELL",
            current_price=market_price.last,
            decision_rationale=reason,
        )

    async def check_stop_loss_take_profit(
        self,
        session: AsyncSession,
        portfolio_id: int,
    ) -> List[Trade]:
        """Check all positions for stop loss and take profit triggers.

        Args:
            session: Database session
            portfolio_id: Portfolio ID

        Returns:
            List of trades executed due to stop loss / take profit
        """
        position_repo = PositionRepository(session)
        positions = await position_repo.get_by_portfolio(portfolio_id)

        executed_trades = []

        for position in positions:
            if position.quantity == 0:
                continue

            # Get current market price
            market_price = await self.broker.get_market_price(position.symbol)
            current_price = market_price.last

            # Update position price
            position.current_price = current_price
            position.unrealized_pnl = position.quantity * (current_price - position.average_cost)
            await position_repo.update(position)

            # Check stop loss
            if self.risk_management.check_stop_loss(position, current_price):
                # Publish stop loss event
                self._publish_event(
                    session_id=None,
                    event=ExecutionEvent(
                        event_type=ExecutionEventType.STOP_LOSS_TRIGGERED,
                        portfolio_id=portfolio_id,
                        risk_data=RiskEventData(
                            symbol=position.symbol,
                            reason="Stop loss triggered",
                            current_price=current_price,
                            stop_loss_price=position.average_cost * (1 - self.risk_management.constraints.stop_loss_pct),
                        ),
                        message=f"Stop loss triggered for {position.symbol}",
                    )
                )
                
                trade = await self.force_exit_position(
                    session, portfolio_id, position.symbol, "Stop loss triggered"
                )
                if trade:
                    executed_trades.append(trade)
                continue

            # Check take profit
            if self.risk_management.check_take_profit(position, current_price):
                # Publish take profit event
                self._publish_event(
                    session_id=None,
                    event=ExecutionEvent(
                        event_type=ExecutionEventType.TAKE_PROFIT_TRIGGERED,
                        portfolio_id=portfolio_id,
                        risk_data=RiskEventData(
                            symbol=position.symbol,
                            reason="Take profit triggered",
                            current_price=current_price,
                            take_profit_price=position.average_cost * (1 + self.risk_management.constraints.take_profit_pct),
                        ),
                        message=f"Take profit triggered for {position.symbol}",
                    )
                )
                
                trade = await self.force_exit_position(
                    session, portfolio_id, position.symbol, "Take profit triggered"
                )
                if trade:
                    executed_trades.append(trade)

        if executed_trades:
            await session.commit()

        return executed_trades
    
    def _publish_event(self, session_id: Optional[str], event: ExecutionEvent) -> None:
        """Publish an execution event to the session stream.
        
        Args:
            session_id: Session ID to publish to
            event: Event to publish
        """
        if not self.event_manager or not session_id:
            return
            
        try:
            self.event_manager.publish(
                session_id,
                event.model_dump(mode='json')
            )
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")
