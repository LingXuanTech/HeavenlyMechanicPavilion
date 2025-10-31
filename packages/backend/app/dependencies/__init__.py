"""依赖注入模块 - 统一管理所有服务的依赖注入."""

from .services import (
    get_alerting_service,
    get_monitoring_service,
    get_broker_adapter,
    get_position_sizing_service,
    get_risk_management_service,
    get_execution_service,
    get_trading_session_service,
)

__all__ = [
    "get_alerting_service",
    "get_monitoring_service",
    "get_broker_adapter",
    "get_position_sizing_service",
    "get_risk_management_service",
    "get_execution_service",
    "get_trading_session_service",
]
