"""Execution event schemas for real-time streaming."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExecutionEventType(str, Enum):
    """Types of execution events."""
    
    # Order lifecycle events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACCEPTED = "order_accepted"
    ORDER_REJECTED = "order_rejected"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_CANCELLED = "order_cancelled"
    
    # Position events
    POSITION_OPENED = "position_opened"
    POSITION_UPDATED = "position_updated"
    POSITION_CLOSED = "position_closed"
    
    # Risk events
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    RISK_CHECK_FAILED = "risk_check_failed"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    
    # Portfolio events
    PORTFOLIO_UPDATED = "portfolio_updated"


class OrderEventData(BaseModel):
    """Data for order-related events."""
    
    symbol: str
    action: str  # BUY, SELL
    quantity: float
    order_type: str  # MARKET, LIMIT
    status: str
    order_id: Optional[str] = None
    filled_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    commission: Optional[float] = None
    fees: Optional[float] = None
    reason: Optional[str] = None  # For rejections/cancellations


class PositionEventData(BaseModel):
    """Data for position-related events."""
    
    symbol: str
    quantity: float
    average_cost: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: Optional[float] = None
    position_type: str = "LONG"  # LONG, SHORT


class RiskEventData(BaseModel):
    """Data for risk-related events."""
    
    symbol: str
    reason: str
    current_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    details: Optional[dict] = None


class PortfolioEventData(BaseModel):
    """Data for portfolio-related events."""
    
    portfolio_id: int
    current_capital: float
    total_value: float
    unrealized_pnl: float
    realized_pnl: float
    positions_count: int


class ExecutionEvent(BaseModel):
    """Standardized execution event for streaming."""
    
    event_type: ExecutionEventType
    session_id: Optional[str] = None
    portfolio_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event-specific data (only one should be populated)
    order_data: Optional[OrderEventData] = None
    position_data: Optional[PositionEventData] = None
    risk_data: Optional[RiskEventData] = None
    portfolio_data: Optional[PortfolioEventData] = None
    
    # Additional context
    message: Optional[str] = None
    metadata: Optional[dict] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }