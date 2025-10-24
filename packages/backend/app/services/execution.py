"""Execution service for converting trading signals into executed orders."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Execution, Portfolio, Position, Trade
from ..repositories import (
    ExecutionRepository,
    PortfolioRepository,
    PositionRepository,
    TradeRepository,
)
from .broker_adapter import (
    BrokerAdapter,
    OrderAction,
    OrderRequest,
    OrderStatus,
    OrderType,
)
from .position_sizing import PositionSizingMethod, PositionSizingService
from .risk_management import RiskConstraints, RiskManagementService

logger = logging.getLogger(__name__)


class ExecutionService:
    """Service for executing trading signals."""
    
    def __init__(
        self,
        broker: BrokerAdapter,
        position_sizing_service: Optional[PositionSizingService] = None,
        risk_management_service: Optional[RiskManagementService] = None,
    ):
        """Initialize execution service.
        
        Args:
            broker: Broker adapter for order execution
            position_sizing_service: Position sizing service
            risk_management_service: Risk management service
        """
        self.broker = broker
        self.position_sizing = position_sizing_service or PositionSizingService()
        self.risk_management = risk_management_service or RiskManagementService()
        
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
            logger.error(f"Portfolio {portfolio_id} not found")
            return None
        
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
        risk_check_passed = await self._check_risk_constraints(
            session, portfolio, order_action, symbol, quantity, current_price
        )
        
        if not risk_check_passed:
            logger.warning(f"Risk check failed for {symbol} {order_action.value}")
            return None
        
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
        logger.info(
            f"Submitting order: {order_action.value} {quantity} {symbol} @ MARKET"
        )
        order_response = await self.broker.submit_order(order_request)
        
        # Create trade record
        trade_repo = TradeRepository(session)
        
        trade = Trade(
            portfolio_id=portfolio_id,
            symbol=symbol,
            action=order_action.value,
            quantity=quantity,
            order_type=order_response.status.value if hasattr(order_response.status, 'value') else str(order_response.status),
            status=order_response.status.value if hasattr(order_response.status, 'value') else str(order_response.status),
            filled_quantity=order_response.filled_quantity,
            average_fill_price=order_response.average_fill_price,
            decision_rationale=decision_rationale,
            confidence_score=confidence_score,
            created_at=order_response.submitted_at or datetime.utcnow(),
            filled_at=order_response.filled_at,
        )
        
        created_trade = await trade_repo.create(trade)
        
        # If filled, create execution record and update position
        if order_response.status == OrderStatus.FILLED:
            await self._handle_fill(
                session,
                created_trade,
                order_response,
                portfolio,
                current_position,
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
    ) -> bool:
        """Check if order meets risk constraints.
        
        Args:
            session: Database session
            portfolio: Portfolio
            action: Order action
            symbol: Stock symbol
            quantity: Order quantity
            price: Current price
            
        Returns:
            True if constraints are met, False otherwise
        """
        # Check if we have enough capital for buy orders
        if action in [OrderAction.BUY, OrderAction.COVER]:
            order_value = quantity * price
            buying_power = await self.broker.get_buying_power()
            
            if order_value > buying_power:
                logger.warning(
                    f"Insufficient buying power: need ${order_value:,.2f}, "
                    f"have ${buying_power:,.2f}"
                )
                return False
        
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
            portfolio.current_capital
            * self.risk_management.constraints.max_position_weight
        )
        
        if new_position_value > max_position_value:
            logger.warning(
                f"Position size ${new_position_value:,.0f} would exceed maximum "
                f"${max_position_value:,.0f}"
            )
            return False
        
        return True
    
    async def _handle_fill(
        self,
        session: AsyncSession,
        trade: Trade,
        order_response,
        portfolio: Portfolio,
        current_position: Optional[Position],
    ):
        """Handle a filled order by creating execution and updating position.
        
        Args:
            session: Database session
            trade: Trade record
            order_response: Order response from broker
            portfolio: Portfolio
            current_position: Current position (if exists)
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
                
                await position_repo.update(current_position)
                
            elif trade.action == "SELL":
                # Realize P&L
                realized_pnl = (
                    order_response.filled_quantity
                    * (order_response.average_fill_price - current_position.average_cost)
                )
                
                current_position.quantity -= order_response.filled_quantity
                current_position.realized_pnl += realized_pnl
                current_position.current_price = order_response.average_fill_price
                current_position.updated_at = datetime.utcnow()
                
                # Delete position if fully closed
                if current_position.quantity <= 0:
                    await position_repo.delete(current_position.id)
                else:
                    await position_repo.update(current_position)
        
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
                
                await position_repo.create(new_position)
        
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
        await portfolio_repo.update(portfolio)
    
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
            position.unrealized_pnl = (
                position.quantity * (current_price - position.average_cost)
            )
            await position_repo.update(position)
            
            # Check stop loss
            if self.risk_management.check_stop_loss(position, current_price):
                trade = await self.force_exit_position(
                    session, portfolio_id, position.symbol, "Stop loss triggered"
                )
                if trade:
                    executed_trades.append(trade)
                continue
            
            # Check take profit
            if self.risk_management.check_take_profit(position, current_price):
                trade = await self.force_exit_position(
                    session, portfolio_id, position.symbol, "Take profit triggered"
                )
                if trade:
                    executed_trades.append(trade)
        
        if executed_trades:
            await session.commit()
        
        return executed_trades
