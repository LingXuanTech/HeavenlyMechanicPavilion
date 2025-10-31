"""统一的服务依赖注入管理."""
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import Settings, get_settings
from ..db import get_session
from ..services.alerting import AlertingService
from ..services.monitoring import MonitoringService
from ..services.broker_adapter import BrokerAdapter, SimulatedBroker
from ..services.position_sizing import PositionSizingService, PositionSizingMethod
from ..services.risk_management import RiskManagementService, RiskConstraints
from ..services.execution import ExecutionService
from ..services.trading_session import TradingSessionService


# ============= 应用级单例服务 =============

def get_alerting_service(
    settings: Settings = Depends(get_settings)
) -> AlertingService:
    """获取告警服务实例 (应用级单例).
    
    Args:
        settings: 应用配置
        
    Returns:
        AlertingService 实例
    """
    return AlertingService(settings)


def get_monitoring_service() -> MonitoringService:
    """获取监控服务实例 (应用级单例).
    
    Returns:
        MonitoringService 实例
    """
    return MonitoringService()


# ============= 会话级服务 =============

def get_broker_adapter(
    settings: Settings = Depends(get_settings),
    session_type: str = "PAPER",
    initial_capital: float = 100000.0,
) -> BrokerAdapter:
    """获取券商适配器实例 (会话级).
    
    Args:
        settings: 应用配置
        session_type: 会话类型 (PAPER/LIVE)
        initial_capital: 初始资金
        
    Returns:
        BrokerAdapter 实例
        
    Raises:
        NotImplementedError: 如果请求实盘交易但未实现
    """
    if session_type == "PAPER":
        return SimulatedBroker(
            initial_capital=initial_capital,
            commission_per_trade=0.0,
            slippage_percent=0.001,
        )
    else:
        # TODO: 实现实盘券商适配器
        raise NotImplementedError("Live trading not yet implemented")


def get_position_sizing_service(
    method: PositionSizingMethod = PositionSizingMethod.FIXED_PERCENTAGE,
) -> PositionSizingService:
    """获取仓位管理服务实例.
    
    Args:
        method: 仓位计算方法
        
    Returns:
        PositionSizingService 实例
    """
    return PositionSizingService(method=method)


def get_risk_management_service(
    max_position_weight: float = 0.20,
    max_portfolio_exposure: float = 1.0,
    default_stop_loss_pct: float = 0.10,
    default_take_profit_pct: float = 0.20,
) -> RiskManagementService:
    """获取风险管理服务实例.
    
    Args:
        max_position_weight: 最大单个持仓权重
        max_portfolio_exposure: 最大组合敞口
        default_stop_loss_pct: 默认止损百分比
        default_take_profit_pct: 默认止盈百分比
        
    Returns:
        RiskManagementService 实例
    """
    constraints = RiskConstraints(
        max_position_weight=max_position_weight,
        max_portfolio_exposure=max_portfolio_exposure,
        default_stop_loss_pct=default_stop_loss_pct,
        default_take_profit_pct=default_take_profit_pct,
    )
    return RiskManagementService(constraints=constraints)


def get_execution_service(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    position_sizing: PositionSizingService = Depends(get_position_sizing_service),
    risk_management: RiskManagementService = Depends(get_risk_management_service),
) -> ExecutionService:
    """获取执行服务实例.
    
    Args:
        broker: 券商适配器
        position_sizing: 仓位管理服务
        risk_management: 风险管理服务
        
    Returns:
        ExecutionService 实例
    """
    return ExecutionService(broker, position_sizing, risk_management)


def get_trading_session_service() -> TradingSessionService:
    """获取交易会话服务实例.
    
    Returns:
        TradingSessionService 实例
    """
    return TradingSessionService()

