"""Repository layer for database access."""

from __future__ import annotations

from .agent_config import AgentConfigRepository
from .analysis_session import AnalysisSessionRepository
from .backtest import (
    BacktestArtifactRepository,
    BacktestEquityCurveRepository,
    BacktestMetricsRepository,
    BacktestRunRepository,
)
from .base import BaseRepository
from .execution import ExecutionRepository
from .portfolio import PortfolioRepository
from .position import PositionRepository
from .risk_metrics import RiskMetricsRepository
from .run_log import RunLogRepository
from .session_event import SessionEventRepository
from .trade import TradeRepository
from .trading_session import TradingSessionRepository
from .vendor_config import VendorConfigRepository

__all__ = [
    "AgentConfigRepository",
    "AnalysisSessionRepository",
    "BacktestArtifactRepository",
    "BacktestEquityCurveRepository",
    "BacktestMetricsRepository",
    "BacktestRunRepository",
    "BaseRepository",
    "ExecutionRepository",
    "PortfolioRepository",
    "PositionRepository",
    "RiskMetricsRepository",
    "RunLogRepository",
    "SessionEventRepository",
    "TradeRepository",
    "TradingSessionRepository",
    "VendorConfigRepository",
]
