"""Portfolio model for storing portfolio information."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .position import Position
    from .trade import Trade
else:
    Position = "Position"
    Trade = "Trade"


class Portfolio(SQLModel, table=True):
    """Portfolio model representing a trading portfolio."""

    __tablename__ = "portfolios"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    initial_capital: float = Field(default=100000.0)
    current_capital: float = Field(default=100000.0)
    currency: str = Field(default="USD", max_length=3)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
    
    # Relationships
    positions: List["Position"] = Relationship(back_populates="portfolio")
    trades: List["Trade"] = Relationship(back_populates="portfolio")
