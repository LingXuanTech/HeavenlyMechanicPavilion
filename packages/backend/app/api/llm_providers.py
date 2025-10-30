"""API endpoints for managing LLM providers and validation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tradingagents.llm.providers import LLMProviderFactory, ProviderConfigurationError

from ..schemas.llm_config import (
    LLMProviderListResponse,
    LLMProviderModel,
    ProviderKeyValidationRequest,
    ProviderKeyValidationResponse,
    ProviderModelListResponse,
)

router = APIRouter(prefix="/llm-providers", tags=["llm-providers"])
provider_factory = LLMProviderFactory()


@router.get("/", response_model=LLMProviderListResponse)
async def list_llm_providers() -> LLMProviderListResponse:
    metadata = provider_factory.list_providers()
    providers = [
        LLMProviderModel(
            id=meta.id,
            name=meta.name,
            supports_streaming=meta.supports_streaming,
            models=meta.models,
            default_base_url=meta.default_base_url,
        )
        for meta in metadata
    ]
    return LLMProviderListResponse(providers=providers)


@router.get("/{provider}/models", response_model=ProviderModelListResponse)
async def list_provider_models(provider: str) -> ProviderModelListResponse:
    try:
        models = provider_factory.list_models(provider)
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProviderModelListResponse(provider=provider, models=models)


@router.post("/validate-key", response_model=ProviderKeyValidationResponse)
async def validate_provider_key(payload: ProviderKeyValidationRequest) -> ProviderKeyValidationResponse:
    try:
        valid, error = provider_factory.validate_key(payload.provider, payload.api_key)
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProviderKeyValidationResponse(provider=payload.provider, valid=valid, error=error)
