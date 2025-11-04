"""
LLM provider adapters - DEPRECATED.

This module is deprecated and maintained only for backward compatibility.
Please import from tradingagents.llm_providers instead.

All exports are redirected to the canonical tradingagents.llm_providers package.
"""

import warnings

# Redirect all imports to the canonical location
from tradingagents.llm_providers import (
    APIKeyMissingError,
    ClaudeProvider,
    LLMProviderError,
    OpenAIProvider,
    ProviderAPIError,
    RateLimitExceededError,
    TokenLimitExceededError,
)

# Issue deprecation warning
warnings.warn(
    "The 'llm_providers' module is deprecated. Please use 'tradingagents.llm_providers' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy exception aliases for backward compatibility
OpenAIProviderError = ProviderAPIError
ClaudeProviderError = LLMProviderError
ClaudeAPIKeyMissingError = APIKeyMissingError
ClaudeRateLimitExceededError = RateLimitExceededError
ClaudeTokenLimitExceededError = TokenLimitExceededError

__all__ = [
    "OpenAIProvider",
    "OpenAIProviderError",
    "APIKeyMissingError",
    "RateLimitExceededError",
    "TokenLimitExceededError",
    "ClaudeProvider",
    "ClaudeProviderError",
    "ClaudeAPIKeyMissingError",
    "ClaudeRateLimitExceededError",
    "ClaudeTokenLimitExceededError",
]
