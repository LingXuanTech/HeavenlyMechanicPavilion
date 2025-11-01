"""Database base configuration and utilities."""

from __future__ import annotations

from sqlmodel import SQLModel

from .models.agent_config import AgentConfig  # noqa: F401
from .models.agent_llm_config import AgentLLMConfig  # noqa: F401
from .models.agent_llm_usage import AgentLLMUsage  # noqa: F401
from .models.api_key import APIKey  # noqa: F401
from .models.audit_log import AuditLog  # noqa: F401
from .models.backtest import (  # noqa: F401
    BacktestArtifact,
    BacktestEquityCurvePoint,
    BacktestMetrics,
    BacktestRun,
)
from .models.execution import Execution  # noqa: F401
from .models.portfolio import Portfolio  # noqa: F401
from .models.position import Position  # noqa: F401
from .models.risk_metrics import RiskMetrics  # noqa: F401
from .models.run_log import RunLog  # noqa: F401
from .models.trade import Trade  # noqa: F401
from .models.trading_session import TradingSession  # noqa: F401

# Import models in dependency order to resolve relationships properly
# User must be before APIKey and AuditLog
# Trade must be before Execution
from .models.user import User  # noqa: F401
from .models.vendor_config import VendorConfig  # noqa: F401

__all__ = [
    "SQLModel",
    "Portfolio",
    "Position",
    "Trade",
    "Execution",
    "AgentConfig",
    "AgentLLMConfig",
    "AgentLLMUsage",
    "APIKey",
    "AuditLog",
    "User",
    "VendorConfig",
    "RunLog",
    "BacktestRun",
    "BacktestMetrics",
    "BacktestEquityCurvePoint",
    "BacktestArtifact",
]
