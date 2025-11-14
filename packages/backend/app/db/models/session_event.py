"""Session event model for persisting analysis session events."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


class SessionEvent(SQLModel, table=True):
    """Session event model for storing individual events during analysis sessions.
    
    This model persists all events that occur during a session, enabling
    event history retrieval after service restarts and supporting paginated queries.
    """

    __tablename__ = "session_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(max_length=36, index=True, foreign_key="analysis_sessions.id")
    
    # Event data
    event_type: str = Field(max_length=50, index=True)  # e.g., "agent_start", "agent_complete", "error"
    message: Optional[str] = Field(default=None)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Sequencing and timing
    sequence_number: int = Field(index=True)  # Auto-incrementing per session
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Metadata
    agent_name: Optional[str] = Field(default=None, max_length=100, index=True)
    status: Optional[str] = Field(default=None, max_length=20)  # "success", "error", "pending"

    __table_args__ = (
        Index("idx_session_events_session_seq", "session_id", "sequence_number"),
        Index("idx_session_events_session_time", "session_id", "timestamp"),
    )