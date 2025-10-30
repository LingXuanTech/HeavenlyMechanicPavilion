"""AgentLLMUsage model for tracking LLM cost and token consumption."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class AgentLLMUsage(SQLModel, table=True):
    """Individual LLM invocation usage record per agent."""

    __tablename__ = "agent_llm_usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: Optional[int] = Field(foreign_key="agent_configs.id", index=True, default=None)
    llm_config_id: Optional[int] = Field(foreign_key="agent_llm_configs.id", index=True, default=None)

    agent_name: Optional[str] = Field(default=None, max_length=255, index=True)
    provider: str = Field(max_length=50, index=True)
    model: str = Field(max_length=100)

    prompt_tokens: Optional[int] = Field(default=None)
    completion_tokens: Optional[int] = Field(default=None)
    total_tokens: Optional[int] = Field(default=None)

    cost: Optional[float] = Field(default=None)
    latency_ms: Optional[float] = Field(default=None)

    success: bool = Field(default=True, index=True)
    error_type: Optional[str] = Field(default=None, max_length=255)
    error_message: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    llm_config: Optional["AgentLLMConfig"] = Relationship(back_populates="usage_events")
    agent: Optional["AgentConfig"] = Relationship(back_populates="llm_usage_events")
