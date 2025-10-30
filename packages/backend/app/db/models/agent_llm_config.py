"""AgentLLMConfig model for storing agent-specific LLM configurations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentLLMConfig(SQLModel, table=True):
    """AgentLLMConfig model for storing LLM provider configurations per agent."""

    __tablename__ = "agent_llm_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent_configs.id", index=True)

    # Provider configuration
    provider: str = Field(index=True, max_length=50)  # openai, deepseek, grok, claude
    model_name: str = Field(max_length=100)

    # LLM parameters
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    top_p: Optional[float] = Field(default=None)

    # Optional API key override (encrypted)
    api_key_encrypted: Optional[str] = Field(default=None, max_length=500)

    # Fallback configuration
    fallback_provider: Optional[str] = Field(default=None, max_length=50)
    fallback_model: Optional[str] = Field(default=None, max_length=100)

    # Cost tracking
    cost_per_1k_input_tokens: float = Field(default=0.0)
    cost_per_1k_output_tokens: float = Field(default=0.0)

    # Status
    enabled: bool = Field(default=True, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata_json: Optional[str] = Field(default=None)
