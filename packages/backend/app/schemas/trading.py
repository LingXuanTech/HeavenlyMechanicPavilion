"""Schemas for trading and execution endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    """Request to start a trading session."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    session_type: str = Field(default="PAPER", description="Session type (PAPER or LIVE)")
    name: Optional[str] = Field(None, description="Session name")
    description: Optional[str] = Field(None, description="Session description")
    max_position_size: Optional[float] = Field(
        None, ge=0, le=1, description="Max position size as percentage (0-1)"
    )
    max_portfolio_exposure: Optional[float] = Field(
        None, ge=0, le=2, description="Max portfolio exposure"
    )
    stop_loss_percentage: Optional[float] = Field(
        None, ge=0, le=1, description="Stop loss percentage (0-1)"
    )
    take_profit_percentage: Optional[float] = Field(
        None, ge=0, description="Take profit percentage"
    )
    position_sizing_method: str = Field(
        default="FIXED_PERCENTAGE", description="Position sizing method"
    )


class TradingSessionResponse(BaseModel):
    """Trading session response."""

    id: int
    portfolio_id: int
    session_type: str
    status: str
    name: Optional[str]
    description: Optional[str]

    max_position_size: Optional[float]
    max_portfolio_exposure: Optional[float]
    stop_loss_percentage: Optional[float]
    take_profit_percentage: Optional[float]

    starting_capital: float
    current_capital: float
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int

    started_at: datetime
    stopped_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExecuteSignalRequest(BaseModel):
    """Request to execute a trading signal."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    symbol: str = Field(..., description="Stock symbol")
    signal: str = Field(..., description="Trading signal (BUY, SELL, HOLD)")
    current_price: float = Field(..., gt=0, description="Current market price")
    decision_rationale: Optional[str] = Field(None, description="Decision rationale")
    confidence_score: Optional[float] = Field(
        None, ge=0, le=1, description="Confidence score (0-1)"
    )
    session_id: Optional[int] = Field(None, description="Trading session ID")


class TradeResponse(BaseModel):
    """Trade response."""

    id: int
    portfolio_id: int
    symbol: str
    action: str
    quantity: float
    order_type: str

    limit_price: Optional[float]
    stop_price: Optional[float]

    status: str
    filled_quantity: float
    average_fill_price: Optional[float]

    created_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime]

    decision_rationale: Optional[str]
    confidence_score: Optional[float]

    class Config:
        from_attributes = True


class ForceExitRequest(BaseModel):
    """Request to force exit a position."""

    portfolio_id: int = Field(..., description="Portfolio ID")
    symbol: str = Field(..., description="Stock symbol")
    reason: str = Field(default="Force exit", description="Reason for exit")


class RiskDiagnosticsResponse(BaseModel):
    """Risk diagnostics response."""

    portfolio_id: int
    portfolio_value: float

    var_1day_95: Optional[float]
    var_1day_99: Optional[float]
    var_5day_95: Optional[float]
    var_5day_99: Optional[float]

    portfolio_volatility: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]

    largest_position_weight: Optional[float]
    top5_concentration: Optional[float]
    number_of_positions: int

    total_exposure: float
    long_exposure: float
    short_exposure: float
    net_exposure: float

    warnings: List[str]
    measured_at: datetime


class PortfolioStateResponse(BaseModel):
    """Portfolio state response."""

    id: int
    name: str
    description: Optional[str]
    initial_capital: float
    current_capital: float
    currency: str

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Position response."""

    id: int
    portfolio_id: int
    symbol: str
    quantity: float

    average_cost: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float

    position_type: str
    entry_date: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioStateDetailResponse(BaseModel):
    """Detailed portfolio state response."""

    portfolio: PortfolioStateResponse
    positions: List[PositionResponse]
    total_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
