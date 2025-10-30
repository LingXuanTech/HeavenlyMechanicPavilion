"""Pydantic schemas for agent LLM usage analytics."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentLLMUsageRecord(BaseModel):
    """Single usage record for an agent LLM invocation."""

    id: int
    agent_id: int
    provider: str
    model_name: str
    is_fallback: bool = Field(default=False)
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    created_at: datetime
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class AgentLLMUsageSummary(BaseModel):
    """Aggregated usage summary for an agent."""

    agent_id: int
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    records: List[AgentLLMUsageRecord]


class AgentLLMUsageQuery(BaseModel):
    """Query parameters for usage analytics."""

    start: Optional[datetime] = Field(default=None, description="Filter usage at or after this timestamp")
    end: Optional[datetime] = Field(default=None, description="Filter usage before this timestamp")
    limit: int = Field(default=100, ge=1, le=1000)
