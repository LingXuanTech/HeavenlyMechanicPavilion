"""DeepSeek provider implementation (OpenAI-compatible API)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, List

import tiktoken
from langchain_openai import ChatOpenAI

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .exceptions import (
    APIKeyMissingError,
    ProviderAPIError,
    RateLimitExceededError,
    TokenLimitExceededError,
)

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM provider implementation (OpenAI-compatible)."""

    BASE_URL = "https://api.deepseek.com/v1"
    RATE_LIMIT_DELAY = 1.0

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            model_name: Model name (e.g., "deepseek-chat", "deepseek-coder")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters
        """
        if not api_key:
            raise APIKeyMissingError("DeepSeek API key is required")

        super().__init__(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

        # Use ChatOpenAI with custom base_url for DeepSeek
        self.client = ChatOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"top_p": top_p} if top_p else {},
            **kwargs,
        )

        # Use cl100k_base encoding as fallback
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to DeepSeek.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            LLMResponse: The response from DeepSeek
        """
        retries = kwargs.pop("retries", 3)
        retry_delay = kwargs.pop("retry_delay", self.RATE_LIMIT_DELAY)

        for attempt in range(retries):
            try:
                # Convert messages to LangChain format
                lc_messages = [
                    {"role": msg.role, "content": msg.content} for msg in messages
                ]

                # Invoke the chat model
                response = await self.client.ainvoke(lc_messages, **kwargs)

                # Extract usage information
                usage = {}
                if hasattr(response, "response_metadata"):
                    token_usage = response.response_metadata.get("token_usage", {})
                    usage = {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0),
                    }

                return LLMResponse(
                    content=response.content,
                    model=self.model_name,
                    usage=usage,
                    finish_reason=getattr(response, "finish_reason", None),
                    metadata=getattr(response, "response_metadata", {}),
                )

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limit errors
                if "rate" in error_msg or "429" in error_msg:
                    if attempt < retries - 1:
                        logger.warning(
                            f"Rate limit hit, retrying in {retry_delay}s... "
                            f"(attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise RateLimitExceededError(f"DeepSeek rate limit exceeded: {e}")

                # Check for token limit errors
                if "token" in error_msg and "limit" in error_msg:
                    raise TokenLimitExceededError(f"DeepSeek token limit exceeded: {e}")

                logger.error(f"DeepSeek API error: {e}")
                raise ProviderAPIError(f"DeepSeek API error: {e}")

        raise ProviderAPIError("Max retries exceeded")

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion from DeepSeek.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Yields:
            str: Chunks of response content
        """
        try:
            # Convert messages to LangChain format
            lc_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            # Stream the response
            async for chunk in self.client.astream(lc_messages, **kwargs):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            error_msg = str(e).lower()

            if "rate" in error_msg or "429" in error_msg:
                raise RateLimitExceededError(f"DeepSeek rate limit exceeded: {e}")

            if "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"DeepSeek token limit exceeded: {e}")

            logger.error(f"DeepSeek streaming error: {e}")
            raise ProviderAPIError(f"DeepSeek streaming error: {e}")

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate
            return len(text) // 4

    async def health_check(self) -> bool:
        """Check DeepSeek API health.

        Returns:
            bool: True if healthy
        """
        try:
            test_messages = [LLMMessage(role="user", content="ping")]
            await self.chat(test_messages, max_tokens=5)
            return True
        except Exception as e:
            logger.error(f"DeepSeek health check failed: {e}")
            return False
