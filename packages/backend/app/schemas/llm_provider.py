"""Schemas for LLM provider metadata APIs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LLMModelInfo(BaseModel):
    name: str
    context_window: int
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    supports_streaming: bool = Field(default=False)
    supports_function_calling: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    max_output_tokens: Optional[int] = None


class LLMProviderSummary(BaseModel):
    provider: str
    display_name: str
    models: list[LLMModelInfo]


class ValidateKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider identifier")
    api_key: str = Field(..., description="API key to validate")
    model_name: Optional[str] = Field(
        default=None, description="Optional model name when validation requires it"
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ValidateKeyResponse(BaseModel):
    provider: str
    model_name: Optional[str]
    valid: bool
    detail: Optional[str] = None
