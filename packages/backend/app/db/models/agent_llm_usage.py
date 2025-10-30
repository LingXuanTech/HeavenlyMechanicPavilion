"""AgentLLMUsage model for tracking per-agent LLM consumption."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentLLMUsage(SQLModel, table=True):
    """Tracks token usage and cost per agent LLM invocation."""

    __tablename__ = "agent_llm_usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent_configs.id", index=True)

    provider: str = Field(max_length=50, description="Primary or fallback provider name")
    model_name: str = Field(max_length=100, description="Model used for the call")
    is_fallback: bool = Field(default=False, description="Whether the fallback provider was used")

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    cost_usd: float = Field(default=0.0, ge=0.0)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    metadata_json: Optional[str] = Field(default=None)
