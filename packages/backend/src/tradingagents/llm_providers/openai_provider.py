"""OpenAI provider implementation."""

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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""

    RATE_LIMIT_DELAY = 1.0  # seconds between retries

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model_name: Model name (e.g., "gpt-4o-mini", "gpt-4o")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters
        """
        if not api_key:
            raise APIKeyMissingError("OpenAI API key is required")

        super().__init__(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

        self.client = ChatOpenAI(
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs={"top_p": top_p} if top_p else {},
            **kwargs,
        )

        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to OpenAI.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            LLMResponse: The response from OpenAI
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
                        retry_delay *= 2  # Exponential backoff
                        continue
                    raise RateLimitExceededError(f"OpenAI rate limit exceeded: {e}")

                # Check for token limit errors
                if "token" in error_msg and "limit" in error_msg:
                    raise TokenLimitExceededError(f"OpenAI token limit exceeded: {e}")

                # Generic API error
                logger.error(f"OpenAI API error: {e}")
                raise ProviderAPIError(f"OpenAI API error: {e}")

        raise ProviderAPIError("Max retries exceeded")

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion from OpenAI.

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
                raise RateLimitExceededError(f"OpenAI rate limit exceeded: {e}")

            if "token" in error_msg and "limit" in error_msg:
                raise TokenLimitExceededError(f"OpenAI token limit exceeded: {e}")

            logger.error(f"OpenAI streaming error: {e}")
            raise ProviderAPIError(f"OpenAI streaming error: {e}")

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
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    async def health_check(self) -> bool:
        """Check OpenAI API health.

        Returns:
            bool: True if healthy
        """
        try:
            test_messages = [LLMMessage(role="user", content="ping")]
            await self.chat(test_messages, max_tokens=5)
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
