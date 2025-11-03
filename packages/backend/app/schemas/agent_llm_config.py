"""Pydantic schemas for agent LLM configuration management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AgentLLMConfigBase(BaseModel):
    """Base schema for agent LLM configuration."""

    provider: str = Field(..., description="LLM provider name (openai, anthropic, deepseek, grok)")
    model_name: str = Field(..., description="Model name (e.g., gpt-4o-mini)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p sampling parameter")


class AgentLLMConfigCreate(AgentLLMConfigBase):
    """Schema for creating a new agent LLM configuration."""

    agent_id: int = Field(..., description="Agent ID this configuration belongs to")
    api_key: Optional[str] = Field(default=None, description="Optional API key override")
    fallback_provider: Optional[str] = Field(default=None, description="Fallback provider name")
    fallback_model: Optional[str] = Field(default=None, description="Fallback model name")
    cost_per_1k_input_tokens: float = Field(default=0.0, ge=0.0, description="Cost per 1k input tokens")
    cost_per_1k_output_tokens: float = Field(default=0.0, ge=0.0, description="Cost per 1k output tokens")
    enabled: bool = Field(default=True, description="Whether this configuration is enabled")
    metadata_json: Optional[str] = Field(default=None, description="Additional metadata as JSON string")


class AgentLLMConfigUpdate(BaseModel):
    """Schema for updating an agent LLM configuration."""

    provider: Optional[str] = Field(default=None, description="LLM provider name")
    model_name: Optional[str] = Field(default=None, description="Model name")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Top-p sampling parameter")
    api_key: Optional[str] = Field(default=None, description="Optional API key override")
    fallback_provider: Optional[str] = Field(default=None, description="Fallback provider name")
    fallback_model: Optional[str] = Field(default=None, description="Fallback model name")
    cost_per_1k_input_tokens: Optional[float] = Field(default=None, ge=0.0)
    cost_per_1k_output_tokens: Optional[float] = Field(default=None, ge=0.0)
    enabled: Optional[bool] = Field(default=None, description="Whether this configuration is enabled")
    metadata_json: Optional[str] = Field(default=None, description="Additional metadata as JSON string")


class AgentLLMConfigUpsert(AgentLLMConfigBase):
    """Schema for upserting (create or update) an agent LLM configuration."""

    api_key: Optional[str] = Field(default=None, description="Optional API key override")
    fallback_provider: Optional[str] = Field(default=None, description="Fallback provider name")
    fallback_model: Optional[str] = Field(default=None, description="Fallback model name")
    cost_per_1k_input_tokens: float = Field(default=0.0, ge=0.0, description="Cost per 1k input tokens")
    cost_per_1k_output_tokens: float = Field(default=0.0, ge=0.0, description="Cost per 1k output tokens")
    enabled: bool = Field(default=True, description="Whether this configuration is enabled")
    metadata_json: Optional[str] = Field(default=None, description="Additional metadata as JSON string")


class AgentLLMConfigResponse(BaseModel):
    """Schema for agent LLM configuration response."""

    id: int
    agent_id: int
    provider: str
    model_name: str
    temperature: float
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    has_api_key_override: bool = Field(
        default=False,
        description="Whether this config has an API key override (not the key itself)"
    )
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    enabled: bool
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("has_api_key_override", mode="before")
    @classmethod
    def compute_has_api_key(cls, v: bool | None, info) -> bool:
        """Compute has_api_key_override from api_key_encrypted field."""
        if v is not None:
            return v
        # If called from ORM, check for api_key_encrypted attribute
        if hasattr(info.data, "get"):
            api_key_encrypted = info.data.get("api_key_encrypted")
            return api_key_encrypted is not None and len(api_key_encrypted) > 0
        return False
