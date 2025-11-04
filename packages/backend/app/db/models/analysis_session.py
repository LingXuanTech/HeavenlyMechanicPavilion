"""Analysis session model for tracking TradingGraph analysis runs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AnalysisSession(SQLModel, table=True):
    """Analysis session model representing TradingGraph analysis runs.
    
    This model persists analysis session metadata including the ticker being
    analyzed, selected analysts, status, and lightweight summaries. It is
    distinct from the TradingSession model which tracks live/paper trading
    execution.
    """

    __tablename__ = "analysis_sessions"

    id: str = Field(primary_key=True, max_length=36)  # UUID string
    ticker: str = Field(max_length=20, index=True)
    status: str = Field(default="pending", max_length=20, index=True)  # pending, running, completed, failed
    
    # Configuration
    trade_date: str = Field(max_length=10)  # ISO date string YYYY-MM-DD
    selected_analysts_json: Optional[str] = Field(default=None)  # JSON list of analyst names
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = Field(default=None, index=True)
    
    # Optional lightweight summaries (can be populated from event buffer)
    summary_json: Optional[str] = Field(default=None)  # JSON for storing lightweight summary data
