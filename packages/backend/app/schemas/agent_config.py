"""Pydantic schemas for agent configuration API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # pragma: no cover - import guard for type checkers
    from .agent_llm_config import AgentLLMConfigResponse


class AgentConfigBase(BaseModel):
    """Base schema for agent configuration."""
    
    name: str = Field(..., description="Unique agent name")
    agent_type: str = Field(..., description="Type of agent (analyst, researcher, etc.)")
    role: str = Field(..., description="Agent role from AgentRole enum")
    description: Optional[str] = Field(None, description="Human-readable description")
    
    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model name")
    llm_type: str = Field(default="quick", description="LLM type: 'quick' or 'deep'")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    
    # Agent configuration
    prompt_template: Optional[str] = Field(None, description="Agent's prompt template")
    capabilities: Optional[List[str]] = Field(None, description="List of agent capabilities")
    required_tools: Optional[List[str]] = Field(None, description="List of required tool names")
    
    # Memory configuration
    requires_memory: bool = Field(default=False)
    memory_name: Optional[str] = Field(None)
    
    # Slot and workflow configuration
    is_reserved: bool = Field(default=False, description="Reserved agents cannot be deleted")
    slot_name: Optional[str] = Field(None, description="Workflow slot name")
    
    # Status
    is_active: bool = Field(default=True)
    version: str = Field(default="1.0.0")
    
    # Additional configuration
    config: Optional[dict] = Field(None, description="Additional agent-specific configuration")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class AgentConfigCreate(AgentConfigBase):
    """Schema for creating a new agent configuration."""
    pass


class AgentConfigUpdate(BaseModel):
    """Schema for updating an agent configuration."""
    
    agent_type: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    
    # LLM Configuration
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_type: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    
    # Agent configuration
    prompt_template: Optional[str] = None
    capabilities: Optional[List[str]] = None
    required_tools: Optional[List[str]] = None
    
    # Memory configuration
    requires_memory: Optional[bool] = None
    memory_name: Optional[str] = None
    
    # Slot and workflow configuration
    slot_name: Optional[str] = None
    
    # Status
    is_active: Optional[bool] = None
    version: Optional[str] = None
    
    # Additional configuration
    config: Optional[dict] = None
    metadata: Optional[dict] = None


class AgentConfigResponse(AgentConfigBase):
    """Schema for agent configuration response."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    active_llm_config: Optional["AgentLLMConfigResponse"] = None
    
    class Config:
        from_attributes = True


class AgentConfigList(BaseModel):
    """Schema for list of agent configurations."""
    
    agents: List[AgentConfigResponse]
    total: int


AgentConfigResponse.model_rebuild()
