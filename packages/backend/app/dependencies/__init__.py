"""依赖注入模块 - 统一管理所有服务的依赖注入."""

from ..config import get_settings
from ..services.events import SessionEventManager
from ..services.graph import TradingGraphService
from .services import (
    get_alerting_service,
    get_broker_adapter,
    get_execution_service,
    get_market_data_service,
    get_monitoring_service,
    get_position_sizing_service,
    get_risk_management_service,
    get_trading_session_service,
)

# Global singleton event manager for session streaming and event buffering
_event_manager: SessionEventManager | None = None


def get_event_manager() -> SessionEventManager:
    """Get the global session event manager singleton.

    Returns:
        SessionEventManager instance
    """
    global _event_manager
    if _event_manager is None:
        _event_manager = SessionEventManager()
    return _event_manager


def get_graph_service() -> TradingGraphService:
    """Get the trading graph service instance.

    Returns:
        TradingGraphService instance
    """
    return TradingGraphService(event_manager=get_event_manager())


__all__ = [
    "get_settings",
    "get_alerting_service",
    "get_monitoring_service",
    "get_broker_adapter",
    "get_position_sizing_service",
    "get_risk_management_service",
    "get_execution_service",
    "get_trading_session_service",
    "get_event_manager",
    "get_market_data_service",
    "get_graph_service",
]
