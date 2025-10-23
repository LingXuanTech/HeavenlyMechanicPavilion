"""Position model for storing current positions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .portfolio import Portfolio
else:
    Portfolio = "Portfolio"


class Position(SQLModel, table=True):
    """Position model representing a current holding in a portfolio."""

    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    symbol: str = Field(index=True, max_length=20)
    quantity: float = Field(default=0.0)
    
    # Cost basis and P&L tracking
    average_cost: float = Field(default=0.0)
    current_price: float = Field(default=0.0)
    unrealized_pnl: float = Field(default=0.0)
    realized_pnl: float = Field(default=0.0)
    
    # Position metadata
    position_type: str = Field(default="LONG", max_length=10)  # LONG or SHORT
    entry_date: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
    
    # Relationships
    portfolio: "Portfolio" = Relationship(back_populates="positions")
