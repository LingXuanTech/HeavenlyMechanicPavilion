"""Risk metrics model for storing portfolio risk measurements."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RiskMetrics(SQLModel, table=True):
    """Risk metrics model for storing portfolio risk measurements over time."""

    __tablename__ = "risk_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    session_id: Optional[int] = Field(default=None, foreign_key="trading_sessions.id", index=True)

    # VaR metrics (Value at Risk)
    var_1day_95: Optional[float] = Field(default=None)  # 1-day VaR at 95% confidence
    var_1day_99: Optional[float] = Field(default=None)  # 1-day VaR at 99% confidence
    var_5day_95: Optional[float] = Field(default=None)  # 5-day VaR at 95% confidence
    var_5day_99: Optional[float] = Field(default=None)  # 5-day VaR at 99% confidence

    # Portfolio metrics
    portfolio_value: float = Field(default=0.0)
    portfolio_volatility: Optional[float] = Field(default=None)
    sharpe_ratio: Optional[float] = Field(default=None)
    max_drawdown: Optional[float] = Field(default=None)

    # Position concentration
    largest_position_weight: Optional[float] = Field(default=None)
    top5_concentration: Optional[float] = Field(default=None)
    number_of_positions: int = Field(default=0)

    # Exposure metrics
    total_exposure: float = Field(default=0.0)
    long_exposure: float = Field(default=0.0)
    short_exposure: float = Field(default=0.0)
    net_exposure: float = Field(default=0.0)

    # Beta and correlation
    market_beta: Optional[float] = Field(default=None)
    correlation_to_spy: Optional[float] = Field(default=None)

    measured_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
