"""Trading session model for tracking live/paper trading sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TradingSession(SQLModel, table=True):
    """Trading session model for live or paper trading runs."""

    __tablename__ = "trading_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    
    session_type: str = Field(max_length=20, index=True)  # PAPER, LIVE
    status: str = Field(default="ACTIVE", max_length=20, index=True)  # ACTIVE, STOPPED, COMPLETED
    
    # Session metadata
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    
    # Configuration
    max_position_size: Optional[float] = Field(default=None)
    max_portfolio_exposure: Optional[float] = Field(default=None)
    stop_loss_percentage: Optional[float] = Field(default=None)
    take_profit_percentage: Optional[float] = Field(default=None)
    
    # Performance tracking
    starting_capital: float = Field(default=0.0)
    current_capital: float = Field(default=0.0)
    total_pnl: float = Field(default=0.0)
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    stopped_at: Optional[datetime] = Field(default=None)
    
    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
