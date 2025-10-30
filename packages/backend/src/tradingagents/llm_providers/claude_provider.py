"""Claude (Anthropic) provider implementation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, List

from anthropic import AsyncAnthropic
from langchain_anthropic import ChatAnthropic

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .exceptions import (
    APIKeyMissingError,
    ProviderAPIError,
    RateLimitExceededError,
    TokenLimitExceededError,
)

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Claude (Anthropic) LLM provider implementation."""

    RATE_LIMIT_DELAY = 1.0

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int | None = 1024,
        top_p: float | None = None,
        **kwargs: Any,
    ):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model_name: Model name (e.g., "claude-3-5-sonnet-20241022", "claude-3-opus-20240229")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate (required for Claude)
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters
        """
        if not api_key:
            raise APIKeyMissingError("Anthropic API key is required")

        # Claude requires max_tokens to be set
        if max_tokens is None:
            max_tokens = 1024

        super().__init__(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

        self.client = ChatAnthropic(
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

        # For token counting
        self.anthropic_client = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to Claude.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            LLMResponse: The response from Claude
        """
        retries = kwargs.pop("retries", 3)
        retry_delay = kwargs.pop("retry_delay", self.RATE_LIMIT_DELAY)

        for attempt in range(retries):
            try:
                # Convert messages to LangChain format
                # Note: Claude requires system messages to be separated
                system_message = None
                user_messages = []

                for msg in messages:
                    if msg.role == "system":
                        system_message = msg.content
                    else:
                        user_messages.append({"role": msg.role, "content": msg.content})

                # Add system message as kwarg if present
                invoke_kwargs = kwargs.copy()
                if system_message:
                    # For LangChain Anthropic, system message is handled differently
                    # We'll prepend it to the first user message or add as separate parameter
                    user_messages = [{"role": "system", "content": system_message}] + user_messages

                # Invoke the chat model
                response = await self.client.ainvoke(user_messages, **invoke_kwargs)

                # Extract usage information
                usage = {}
                if hasattr(response, "response_metadata"):
                    usage_data = response.response_metadata.get("usage", {})
                    usage = {
                        "prompt_tokens": usage_data.get("input_tokens", 0),
                        "completion_tokens": usage_data.get("output_tokens", 0),
                        "total_tokens": usage_data.get("input_tokens", 0)
                        + usage_data.get("output_tokens", 0),
                    }

                return LLMResponse(
                    content=response.content,
                    model=self.model_name,
                    usage=usage,
                    finish_reason=getattr(response, "stop_reason", None),
                    metadata=getattr(response, "response_metadata", {}),
                )

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limit errors
                if "rate" in error_msg or "429" in error_msg or "overloaded" in error_msg:
                    if attempt < retries - 1:
                        logger.warning(
                            f"Rate limit hit, retrying in {retry_delay}s... "
                            f"(attempt {attempt + 1}/{retries})"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise RateLimitExceededError(f"Claude rate limit exceeded: {e}")

                # Check for token limit errors
                if "token" in error_msg and ("limit" in error_msg or "maximum" in error_msg):
                    raise TokenLimitExceededError(f"Claude token limit exceeded: {e}")

                logger.error(f"Claude API error: {e}")
                raise ProviderAPIError(f"Claude API error: {e}")

        raise ProviderAPIError("Max retries exceeded")

    async def stream(
        self,
        messages: List[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Claude.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Yields:
            str: Chunks of response content
        """
        try:
            # Convert messages to LangChain format
            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    user_messages.append({"role": msg.role, "content": msg.content})

            invoke_kwargs = kwargs.copy()
            if system_message:
                user_messages = [{"role": "system", "content": system_message}] + user_messages

            # Stream the response
            async for chunk in self.client.astream(user_messages, **invoke_kwargs):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            error_msg = str(e).lower()

            if "rate" in error_msg or "429" in error_msg or "overloaded" in error_msg:
                raise RateLimitExceededError(f"Claude rate limit exceeded: {e}")

            if "token" in error_msg and ("limit" in error_msg or "maximum" in error_msg):
                raise TokenLimitExceededError(f"Claude token limit exceeded: {e}")

            logger.error(f"Claude streaming error: {e}")
            raise ProviderAPIError(f"Claude streaming error: {e}")

    def count_tokens(self, text: str) -> int:
        """Count tokens using Anthropic's token counting.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens
        """
        try:
            # Use Anthropic's token counting
            # This is a synchronous approximation
            # For more accurate counting, use the Anthropic client's count_tokens method
            # Rough estimate: 1 token ≈ 4 characters for Claude
            return len(text) // 4
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return len(text) // 4

    async def health_check(self) -> bool:
        """Check Claude API health.

        Returns:
            bool: True if healthy
        """
        try:
            test_messages = [LLMMessage(role="user", content="ping")]
            await self.chat(test_messages, max_tokens=5)
            return True
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False
