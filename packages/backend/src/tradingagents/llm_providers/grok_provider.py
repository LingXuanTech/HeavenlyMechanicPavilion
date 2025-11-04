"""Grok provider implementation."""

from __future__ import annotations

import os
from typing import AsyncIterator

from langchain_openai import ChatOpenAI

from tradingagents.llm_providers.base import BaseLLMProvider, LLMMessage, LLMResponse
from tradingagents.llm_providers.exceptions import (
    APIKeyMissingError,
    ProviderAPIError,
    RateLimitExceededError,
    TokenLimitExceededError,
)


class GrokProvider(BaseLLMProvider):
    """Grok provider implementation using LangChain with OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "grok-beta",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ):
        """Initialize Grok provider."""
        self.api_key = api_key or os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise APIKeyMissingError("Grok API key is required")

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

        # Initialize LangChain ChatOpenAI with Grok base URL
        self.client = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            base_url="https://api.x.ai/v1",
            model_kwargs={"top_p": self.top_p} if self.top_p else {},
        )

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        """Chat with the model."""
        try:
            # Convert LLMMessage to LangChain format
            lc_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            # Call LangChain ChatOpenAI
            response = await self.client.ainvoke(lc_messages)

            # Extract usage from response metadata
            usage = response.response_metadata.get("token_usage", {})

            return LLMResponse(
                content=response.content,
                model=self.model_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                finish_reason=response.response_metadata.get("finish_reason"),
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "rate_limit" in error_msg:
                raise RateLimitExceededError(f"Grok rate limit exceeded: {e}")
            elif "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"Token limit exceeded: {e}")
            else:
                raise ProviderAPIError(f"Grok API error: {e}")

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        """Stream response from the model."""
        try:
            # Convert LLMMessage to LangChain format
            lc_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            # Stream from LangChain ChatOpenAI
            async for chunk in self.client.astream(lc_messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "rate_limit" in error_msg:
                raise RateLimitExceededError(f"Grok rate limit exceeded: {e}")
            elif "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"Token limit exceeded: {e}")
            else:
                raise ProviderAPIError(f"Grok API error: {e}")

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
