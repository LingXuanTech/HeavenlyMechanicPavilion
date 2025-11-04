"""Claude provider implementation."""

from __future__ import annotations

import os
from typing import AsyncIterator

from anthropic import AsyncAnthropic
from langchain_anthropic import ChatAnthropic

from tradingagents.llm_providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from tradingagents.llm_providers.exceptions import (
    APIKeyMissingError,
    ProviderAPIError,
    RateLimitExceededError,
    TokenLimitExceededError,
)


class ClaudeProvider(BaseLLMProvider):
    """Claude provider implementation using LangChain."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ):
        """Initialize Claude provider."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError("Anthropic API key is required")

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens or 1024
        self.top_p = top_p

        # Initialize LangChain ChatAnthropic
        self.client = ChatAnthropic(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Initialize AsyncAnthropic for token counting
        self.async_client = AsyncAnthropic(api_key=self.api_key)

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        """Chat with the model."""
        try:
            # Convert LLMMessage to LangChain format
            lc_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            # Call LangChain ChatAnthropic
            response = await self.client.ainvoke(lc_messages)

            # Extract usage from response metadata
            usage = response.response_metadata.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            return LLMResponse(
                content=response.content,
                model=self.model_name,
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                finish_reason=response.response_metadata.get("stop_reason"),
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "rate_limit" in error_msg:
                raise RateLimitExceededError(f"Claude rate limit exceeded: {e}")
            elif "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"Token limit exceeded: {e}")
            else:
                raise ProviderAPIError(f"Claude API error: {e}")

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """Stream response from the model."""
        try:
            # Convert LLMMessage to LangChain format
            lc_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            # Stream from LangChain ChatAnthropic
            async for chunk in self.client.astream(lc_messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "rate_limit" in error_msg:
                raise RateLimitExceededError(f"Claude rate limit exceeded: {e}")
            elif "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"Token limit exceeded: {e}")
            else:
                raise ProviderAPIError(f"Claude API error: {e}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    async def health_check(self) -> bool:
        """Check provider health."""
        try:
            test_message = [LLMMessage(role="user", content="ping")]
            response = await self.chat(test_message)
            return bool(response.content)
        except Exception:
            return False
