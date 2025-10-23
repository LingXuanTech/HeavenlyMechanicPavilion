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
    
    # LLM Configuration
    llm_provider: str = Field(default="openai", max_length=50)
    llm_model: str = Field(default="gpt-4o-mini", max_length=100)
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    
    # Agent-specific parameters
    config_json: Optional[str] = Field(default=None)
    
    # Status
    is_active: bool = Field(default=True, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata fields
    description: Optional[str] = Field(default=None, max_length=1000)
    metadata_json: Optional[str] = Field(default=None)
