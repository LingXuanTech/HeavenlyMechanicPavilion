"""Base abstract class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel


class LLMMessage(BaseModel):
    """Standard message format for LLM communication."""

    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Standard response format from LLM providers."""

    content: str
    model: str
    usage: Dict[str, int]  # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs: Any,
    ):
        """Initialize the provider.

        Args:
            api_key: API key for authentication
            model_name: Name of the model to use
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.kwargs = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the request

        Returns:
            LLMResponse: The response from the LLM

        Raises:
            ProviderAPIError: If the API request fails
            RateLimitExceededError: If rate limit is exceeded
            TokenLimitExceededError: If token limit is exceeded
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.

        Args:
            messages: List of messages in the conversation
            **kwargs: Additional parameters for the request

        Yields:
            str: Chunks of the response content

        Raises:
            ProviderAPIError: If the API request fails
            RateLimitExceededError: If rate limit is exceeded
            TokenLimitExceededError: If token limit is exceeded
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text.

        Args:
            text: The text to count tokens for

        Returns:
            int: The number of tokens
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible.

        Returns:
            bool: True if healthy, False otherwise
        """
        pass

    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: The provider name
        """
        return self.__class__.__name__.replace("Provider", "").lower()

    def get_model_name(self) -> str:
        """Get the model name.

        Returns:
            str: The model name
        """
        return self.model_name
