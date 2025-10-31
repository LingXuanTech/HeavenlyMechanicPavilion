"""LLM provider metadata and validation endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from tradingagents.llm_providers.registry import (
    ProviderType,
    get_provider_info,
    list_providers,
)

from tradingagents.llm_providers import ProviderFactory

from ..schemas.llm_provider import (
    LLMModelInfo,
    LLMProviderSummary,
    ValidateKeyRequest,
    ValidateKeyResponse,
)

router = APIRouter(prefix="/llm-providers", tags=["llm-providers"])


@router.get("/", response_model=List[LLMProviderSummary])
async def list_llm_providers() -> List[LLMProviderSummary]:
    """List all supported LLM providers and their available models."""

    summaries: List[LLMProviderSummary] = []
    for provider_enum in list_providers():
        info = get_provider_info(provider_enum)
        models = [
            LLMModelInfo(
                name=model.name,
                context_window=model.context_window,
                cost_per_1k_input_tokens=model.cost_per_1k_input_tokens,
                cost_per_1k_output_tokens=model.cost_per_1k_output_tokens,
                supports_streaming=model.supports_streaming,
                supports_function_calling=model.supports_function_calling,
                supports_vision=model.supports_vision,
                max_output_tokens=model.max_output_tokens,
            )
            for model in info.models.values()
        ]
        summaries.append(
            LLMProviderSummary(
                provider=provider_enum.value,
                display_name=info.name,
                models=models,
            )
        )
    return summaries


@router.get("/{provider}/models", response_model=List[LLMModelInfo])
async def list_models(provider: str) -> List[LLMModelInfo]:
    """List models for a specific provider."""
    try:
        provider_enum = ProviderType(provider.lower())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    info = get_provider_info(provider_enum)
    return [
        LLMModelInfo(
            name=model.name,
            context_window=model.context_window,
            cost_per_1k_input_tokens=model.cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=model.cost_per_1k_output_tokens,
            supports_streaming=model.supports_streaming,
            supports_function_calling=model.supports_function_calling,
            supports_vision=model.supports_vision,
            max_output_tokens=model.max_output_tokens,
        )
        for model in info.models.values()
    ]


@router.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_provider_key(request: ValidateKeyRequest) -> ValidateKeyResponse:
    """Validate an API key for the requested provider."""
    try:
        provider_enum = ProviderType(request.provider.lower())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    provider_info = get_provider_info(provider_enum)
    model_name = request.model_name or next(iter(provider_info.models.keys()), None)
    if not model_name:
        raise HTTPException(status_code=400, detail="Provider has no models configured")

    try:
        provider = ProviderFactory.create_provider(
            provider_type=provider_enum,
            api_key=request.api_key,
            model_name=model_name,
            temperature=request.temperature or 0.0,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
        )
        is_valid = await provider.health_check()
        detail = None if is_valid else "Provider health check failed"
        return ValidateKeyResponse(
            provider=provider_enum.value,
            model_name=model_name,
            valid=bool(is_valid),
            detail=detail,
        )
    except Exception as exc:
        return ValidateKeyResponse(
            provider=provider_enum.value,
            model_name=model_name,
            valid=False,
            detail=str(exc),
        )
