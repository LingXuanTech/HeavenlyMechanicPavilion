"""Trading and execution API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import TradingAgentsError
from ..db import get_db
from ..db.models import User, UserRole
from ..repositories import PortfolioRepository, PositionRepository
from ..schemas.trading import (
    ExecuteSignalRequest,
    ForceExitRequest,
    PortfolioStateDetailResponse,
    PortfolioStateResponse,
    PositionResponse,
    RiskDiagnosticsResponse,
    StartSessionRequest,
    TradeResponse,
    TradingSessionResponse,
)
from ..security.dependencies import get_current_active_user, require_role
from ..services import (
    PositionSizingMethod,
    TradingSessionService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])

# Global trading session service
trading_session_service = TradingSessionService()


@router.post("/sessions/start", response_model=TradingSessionResponse)
async def start_trading_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> TradingSessionResponse:
    """Start a new trading session."""
    try:
        # Parse position sizing method
        try:
            sizing_method = PositionSizingMethod(request.position_sizing_method)
        except ValueError:
            sizing_method = PositionSizingMethod.FIXED_PERCENTAGE

        session = await trading_session_service.start_session(
            session=db,
            portfolio_id=request.portfolio_id,
            session_type=request.session_type,
            name=request.name,
            description=request.description,
            max_position_size=request.max_position_size,
            max_portfolio_exposure=request.max_portfolio_exposure,
            stop_loss_percentage=request.stop_loss_percentage,
            take_profit_percentage=request.take_profit_percentage,
            position_sizing_method=sizing_method,
        )

        return TradingSessionResponse.model_validate(session)

    except TradingAgentsError as exc:
        raise exc
    except ValueError as e:
        logger.error(f"Validation error starting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error starting trading session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start trading session",
        )


@router.post("/sessions/{session_id}/stop", response_model=TradingSessionResponse)
async def stop_trading_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> TradingSessionResponse:
    """Stop a trading session."""
    try:
        session = await trading_session_service.stop_session(
            session=db,
            session_id=session_id,
        )

        return TradingSessionResponse.model_validate(session)

    except TradingAgentsError as exc:
        raise exc
    except ValueError as e:
        logger.error(f"Validation error stopping session: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error stopping trading session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop trading session",
        )


@router.post("/execute", response_model=TradeResponse | None)
async def execute_signal(
    request: ExecuteSignalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> TradeResponse | None:
    """Execute a trading signal."""
    try:
        # Get execution service
        execution_service = None

        if request.session_id:
            execution_service = trading_session_service.get_execution_service(request.session_id)

        if not execution_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found or session_id not provided",
            )

        # Execute signal
        trade = await execution_service.execute_signal(
            session=db,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            signal=request.signal,
            current_price=request.current_price,
            decision_rationale=request.decision_rationale,
            confidence_score=request.confidence_score,
            session_id=request.session_id,
        )

        if trade is None:
            return None

        return TradeResponse.model_validate(trade)

    except HTTPException:
        raise
    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute signal",
        )


@router.post("/positions/exit", response_model=TradeResponse | None)
async def force_exit_position(
    request: ForceExitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> TradeResponse | None:
    """Force exit a position."""
    try:
        # Find an active session for the portfolio
        # In a real implementation, you might want to specify the session
        execution_service = None

        for session_id, session_data in trading_session_service.active_sessions.items():
            session_obj = session_data["session"]
            if session_obj.portfolio_id == request.portfolio_id:
                execution_service = session_data["execution_service"]
                break

        if not execution_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found for portfolio",
            )

        # Force exit
        trade = await execution_service.force_exit_position(
            session=db,
            portfolio_id=request.portfolio_id,
            symbol=request.symbol,
            reason=request.reason,
        )

        if trade is None:
            return None

        return TradeResponse.model_validate(trade)

    except HTTPException:
        raise
    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"Error forcing exit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to force exit position",
        )


@router.get("/risk/diagnostics/{portfolio_id}", response_model=RiskDiagnosticsResponse)
async def get_risk_diagnostics(
    portfolio_id: int,
    session_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RiskDiagnosticsResponse:
    """Get risk diagnostics for a portfolio."""
    try:
        # Calculate and store risk metrics
        risk_metrics = await trading_session_service.calculate_and_store_risk_metrics(
            session=db,
            portfolio_id=portfolio_id,
            session_id=session_id,
        )

        # Get risk management service
        risk_service = None
        if session_id:
            risk_service = trading_session_service.get_risk_management_service(session_id)

        # Get positions for warnings
        position_repo = PositionRepository(db)
        positions = await position_repo.get_by_portfolio(portfolio_id)

        current_prices = {pos.symbol: pos.current_price for pos in positions}

        if risk_service:
            diagnostics = await risk_service.calculate_diagnostics(
                portfolio_id=portfolio_id,
                positions=positions,
                current_prices=current_prices,
            )
            warnings = diagnostics.warnings
        else:
            warnings = []

        return RiskDiagnosticsResponse(
            portfolio_id=risk_metrics.portfolio_id,
            portfolio_value=risk_metrics.portfolio_value,
            var_1day_95=risk_metrics.var_1day_95,
            var_1day_99=risk_metrics.var_1day_99,
            var_5day_95=risk_metrics.var_5day_95,
            var_5day_99=risk_metrics.var_5day_99,
            portfolio_volatility=risk_metrics.portfolio_volatility,
            sharpe_ratio=risk_metrics.sharpe_ratio,
            max_drawdown=risk_metrics.max_drawdown,
            largest_position_weight=risk_metrics.largest_position_weight,
            top5_concentration=risk_metrics.top5_concentration,
            number_of_positions=risk_metrics.number_of_positions,
            total_exposure=risk_metrics.total_exposure,
            long_exposure=risk_metrics.long_exposure,
            short_exposure=risk_metrics.short_exposure,
            net_exposure=risk_metrics.net_exposure,
            warnings=warnings,
            measured_at=risk_metrics.measured_at,
        )

    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"Error getting risk diagnostics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get risk diagnostics",
        )


@router.get("/portfolio/{portfolio_id}/state", response_model=PortfolioStateDetailResponse)
async def get_portfolio_state(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioStateDetailResponse:
    """Get current portfolio state including all positions."""
    try:
        # Get portfolio
        portfolio_repo = PortfolioRepository(db)
        portfolio = await portfolio_repo.get(portfolio_id)

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )

        # Get positions
        position_repo = PositionRepository(db)
        positions = await position_repo.get_by_portfolio(portfolio_id)

        # Calculate totals
        total_value = portfolio.current_capital
        total_unrealized_pnl = 0.0
        total_realized_pnl = 0.0

        for pos in positions:
            if pos.quantity != 0:
                total_value += pos.quantity * pos.current_price
                total_unrealized_pnl += pos.unrealized_pnl
                total_realized_pnl += pos.realized_pnl

        return PortfolioStateDetailResponse(
            portfolio=PortfolioStateResponse.model_validate(portfolio),
            positions=[PositionResponse.model_validate(pos) for pos in positions],
            total_value=total_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_realized_pnl=total_realized_pnl,
        )

    except HTTPException:
        raise
    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"Error getting portfolio state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portfolio state",
        )


@router.get("/broker/positions")
async def get_broker_positions(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> list[dict]:
    """从券商直接获取所有持仓（实时数据）.
    
    此端点绕过数据库，直接从券商 API 获取当前持仓状态。
    用于验证数据库持仓记录的准确性或获取最新状态。
    
    Args:
        session_id: 交易会话ID
        
    Returns:
        持仓列表，每个持仓包含：
        - symbol: 股票代码
        - quantity: 持仓数量
        - average_cost: 平均成本
        - current_price: 当前价格
        - market_value: 市值
        - unrealized_pnl: 未实现盈亏
        - unrealized_pnl_percent: 未实现盈亏百分比
        - position_type: 持仓类型 (LONG/SHORT)
    """
    try:
        # 获取执行服务
        execution_service = trading_session_service.get_execution_service(session_id)
        
        if not execution_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading session {session_id} not found or not active",
            )
        
        # 直接从券商查询持仓
        positions = await execution_service.broker.get_positions()
        
        logger.info(f"从券商获取到 {len(positions)} 个持仓 (session {session_id})")
        return positions
        
    except HTTPException:
        raise
    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"从券商获取持仓失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法从券商获取持仓: {str(e)}",
        )


@router.get("/broker/positions/{symbol}")
async def get_broker_position(
    symbol: str,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
) -> dict | None:
    """从券商直接获取指定股票的持仓（实时数据）.
    
    Args:
        symbol: 股票代码
        session_id: 交易会话ID
        
    Returns:
        持仓信息或 None（如果没有持仓）
        字段说明同 get_broker_positions()
    """
    try:
        # 获取执行服务
        execution_service = trading_session_service.get_execution_service(session_id)
        
        if not execution_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading session {session_id} not found or not active",
            )
        
        # 直接从券商查询持仓
        position = await execution_service.broker.get_position(symbol)
        
        if position:
            logger.info(f"从券商获取到 {symbol} 的持仓 (session {session_id})")
        else:
            logger.info(f"券商无 {symbol} 的持仓 (session {session_id})")
            
        return position
        
    except HTTPException:
        raise
    except TradingAgentsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"从券商获取持仓失败 ({symbol}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法从券商获取持仓: {str(e)}",
        )
