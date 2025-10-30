"""Custom exceptions for LLM providers."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class ProviderNotFoundError(LLMProviderError):
    """Raised when a provider is not found in the registry."""

    pass


class ModelNotSupportedError(LLMProviderError):
    """Raised when a model is not supported by the provider."""

    pass


class APIKeyMissingError(LLMProviderError):
    """Raised when an API key is required but not provided."""

    pass


class RateLimitExceededError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    pass


class ProviderAPIError(LLMProviderError):
    """Raised when the provider API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TokenLimitExceededError(LLMProviderError):
    """Raised when token limit is exceeded."""

    pass


class ProviderHealthCheckError(LLMProviderError):
    """Raised when provider health check fails."""

    pass
