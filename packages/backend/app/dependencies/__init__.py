"""依赖注入模块 - 统一管理所有服务的依赖注入."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.session import get_db_manager
from ..services.events_enhanced import EnhancedSessionEventManager
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
_event_manager: EnhancedSessionEventManager | None = None


@asynccontextmanager
async def get_db_session_factory() -> AsyncGenerator[AsyncSession, None]:
    """Database session factory for EnhancedSessionEventManager.

    Yields:
        AsyncSession: A database session
    """
    db_manager = get_db_manager()
    async with db_manager.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_event_manager() -> EnhancedSessionEventManager:
    """Get the global enhanced session event manager singleton.

    Returns:
        EnhancedSessionEventManager instance with database persistence
    """
    global _event_manager
    if _event_manager is None:
        settings = get_settings()
        _event_manager = EnhancedSessionEventManager(
            db_session_factory=get_db_session_factory,
            max_buffer_size=getattr(settings, 'event_buffer_size', 100),
            persist_to_db=getattr(settings, 'event_persistence_enabled', True),
        )
    return _event_manager


def get_graph_service() -> TradingGraphService:
    """Get the trading graph service instance.

    Returns:
        TradingGraphService instance
    """
    return TradingGraphService(
        event_manager=get_event_manager(),
        db_manager=get_db_manager(),
    )


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
