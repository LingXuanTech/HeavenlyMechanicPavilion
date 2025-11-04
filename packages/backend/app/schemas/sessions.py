"""Session and streaming related schemas."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunSessionRequest(BaseModel):
    """Request body required to start a new TradingAgents session."""

    ticker: str = Field(..., description="Ticker or company identifier to analyse")
    trade_date: date = Field(..., description="Trading date to evaluate")
    selected_analysts: Optional[List[str]] = Field(
        default=None,
        description="Override the default analyst roster",
    )


class RunSessionResponse(BaseModel):
    """Metadata returned when a run session has been scheduled."""

    session_id: str
    stream_endpoint: str


class SessionEvent(BaseModel):
    """Represents events sent over SSE/WebSocket transports."""

    type: str
    message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "SessionEvent":
        payload = {k: v for k, v in raw.items() if k not in {"type", "message"}}
        return cls(type=raw.get("type", "event"), message=raw.get("message"), payload=payload)


class BufferedSessionEvent(BaseModel):
    """Represents a buffered event with timestamp from event history."""

    timestamp: str = Field(..., description="ISO format timestamp of when the event was enqueued")
    event: Dict[str, Any] = Field(..., description="The raw event payload")


class SessionEventsHistoryResponse(BaseModel):
    """Response containing recent events buffered for a session."""

    session_id: str = Field(..., description="The session identifier")
    events: List[BufferedSessionEvent] = Field(
        default_factory=list,
        description="List of buffered events with timestamps, ordered from oldest to newest"
    )
    count: int = Field(..., description="Number of events in the buffer")


class SessionSummary(BaseModel):
    """Lightweight summary of a persisted analysis session.
    
    Maps to the shared SessionSummary DTO from the frontend.
    """

    id: str = Field(..., description="Session UUID")
    ticker: str = Field(..., description="Ticker symbol analyzed")
    asOfDate: str = Field(..., description="Trading date in ISO format")
    status: str = Field(..., description="Session status: pending, running, completed, failed")
    createdAt: str = Field(..., description="ISO timestamp of when session was created")
    updatedAt: Optional[str] = Field(None, description="ISO timestamp of last update")


class SessionListResponse(BaseModel):
    """Response for listing analysis sessions."""

    sessions: List[SessionSummary] = Field(default_factory=list)
    total: int = Field(..., description="Total number of sessions in result")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum records returned")


class SessionDetailResponse(BaseModel):
    """Response for a single analysis session with events."""

    session: SessionSummary
    events: List[BufferedSessionEvent] = Field(
        default_factory=list,
        description="Recent events for this session"
    )
