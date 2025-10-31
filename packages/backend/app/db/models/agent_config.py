"""AgentConfig model for storing agent configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentConfig(SQLModel, table=True):
    """AgentConfig model for storing AI agent configurations."""

    __tablename__ = "agent_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=255)
    agent_type: str = Field(index=True, max_length=50)  # analyst, trader, risk_manager, etc.
    role: str = Field(index=True, max_length=50)  # Role from AgentRole enum

    # LLM Configuration (JSON format for maximum flexibility)
    # Structure: {
    #   "provider": "openai" | "anthropic" | "deepseek" | "google",
    #   "model": "gpt-4o" | "claude-3-opus" | "deepseek-chat",
    #   "api_key_env": "OPENAI_API_KEY",  # Environment variable name
    #   "base_url": "https://api.example.com/v1",  # Optional custom endpoint
    #   "temperature": 0.7,
    #   "max_tokens": 4000,
    #   ... additional provider-specific parameters
    # }
    llm_config_json: str = Field(default='{"provider": "openai", "model": "gpt-4o-mini"}')

    # Agent configuration
    prompt_template: str = Field(
        default="You are a helpful AI assistant."
    )  # Agent's prompt template
    capabilities_json: Optional[str] = Field(default=None)  # JSON list of capabilities
    required_tools_json: Optional[str] = Field(default=None)  # JSON list of required tools

    # Memory configuration
    requires_memory: bool = Field(default=False)
    memory_name: Optional[str] = Field(default=None, max_length=100)

    # Slot and workflow configuration
    is_reserved: bool = Field(default=True)  # Reserved agents cannot be deleted
    slot_name: Optional[str] = Field(
        default=None, max_length=50, index=True
    )  # e.g., 'market', 'social'

    # Agent-specific parameters
    config_json: Optional[str] = Field(default=None)

    # Status
    is_active: bool = Field(default=True, index=True)
    version: str = Field(default="1.0.0", max_length=20)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata fields
    description: Optional[str] = Field(default=None, max_length=1000)
    metadata_json: Optional[str] = Field(default=None)
