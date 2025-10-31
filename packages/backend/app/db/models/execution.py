"""Execution model for storing trade executions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .trade import Trade
else:
    Trade = "Trade"


class Execution(SQLModel, table=True):
    """Execution model representing a filled trade or partial fill."""

    __tablename__ = "executions"

    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: int = Field(foreign_key="trades.id", index=True)

    symbol: str = Field(index=True, max_length=20)
    quantity: float = Field(default=0.0)
    price: float = Field(default=0.0)

    # Execution details
    execution_type: str = Field(default="FILL", max_length=20)  # FILL, PARTIAL_FILL
    commission: float = Field(default=0.0)
    fees: float = Field(default=0.0)

    # Exchange information
    exchange: Optional[str] = Field(default=None, max_length=50)
    execution_id: Optional[str] = Field(default=None, max_length=100, unique=True)

    executed_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)

    # Relationships
    trade: "Trade" = Relationship(back_populates="executions")
