"""RunLog model for storing agent execution logs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RunLog(SQLModel, table=True):
    """RunLog model for storing agent execution and session logs."""

    __tablename__ = "run_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, max_length=255)

    # Run information
    run_type: str = Field(index=True, max_length=50)  # trading_session, backtest, analysis, etc.
    status: str = Field(
        default="RUNNING", max_length=20, index=True
    )  # RUNNING, COMPLETED, FAILED, CANCELLED

    # Execution context
    symbols: Optional[str] = Field(default=None, max_length=500)  # Comma-separated symbols
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)

    # Results and metrics
    result_summary: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    # Performance metrics
    total_trades: Optional[int] = Field(default=None)
    successful_trades: Optional[int] = Field(default=None)
    total_pnl: Optional[float] = Field(default=None)

    # Configuration used
    agent_config_snapshot: Optional[str] = Field(default=None)

    # Metadata fields
    metadata_json: Optional[str] = Field(default=None)
