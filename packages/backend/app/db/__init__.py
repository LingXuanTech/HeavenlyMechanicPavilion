"""Database package for TradingAgents."""

from __future__ import annotations

from .base import (
    AgentConfig,
    Execution,
    Portfolio,
    Position,
    RunLog,
    SQLModel,
    Trade,
    VendorConfig,
)
from .session import DatabaseManager, get_db_manager, get_session, init_db

# Alias for compatibility
get_db = get_session

__all__ = [
    "AgentConfig",
    "DatabaseManager",
    "Execution",
    "Portfolio",
    "Position",
    "RunLog",
    "SQLModel",
    "Trade",
    "VendorConfig",
    "get_db",
    "get_db_manager",
    "get_session",
    "init_db",
]
