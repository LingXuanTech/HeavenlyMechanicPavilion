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
