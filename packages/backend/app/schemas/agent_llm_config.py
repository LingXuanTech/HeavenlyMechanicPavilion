"""Pydantic schemas for AgentLLMConfig."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentLLMConfigBase(BaseModel):
    """Base schema for AgentLLMConfig."""

    provider: str = Field(..., description="LLM provider (openai, deepseek, grok, claude)")
    model_name: str = Field(..., description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nucleus sampling")
    fallback_provider: Optional[str] = Field(default=None, description="Fallback provider")
    fallback_model: Optional[str] = Field(default=None, description="Fallback model")
    enabled: bool = Field(default=True, description="Whether this config is enabled")


class AgentLLMConfigCreate(AgentLLMConfigBase):
    """Schema for creating an AgentLLMConfig."""

    agent_id: int = Field(..., description="ID of the agent this config belongs to")
    api_key: Optional[str] = Field(
        default=None, description="Optional API key override (will be encrypted)"
    )
    cost_per_1k_input_tokens: float = Field(
        default=0.0, ge=0.0, description="Cost per 1K input tokens"
    )
    cost_per_1k_output_tokens: float = Field(
        default=0.0, ge=0.0, description="Cost per 1K output tokens"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AgentLLMConfigUpsert(AgentLLMConfigBase):
    """Schema for upserting an AgentLLMConfig without binding to an agent."""

    api_key: Optional[str] = Field(default=None, description="Optional API key override")
    cost_per_1k_input_tokens: Optional[float] = Field(default=None, ge=0.0)
    cost_per_1k_output_tokens: Optional[float] = Field(default=None, ge=0.0)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AgentLLMConfigUpdate(BaseModel):
    """Schema for updating an AgentLLMConfig."""

    provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    api_key: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    cost_per_1k_input_tokens: Optional[float] = Field(default=None, ge=0.0)
    cost_per_1k_output_tokens: Optional[float] = Field(default=None, ge=0.0)
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentLLMConfigResponse(AgentLLMConfigBase):
    """Schema for AgentLLMConfig response."""

    id: int
    agent_id: int
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    has_api_key_override: bool = Field(
        default=False, description="Whether this config has an API key override"
    )
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class BulkAgentLLMConfigRequest(BaseModel):
    """Bulk assignment request for LLM configurations."""

    agent_ids: List[int] = Field(..., description="Agents that should receive the configuration")
    config: AgentLLMConfigUpsert
