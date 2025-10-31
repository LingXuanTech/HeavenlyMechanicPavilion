"""依赖注入模块 - 统一管理所有服务的依赖注入."""

from ..config import get_settings
from ..services.graph import TradingGraphService
from .services import (
    get_alerting_service,
    get_broker_adapter,
    get_execution_service,
    get_monitoring_service,
    get_position_sizing_service,
    get_risk_management_service,
    get_trading_session_service,
)


def get_graph_service() -> TradingGraphService:
    """Get the trading graph service instance.

    Returns:
        TradingGraphService instance
    """
    return TradingGraphService()


__all__ = [
    "get_settings",
    "get_alerting_service",
    "get_monitoring_service",
    "get_broker_adapter",
    "get_position_sizing_service",
    "get_risk_management_service",
    "get_execution_service",
    "get_trading_session_service",
    "get_graph_service",
]
