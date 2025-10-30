"""Database base configuration and utilities."""

from __future__ import annotations

from sqlmodel import SQLModel

# Import all models here to ensure they are registered with SQLModel
# This is needed for Alembic to detect all models
from .models.portfolio import Portfolio  # noqa: F401
from .models.position import Position  # noqa: F401
from .models.trade import Trade  # noqa: F401
from .models.execution import Execution  # noqa: F401
from .models.agent_config import AgentConfig  # noqa: F401
from .models.agent_llm_config import AgentLLMConfig  # noqa: F401
from .models.vendor_config import VendorConfig  # noqa: F401
from .models.run_log import RunLog  # noqa: F401
from .models.backtest import (  # noqa: F401
    BacktestArtifact,
    BacktestEquityCurvePoint,
    BacktestMetrics,
    BacktestRun,
)

__all__ = [
    "SQLModel",
    "Portfolio",
    "Position",
    "Trade",
    "Execution",
    "AgentConfig",
    "AgentLLMConfig",
    "VendorConfig",
    "RunLog",
    "BacktestRun",
    "BacktestMetrics",
    "BacktestEquityCurvePoint",
    "BacktestArtifact",
]
