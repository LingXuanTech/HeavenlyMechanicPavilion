"""Pydantic schemas for backtesting endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class BacktestParameters(BaseModel):
    """Parameters controlling a backtest run."""

    symbols: List[str] = Field(..., min_length=1, description="List of symbols to backtest")
    start_date: date = Field(..., description="Inclusive start date for the replay")
    end_date: date = Field(..., description="Inclusive end date for the replay")
    initial_capital: float = Field(100_000.0, ge=0.0)
    position_size: float = Field(1.0, gt=0.0, description="Number of shares to target per position")
    risk_free_rate: float = Field(
        0.0, description="Annualised risk-free rate used for Sharpe calculations"
    )
    selected_analysts: Optional[List[str]] = Field(
        default=None,
        description="Override the default analyst lineup in the TradingAgents graph",
    )
    data_vendor: Optional[str] = Field(
        default="local",
        description="Preferred market data vendor (defaults to recorded local data)",
    )
    data_dir: Optional[str] = Field(
        default=None,
        description="Optional override for the location of recorded market data",
    )


class StartBacktestRequest(BaseModel):
    """Request payload to enqueue a new backtest."""

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    parameters: BacktestParameters
    config_overrides: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional configuration overrides applied to the TradingAgents graph",
    )


class BacktestRunResponse(BaseModel):
    """Summary representation of a backtest run."""

    id: int
    run_id: str
    name: Optional[str]
    description: Optional[str]
    symbols: List[str]
    start_date: date
    end_date: date
    initial_capital: float
    position_size: float
    risk_free_rate: float
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    result_summary: Optional[str]
    error_message: Optional[str]


class BacktestMetricsResponse(BaseModel):
    """Performance metrics for a backtest run."""

    total_return: float
    annualized_return: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    volatility: Optional[float]
    max_drawdown: Optional[float]
    max_drawdown_duration: Optional[int]
    win_rate: Optional[float]
    best_trade_return: Optional[float]
    worst_trade_return: Optional[float]
    trades_executed: int
    holding_period_days: int
    metadata_json: Optional[str]


class BacktestEquityPointResponse(BaseModel):
    """Single point on the equity curve."""

    timestamp: datetime
    price: float
    equity: float
    cash: float
    position: float
    daily_return: float


class BacktestArtifactResponse(BaseModel):
    """Artifact metadata/content."""

    artifact_type: str
    content: Optional[str]
    uri: Optional[str]
    description: Optional[str]
    created_at: datetime


class BacktestRunDetailResponse(BaseModel):
    """Detailed run information including metrics and equity curve."""

    run: BacktestRunResponse
    metrics: Optional[BacktestMetricsResponse]
    equity_curve: List[BacktestEquityPointResponse]
    artifacts: List[BacktestArtifactResponse]


class BacktestComparisonEntry(BaseModel):
    run: BacktestRunResponse
    metrics: Optional[BacktestMetricsResponse]


class BacktestComparisonSummary(BaseModel):
    top_total_return_run: Optional[str]
    top_sharpe_run: Optional[str]
    lowest_drawdown_run: Optional[str]


class BacktestComparisonResponse(BaseModel):
    runs: List[BacktestComparisonEntry]
    summary: BacktestComparisonSummary


class BacktestTradeLogEntry(BaseModel):
    timestamp: datetime
    action: str
    quantity: float
    price: float
    cash: float
    equity: float
    position: float


class BacktestDecisionLogEntry(BaseModel):
    timestamp: datetime
    processed_signal: str
    raw_decision: Optional[str]
    equity: float
    price: float
    position: float


class BacktestExportResponse(BaseModel):
    """Full export payload for a backtest run."""

    run: BacktestRunResponse
    metrics: Optional[BacktestMetricsResponse]
    equity_curve: List[BacktestEquityPointResponse]
    trades: List[BacktestTradeLogEntry]
    decision_log: List[BacktestDecisionLogEntry]
    artifacts: List[BacktestArtifactResponse]
