"""OpenAI provider adapter with configuration support."""

from __future__ import annotations

import logging
import os
from typing import Any

import tiktoken
from openai import AsyncOpenAI, OpenAIError, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIProviderError(Exception):
    """Base exception for OpenAI provider errors."""

    pass


class APIKeyMissingError(OpenAIProviderError):
    """Raised when API key is missing."""

    pass


class RateLimitExceededError(OpenAIProviderError):
    """Raised when rate limit is exceeded."""

    pass


class TokenLimitExceededError(OpenAIProviderError):
    """Raised when token limit is exceeded."""

    pass


class OpenAIProvider:
    """
    OpenAI provider adapter with configuration support.

    This class provides a clean interface to the OpenAI API with support for:
    - Multiple model configurations (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
    - Parameter validation (temperature range, token limits)
    - Token counting
    - Error handling with proper exceptions
    """

    # Supported models with their token limits
    SUPPORTED_MODELS = {
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-preview": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
    }

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize OpenAI provider.

        Args:
            model_name: OpenAI model name (e.g., "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo")
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (None for model default)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY environment variable)

        Raises:
            APIKeyMissingError: If API key is not provided
            ValueError: If parameters are invalid
        """
        # Load API key from environment if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError(
                "OpenAI API key is required. "
                "Provide it as a parameter or set OPENAI_API_KEY environment variable."
            )

        # Validate model name
        if model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                f"Model '{model_name}' not in supported models list. "
                f"Supported: {list(self.SUPPORTED_MODELS.keys())}"
            )

        self.model_name = model_name

        # Validate temperature
        if not 0.0 <= temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
        self.temperature = temperature

        # Validate max_tokens
        model_limit = self.SUPPORTED_MODELS.get(model_name)
        if max_tokens is not None:
            if max_tokens <= 0:
                raise ValueError(f"max_tokens must be positive, got {max_tokens}")
            if model_limit and max_tokens > model_limit:
                raise ValueError(
                    f"max_tokens ({max_tokens}) exceeds model limit ({model_limit}) "
                    f"for {model_name}"
                )
        self.max_tokens = max_tokens

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)

        # Initialize tokenizer for token counting
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            logger.warning(
                f"Unknown model '{model_name}' for tokenizer, using cl100k_base encoding"
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Example: [{"role": "user", "content": "Hello"}]
            **kwargs: Additional parameters to pass to OpenAI API

        Returns:
            dict containing:
                - content: The response text
                - model: The model used
                - usage: Token usage statistics
                - finish_reason: Why the model stopped generating

        Raises:
            RateLimitExceededError: If rate limit is exceeded
            TokenLimitExceededError: If token limit is exceeded
            OpenAIProviderError: For other API errors
        """
        try:
            # Build request parameters
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
            }
            if self.max_tokens is not None:
                request_params["max_tokens"] = self.max_tokens

            # Merge with any additional kwargs
            request_params.update(kwargs)

            # Make API call
            response = await self.client.chat.completions.create(**request_params)

            # Extract response data
            choice = response.choices[0]
            return {
                "content": choice.message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": choice.finish_reason,
            }

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RateLimitExceededError(f"Rate limit exceeded: {e}")
        except OpenAIError as e:
            error_msg = str(e).lower()
            if "token" in error_msg and "limit" in error_msg:
                logger.error(f"Token limit exceeded: {e}")
                raise TokenLimitExceededError(f"Token limit exceeded: {e}")
            logger.error(f"OpenAI API error: {e}")
            raise OpenAIProviderError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise OpenAIProviderError(f"Unexpected error: {e}")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens in the text
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def get_model_limit(self) -> int | None:
        """
        Get the token limit for the current model.

        Returns:
            Maximum tokens for the model, or None if unknown
        """
        return self.SUPPORTED_MODELS.get(self.model_name)

    def __repr__(self) -> str:
        """String representation of the provider."""
        return (
            f"OpenAIProvider(model={self.model_name}, "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens})"
        )
