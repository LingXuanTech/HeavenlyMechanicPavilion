"""LLM provider abstraction layer for multi-provider support."""

from __future__ import annotations

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .claude_provider import ClaudeProvider
from .deepseek_provider import DeepSeekProvider
from .exceptions import (
    APIKeyMissingError,
    LLMProviderError,
    ModelNotSupportedError,
    ProviderAPIError,
    ProviderHealthCheckError,
    ProviderNotFoundError,
    RateLimitExceededError,
    TokenLimitExceededError,
)
from .factory import ProviderFactory
from .grok_provider import GrokProvider
from .openai_provider import OpenAIProvider
from .registry import (
    PROVIDER_REGISTRY,
    ModelInfo,
    ProviderInfo,
    ProviderType,
    calculate_cost,
    get_model_info,
    get_provider_info,
    list_models,
    list_providers,
)

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    # Providers
    "OpenAIProvider",
    "DeepSeekProvider",
    "GrokProvider",
    "ClaudeProvider",
    # Factory
    "ProviderFactory",
    # Registry
    "ProviderType",
    "ProviderInfo",
    "ModelInfo",
    "PROVIDER_REGISTRY",
    "get_provider_info",
    "get_model_info",
    "list_providers",
    "list_models",
    "calculate_cost",
    # Exceptions
    "LLMProviderError",
    "ProviderNotFoundError",
    "ModelNotSupportedError",
    "APIKeyMissingError",
    "RateLimitExceededError",
    "ProviderAPIError",
    "TokenLimitExceededError",
    "ProviderHealthCheckError",
]
