"""DeepSeek provider implementation."""

from __future__ import annotations

import os

from tradingagents.llm_providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from tradingagents.llm_providers.exceptions import APIKeyMissingError


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek provider implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ):
        """Initialize DeepSeek provider."""
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError("DeepSeek API key is required")
        
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        """Chat with the model."""
        # Placeholder implementation
        return LLMResponse(
            content="Mock response",
            model=self.model_name,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    async def stream(self, messages: list[LLMMessage]):
        """Stream response from the model."""
        # Placeholder implementation
        yield "Mock"

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        # Rough estimation
        return len(text) // 4

    async def health_check(self) -> bool:
        """Check provider health."""
        return True
