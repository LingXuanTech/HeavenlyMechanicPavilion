"""Database models for the TradingAgents application."""

from __future__ import annotations

from .agent_config import AgentConfig
from .agent_llm_config import AgentLLMConfig
from .agent_llm_usage import AgentLLMUsage
from .analysis_session import AnalysisSession
from .api_key import APIKey
from .audit_log import AuditLog
from .backtest import (
    BacktestArtifact,
    BacktestEquityCurvePoint,
    BacktestMetrics,
    BacktestRun,
)
from .execution import Execution
from .portfolio import Portfolio
from .position import Position
from .risk_metrics import RiskMetrics
from .run_log import RunLog
from .trade import Trade
from .trading_session import TradingSession

# Import models in dependency order to avoid relationship resolution issues
from .user import User, UserRole
from .vendor_config import VendorConfig

__all__ = [
    "AgentConfig",
    "AgentLLMConfig",
    "AgentLLMUsage",
    "AnalysisSession",
    "APIKey",
    "AuditLog",
    "Execution",
    "Portfolio",
    "Position",
    "RiskMetrics",
    "RunLog",
    "Trade",
    "TradingSession",
    "User",
    "UserRole",
    "VendorConfig",
    "BacktestRun",
    "BacktestMetrics",
    "BacktestEquityCurvePoint",
    "BacktestArtifact",
]
