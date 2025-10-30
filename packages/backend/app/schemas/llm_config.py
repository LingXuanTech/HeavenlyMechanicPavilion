"""Pydantic schemas for agent-level LLM configuration and provider metadata."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentLLMConfigBase(BaseModel):
    """Shared fields for LLM configuration requests."""

    provider: str = Field(..., description="LLM provider identifier")
    model: str = Field(..., description="Model name for the provider")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    fallback_provider: Optional[str] = Field(
        None, description="Provider to use if the primary provider fails"
    )
    fallback_model: Optional[str] = Field(
        None, description="Model to use on fallback provider"
    )
    cost_per_1k_tokens: Optional[float] = Field(
        None, ge=0.0, description="Cost estimate per 1k tokens for budgeting"
    )
    enabled: bool = Field(True, description="Whether this configuration is active")


class AgentLLMConfigCreate(AgentLLMConfigBase):
    """Schema for creating or replacing an LLM configuration."""

    api_key: Optional[str] = Field(
        None,
        description="Optional API key override specific to this agent",
    )


class AgentLLMConfigUpdate(BaseModel):
    """Schema for partial updates to an LLM configuration."""

    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    cost_per_1k_tokens: Optional[float] = Field(None, ge=0.0)
    enabled: Optional[bool] = None
    api_key: Optional[str] = Field(
        None,
        description="If provided replaces the stored encrypted key; empty string clears",
    )


class AgentLLMConfigResponse(AgentLLMConfigBase):
    """Response schema for agent LLM configuration."""

    agent_id: int
    has_api_key: bool = Field(
        False, description="True if an encrypted API key override is stored"
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentLLMUsageRecord(BaseModel):
    """Individual usage data point for reporting."""

    agent_id: Optional[int]
    agent_name: Optional[str]
    provider: str
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    cost: Optional[float]
    latency_ms: Optional[float]
    success: bool
    error_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentLLMUsageSummary(BaseModel):
    """Aggregated usage summary for dashboards."""

    prompt_tokens: float
    completion_tokens: float
    total_tokens: float
    total_cost: float
    api_calls: float


class LLMProviderModel(BaseModel):
    """Metadata for an available LLM provider."""

    id: str
    name: str
    supports_streaming: bool = False
    models: List[str]
    description: Optional[str] = None
    default_base_url: Optional[str] = None


class LLMProviderListResponse(BaseModel):
    """Response listing all supported providers and their models."""

    providers: List[LLMProviderModel]


class ProviderModelListResponse(BaseModel):
    """Response listing models for a specific provider."""

    provider: str
    models: List[str]


class ProviderKeyValidationRequest(BaseModel):
    """Request payload for validating provider API keys."""

    provider: str
    api_key: str


class ProviderKeyValidationResponse(BaseModel):
    """Response for API key validation."""

    provider: str
    valid: bool
    error: Optional[str] = None


class AgentLLMTestRequest(BaseModel):
    """Payload for testing an agent's LLM configuration."""

    prompt: Optional[str] = Field(
        None,
        description="Optional prompt to send during testing. Defaults to provider ping.",
    )


class AgentLLMTestResponse(BaseModel):
    """Result from testing an LLM configuration."""

    success: bool
    message: str
    latency_ms: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
