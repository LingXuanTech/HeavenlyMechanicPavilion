"""Trade model for storing trade decisions and orders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .execution import Execution
    from .portfolio import Portfolio
else:
    Execution = "Execution"
    Portfolio = "Portfolio"


class Trade(SQLModel, table=True):
    """Trade model representing a trading decision or order."""

    __tablename__ = "trades"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    
    symbol: str = Field(index=True, max_length=20)
    action: str = Field(max_length=10)  # BUY, SELL, SHORT, COVER
    quantity: float = Field(default=0.0)
    order_type: str = Field(default="MARKET", max_length=20)  # MARKET, LIMIT, STOP, etc.
    
    # Price information
    limit_price: Optional[float] = Field(default=None)
    stop_price: Optional[float] = Field(default=None)
    
    # Order status
    status: str = Field(default="PENDING", max_length=20, index=True)  # PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    filled_quantity: float = Field(default=0.0)
    average_fill_price: Optional[float] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = Field(default=None)
    
    # Agent decision metadata
    decision_rationale: Optional[str] = Field(default=None)
    confidence_score: Optional[float] = Field(default=None)
    
    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
    
    # Relationships
    portfolio: "Portfolio" = Relationship(back_populates="trades")
    executions: List["Execution"] = Relationship(back_populates="trade")
