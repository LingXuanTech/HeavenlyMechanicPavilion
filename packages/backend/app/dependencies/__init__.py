"""Application dependency wiring for FastAPI."""

from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import CacheService, RedisManager, get_redis_manager
from ..config import Settings
from ..db import get_db_manager
from ..services import BacktestService
from ..services.events import SessionEventManager
from ..services.graph import TradingGraphService

# Global instances
_settings = Settings()
_event_manager = SessionEventManager()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return _settings


def get_event_manager() -> SessionEventManager:
    """Get the global event manager instance."""
    return _event_manager


@lru_cache
def get_graph_service() -> TradingGraphService:
    """Get the TradingGraphService singleton."""
    return TradingGraphService(
        event_manager=_event_manager,
        config_overrides=_settings.config_overrides(),
    )


@lru_cache
def get_backtest_service() -> BacktestService:
    """Get the BacktestService singleton."""
    return BacktestService(config_overrides=_settings.config_overrides())


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session.
    
    Yields:
        AsyncSession: A database session
    """
    db_manager = get_db_manager()
    async for session in db_manager.get_session():
        yield session


def get_cache_service() -> Optional[CacheService]:
    """Get the cache service if Redis is enabled.
    
    Returns:
        CacheService or None if Redis is not enabled
    """
    if not _settings.redis_enabled:
        return None
    
    redis_manager = get_redis_manager()
    if redis_manager is None:
        return None
    
    return CacheService(redis_manager)


# Backward compatibility alias
BackendSettings = Settings
