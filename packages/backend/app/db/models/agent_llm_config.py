"""AgentLLMConfig model for per-agent LLM provider configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class AgentLLMConfig(SQLModel, table=True):
    """Stores LLM configuration for a specific agent."""

    __tablename__ = "agent_llm_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent_configs.id", unique=True, index=True)

    provider: str = Field(max_length=50, index=True)
    model: str = Field(max_length=100)
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    top_p: Optional[float] = Field(default=None)

    api_key_encrypted: Optional[str] = Field(default=None, max_length=1024)
    fallback_provider: Optional[str] = Field(default=None, max_length=50)
    fallback_model: Optional[str] = Field(default=None, max_length=100)

    cost_per_1k_tokens: Optional[float] = Field(default=None)
    enabled: bool = Field(default=True, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    agent: Optional["AgentConfig"] = Relationship(back_populates="llm_config")
    usage_events: list["AgentLLMUsage"] = Relationship(back_populates="llm_config")
