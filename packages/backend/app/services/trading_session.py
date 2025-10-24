"""Trading session service for managing live and paper trading sessions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Portfolio, RiskMetrics, TradingSession
from ..repositories import (
    PortfolioRepository,
    PositionRepository,
    RiskMetricsRepository,
    TradingSessionRepository,
)
from .broker_adapter import BrokerAdapter, SimulatedBroker
from .execution import ExecutionService
from .position_sizing import PositionSizingMethod, PositionSizingService
from .risk_management import RiskConstraints, RiskManagementService

logger = logging.getLogger(__name__)


class TradingSessionService:
    """Service for managing trading sessions."""
    
    def __init__(self):
        """Initialize trading session service."""
        self.active_sessions = {}
        logger.info("Initialized TradingSessionService")
    
    async def start_session(
        self,
        session: AsyncSession,
        portfolio_id: int,
        session_type: str = "PAPER",
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_position_size: Optional[float] = None,
        max_portfolio_exposure: Optional[float] = None,
        stop_loss_percentage: Optional[float] = None,
        take_profit_percentage: Optional[float] = None,
        position_sizing_method: PositionSizingMethod = PositionSizingMethod.FIXED_PERCENTAGE,
    ) -> TradingSession:
        """Start a new trading session.
        
        Args:
            session: Database session
            portfolio_id: Portfolio ID
            session_type: Session type (PAPER or LIVE)
            name: Session name
            description: Session description
            max_position_size: Max position size as percentage
            max_portfolio_exposure: Max portfolio exposure
            stop_loss_percentage: Stop loss percentage
            take_profit_percentage: Take profit percentage
            position_sizing_method: Position sizing method
            
        Returns:
            Created trading session
        """
        # Get portfolio
        portfolio_repo = PortfolioRepository(session)
        portfolio = await portfolio_repo.get(portfolio_id)
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Create risk constraints
        constraints = RiskConstraints(
            max_position_weight=max_position_size or 0.20,
            max_portfolio_exposure=max_portfolio_exposure or 1.0,
            default_stop_loss_pct=stop_loss_percentage or 0.10,
            default_take_profit_pct=take_profit_percentage or 0.20,
        )
        
        # Create broker adapter
        if session_type == "PAPER":
            broker = SimulatedBroker(
                initial_capital=portfolio.current_capital,
                commission_per_trade=0.0,
                slippage_percent=0.001,
            )
        else:
            # TODO: Implement live broker adapter
            raise NotImplementedError("Live trading not yet implemented")
        
        # Create services
        position_sizing = PositionSizingService(method=position_sizing_method)
        risk_management = RiskManagementService(constraints=constraints)
        execution_service = ExecutionService(broker, position_sizing, risk_management)
        
        # Create session record
        session_repo = TradingSessionRepository(session)
        
        trading_session = TradingSession(
            portfolio_id=portfolio_id,
            session_type=session_type,
            status="ACTIVE",
            name=name or f"{session_type} Session {datetime.utcnow().isoformat()}",
            description=description,
            max_position_size=max_position_size,
            max_portfolio_exposure=max_portfolio_exposure,
            stop_loss_percentage=stop_loss_percentage,
            take_profit_percentage=take_profit_percentage,
            starting_capital=portfolio.current_capital,
            current_capital=portfolio.current_capital,
        )
        
        created_session = await session_repo.create(trading_session)
        await session.commit()
        
        # Store active session
        self.active_sessions[created_session.id] = {
            "session": created_session,
            "broker": broker,
            "execution_service": execution_service,
            "risk_management": risk_management,
        }
        
        logger.info(
            f"Started {session_type} trading session {created_session.id} "
            f"for portfolio {portfolio_id}"
        )
        
        return created_session
    
    async def stop_session(
        self,
        session: AsyncSession,
        session_id: int,
    ) -> TradingSession:
        """Stop a trading session.
        
        Args:
            session: Database session
            session_id: Trading session ID
            
        Returns:
            Updated trading session
        """
        session_repo = TradingSessionRepository(session)
        trading_session = await session_repo.get(session_id)
        
        if not trading_session:
            raise ValueError(f"Trading session {session_id} not found")
        
        if trading_session.status != "ACTIVE":
            logger.warning(f"Session {session_id} is not active")
            return trading_session
        
        # Update session status
        trading_session.status = "STOPPED"
        trading_session.stopped_at = datetime.utcnow()
        
        # Calculate final metrics
        portfolio_repo = PortfolioRepository(session)
        portfolio = await portfolio_repo.get(trading_session.portfolio_id)
        
        if portfolio:
            trading_session.current_capital = portfolio.current_capital
            trading_session.total_pnl = (
                portfolio.current_capital - trading_session.starting_capital
            )
        
        await session_repo.update(trading_session)
        await session.commit()
        
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        logger.info(f"Stopped trading session {session_id}")
        
        return trading_session
    
    def get_execution_service(
        self, session_id: int
    ) -> Optional[ExecutionService]:
        """Get execution service for an active session.
        
        Args:
            session_id: Trading session ID
            
        Returns:
            Execution service if session is active
        """
        if session_id not in self.active_sessions:
            return None
        
        return self.active_sessions[session_id]["execution_service"]
    
    def get_risk_management_service(
        self, session_id: int
    ) -> Optional[RiskManagementService]:
        """Get risk management service for an active session.
        
        Args:
            session_id: Trading session ID
            
        Returns:
            Risk management service if session is active
        """
        if session_id not in self.active_sessions:
            return None
        
        return self.active_sessions[session_id]["risk_management"]
    
    async def update_session_metrics(
        self,
        session: AsyncSession,
        session_id: int,
    ) -> TradingSession:
        """Update trading session metrics.
        
        Args:
            session: Database session
            session_id: Trading session ID
            
        Returns:
            Updated trading session
        """
        session_repo = TradingSessionRepository(session)
        trading_session = await session_repo.get(session_id)
        
        if not trading_session:
            raise ValueError(f"Trading session {session_id} not found")
        
        # Get portfolio
        portfolio_repo = PortfolioRepository(session)
        portfolio = await portfolio_repo.get(trading_session.portfolio_id)
        
        if not portfolio:
            return trading_session
        
        # Update capital and P&L
        trading_session.current_capital = portfolio.current_capital
        trading_session.total_pnl = (
            portfolio.current_capital - trading_session.starting_capital
        )
        
        # Update trade counts (would need to query trades table)
        # For now, leave as is
        
        await session_repo.update(trading_session)
        await session.commit()
        
        return trading_session
    
    async def calculate_and_store_risk_metrics(
        self,
        session: AsyncSession,
        portfolio_id: int,
        session_id: Optional[int] = None,
    ) -> RiskMetrics:
        """Calculate and store risk metrics.
        
        Args:
            session: Database session
            portfolio_id: Portfolio ID
            session_id: Trading session ID (optional)
            
        Returns:
            Created risk metrics
        """
        # Get risk management service
        risk_service = None
        if session_id and session_id in self.active_sessions:
            risk_service = self.active_sessions[session_id]["risk_management"]
        else:
            risk_service = RiskManagementService()
        
        # Get positions
        position_repo = PositionRepository(session)
        positions = await position_repo.get_by_portfolio(portfolio_id)
        
        # Get current prices (would need market data service)
        current_prices = {}
        for pos in positions:
            current_prices[pos.symbol] = pos.current_price
        
        # Calculate diagnostics
        diagnostics = await risk_service.calculate_diagnostics(
            portfolio_id=portfolio_id,
            positions=positions,
            current_prices=current_prices,
        )
        
        # Store risk metrics
        risk_metrics_repo = RiskMetricsRepository(session)
        
        risk_metrics = RiskMetrics(
            portfolio_id=portfolio_id,
            session_id=session_id,
            var_1day_95=diagnostics.var_1day_95,
            var_1day_99=diagnostics.var_1day_99,
            var_5day_95=diagnostics.var_5day_95,
            var_5day_99=diagnostics.var_5day_99,
            portfolio_value=diagnostics.portfolio_value,
            portfolio_volatility=diagnostics.portfolio_volatility,
            sharpe_ratio=diagnostics.sharpe_ratio,
            max_drawdown=diagnostics.max_drawdown,
            largest_position_weight=diagnostics.largest_position_weight,
            top5_concentration=diagnostics.top5_concentration,
            number_of_positions=diagnostics.number_of_positions,
            total_exposure=diagnostics.total_exposure,
            long_exposure=diagnostics.long_exposure,
            short_exposure=diagnostics.short_exposure,
            net_exposure=diagnostics.net_exposure,
        )
        
        created_metrics = await risk_metrics_repo.create(risk_metrics)
        await session.commit()
        
        logger.info(f"Calculated and stored risk metrics for portfolio {portfolio_id}")
        
        return created_metrics
