"""AgentLLMConfig model for storing per-agent LLM provider configurations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentLLMConfig(SQLModel, table=True):
    """Stores LLM provider configurations for each agent."""

    __tablename__ = "agent_llm_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent_configs.id", index=True)

    # Primary LLM configuration
    provider: str = Field(max_length=50, index=True)  # openai, anthropic, deepseek, grok, etc.
    model_name: str = Field(max_length=100)  # gpt-4o-mini, claude-3-5-sonnet, etc.
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Optional API key override (encrypted)
    api_key_encrypted: Optional[str] = Field(default=None, max_length=500)

    # Fallback configuration
    fallback_provider: Optional[str] = Field(default=None, max_length=50)
    fallback_model: Optional[str] = Field(default=None, max_length=100)

    # Cost tracking
    cost_per_1k_input_tokens: float = Field(default=0.0, ge=0.0)
    cost_per_1k_output_tokens: float = Field(default=0.0, ge=0.0)

    # Status
    enabled: bool = Field(default=True, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata_json: Optional[str] = Field(default=None)
