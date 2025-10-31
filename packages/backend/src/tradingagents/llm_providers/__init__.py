"""LLM provider abstraction layer for multi-provider support."""

from __future__ import annotations

# NOTE: agent_llm_factory module is not yet implemented
# from .agent_llm_factory import (
#     clear_llm_cache,
#     get_llm_for_agent,
#     get_llm_for_agent_by_name,
# )
from .base import BaseLLMProvider, LLMMessage, LLMResponse
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

# NOTE: These modules are not yet implemented in this directory
# They exist in src/llm_providers/ instead
# from .claude_provider import ClaudeProvider
# from .deepseek_provider import DeepSeekProvider
# from .factory import ProviderFactory
# from .grok_provider import GrokProvider
# from .openai_provider import OpenAIProvider
# from .registry import (
#     PROVIDER_REGISTRY,
#     ModelInfo,
#     ProviderInfo,
#     ProviderType,
#     calculate_cost,
#     get_model_info,
#     get_provider_info,
#     list_models,
#     list_providers,
# )

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
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
