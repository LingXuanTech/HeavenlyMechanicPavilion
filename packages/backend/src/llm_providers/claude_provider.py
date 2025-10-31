"""Claude (Anthropic) provider adapter with configuration support."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

try:  # pragma: no cover - handled in __init__
    from anthropic import Anthropic, APIError, APIStatusError, AsyncAnthropic, RateLimitError
except ImportError as exc:  # pragma: no cover - handled in __init__
    Anthropic = AsyncAnthropic = None  # type: ignore[assignment]

    class _AnthropicSDKMissingError(Exception):
        """Placeholder error when Anthropic SDK is unavailable."""

    APIError = APIStatusError = RateLimitError = _AnthropicSDKMissingError  # type: ignore[assignment]
    _anthropic_import_error = exc
else:  # pragma: no cover - trivial branch
    _anthropic_import_error = None


logger = logging.getLogger(__name__)


class ClaudeProviderError(Exception):
    """Base exception for Claude provider errors."""

    pass


class ClaudeAPIKeyMissingError(ClaudeProviderError):
    """Raised when the Anthropic API key is missing."""

    pass


class ClaudeRateLimitExceededError(ClaudeProviderError):
    """Raised when the Anthropic API rate limit is exceeded."""

    pass


class ClaudeTokenLimitExceededError(ClaudeProviderError):
    """Raised when a request exceeds Claude's token limits."""

    pass


class ClaudeProvider:
    """
    Claude (Anthropic) provider adapter with configuration and error handling.

    This class mirrors the OpenAI provider adapter, offering Anthropic-specific
    message formatting, retries, and token counting support.
    """

    SUPPORTED_MODELS: dict[str, int | None] = {
        "claude-3-opus-20240229": 200_000,
        "claude-3-sonnet-20240229": 200_000,
        "claude-3-haiku-20240307": 200_000,
        "claude-3-5-sonnet-20241022": 200_000,
    }
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024
    MIN_TEMPERATURE = 0.0
    MAX_TEMPERATURE = 1.0
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF_SECONDS = 1.0

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialise the Claude provider."""

        if AsyncAnthropic is None or Anthropic is None:  # pragma: no cover - installation guard
            raise ImportError(
                "The 'anthropic' package is required to use ClaudeProvider. "
                "Install anthropic>=0.31.0 to continue."
            ) from _anthropic_import_error

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ClaudeAPIKeyMissingError(
                "Anthropic API key is required. Provide it via parameter or set "
                "ANTHROPIC_API_KEY environment variable."
            )

        if model_name not in self.SUPPORTED_MODELS:
            logger.warning(
                "Model '%s' not in supported Claude models list. Supported: %s",
                model_name,
                list(self.SUPPORTED_MODELS.keys()),
            )
        self.model_name = model_name

        if not self.MIN_TEMPERATURE <= temperature <= self.MAX_TEMPERATURE:
            raise ValueError(
                "Temperature must be between "
                f"{self.MIN_TEMPERATURE} and {self.MAX_TEMPERATURE}, got {temperature}"
            )
        self.temperature = temperature

        validated_max_tokens = self._validate_max_tokens(max_tokens)
        self.max_tokens = validated_max_tokens

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if timeout is not None:
            client_kwargs["timeout"] = timeout

        self.client = AsyncAnthropic(**client_kwargs)
        self.sync_client = Anthropic(**client_kwargs)

        self.max_retries = self.DEFAULT_RETRIES
        self.retry_backoff = self.DEFAULT_BACKOFF_SECONDS

    async def chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat completion request to Claude.

        Args:
            messages: List of chat messages with role/content keys.
            **kwargs: Additional parameters forwarded to Anthropic API.

        Returns:
            dict containing content, model, usage statistics, and finish reason.
        """

        retry_param = kwargs.pop("retries", self.max_retries)
        retry_delay = kwargs.pop("retry_delay", self.retry_backoff)
        try:
            retry_count = int(retry_param)
        except (TypeError, ValueError):
            retry_count = self.max_retries
        retry_count = max(retry_count, 1)

        request_temperature = kwargs.pop("temperature", self.temperature)
        if not self.MIN_TEMPERATURE <= request_temperature <= self.MAX_TEMPERATURE:
            raise ValueError(
                "Temperature must be between "
                f"{self.MIN_TEMPERATURE} and {self.MAX_TEMPERATURE}, "
                f"got {request_temperature}"
            )

        request_max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        validated_max_tokens = self._validate_max_tokens(request_max_tokens)

        system_prompt, formatted_messages = self._prepare_messages(messages)

        request_params: dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": validated_max_tokens,
            "temperature": request_temperature,
            "messages": formatted_messages,
        }
        if system_prompt:
            request_params["system"] = system_prompt
        request_params.update(kwargs)

        last_error: Exception | None = None
        for attempt in range(retry_count):
            try:
                response = await self.client.messages.create(**request_params)
                return self._build_response(response)
            except RateLimitError as exc:  # type: ignore[misc]
                last_error = exc
                logger.warning(
                    "Claude rate limit encountered on attempt %s/%s: %s",
                    attempt + 1,
                    retry_count,
                    exc,
                )
                if attempt == retry_count - 1:
                    raise ClaudeRateLimitExceededError(
                        f"Claude rate limit exceeded: {exc}"
                    ) from exc
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except (APIStatusError, APIError) as exc:  # type: ignore[misc]
                last_error = exc
                if self._is_token_limit_error(exc):
                    logger.error("Claude token limit exceeded: %s", exc)
                    raise ClaudeTokenLimitExceededError(
                        f"Claude token limit exceeded: {exc}"
                    ) from exc
                logger.error("Claude API error: %s", exc)
                raise ClaudeProviderError(f"Claude API error: {exc}") from exc
            except Exception as exc:  # pragma: no cover - safety net
                last_error = exc
                logger.error("Unexpected Claude provider error: %s", exc)
                raise ClaudeProviderError(f"Unexpected Claude provider error: {exc}") from exc

        raise ClaudeProviderError("Claude chat request failed after retries") from last_error

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string using Anthropic's API."""

        if not text:
            return 0

        try:
            result = self.sync_client.messages.count_tokens(  # type: ignore[union-attr]
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": self._format_content(text),
                    }
                ],
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logger.error("Error counting tokens with Claude: %s", exc)
            return len(text) // 4

        return self._extract_input_tokens(result, default=len(text) // 4)

    def get_model_limit(self) -> int | None:
        """Return the model's maximum context window."""

        return self.SUPPORTED_MODELS.get(self.model_name)

    def __repr__(self) -> str:  # pragma: no cover - trivial representation
        return "ClaudeProvider(model={model}, temperature={temp}, max_tokens={tokens})".format(
            model=self.model_name,
            temp=self.temperature,
            tokens=self.max_tokens,
        )

    def _validate_max_tokens(self, value: int | None) -> int:
        if value is None:
            value = self.DEFAULT_MAX_TOKENS

        if value <= 0:
            raise ValueError(f"max_tokens must be positive, got {value}")

        model_limit = self.SUPPORTED_MODELS.get(self.model_name)
        if model_limit is not None and value > model_limit:
            raise ValueError(
                f"max_tokens ({value}) exceeds model limit ({model_limit}) for {self.model_name}"
            )

        return value

    def _prepare_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[str | None, list[dict[str, Any]]]:
        if not messages:
            raise ValueError("ClaudeProvider requires at least one message.")

        system_prompt: str | None = None
        formatted_messages: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role")
            if role is None:
                raise ValueError("Each message must include a 'role'.")

            content = message.get("content", "")

            if role == "system":
                system_prompt = f"{system_prompt}\n{content}" if system_prompt else str(content)
                continue

            if role not in {"user", "assistant"}:
                raise ValueError(f"Unsupported role '{role}' for Claude messages.")

            formatted_messages.append(
                {
                    "role": role,
                    "content": self._format_content(content),
                }
            )

        if not formatted_messages:
            raise ValueError("ClaudeProvider requires at least one non-system message.")

        return system_prompt, formatted_messages

    def _format_content(self, content: Any) -> list[dict[str, Any]]:
        if isinstance(content, list):
            if all(isinstance(item, str) for item in content):
                return [
                    {
                        "type": "text",
                        "text": item,
                    }
                    for item in content
                ]
            return content

        if isinstance(content, str):
            text_value = content
        else:
            text_value = str(content)

        return [{"type": "text", "text": text_value}]

    def _build_response(self, response: Any) -> dict[str, Any]:
        content = self._extract_text(response)
        usage = self._extract_usage(response)
        return {
            "content": content,
            "model": getattr(response, "model", self.model_name),
            "usage": usage,
            "finish_reason": getattr(response, "stop_reason", None),
        }

    def _extract_text(self, response: Any) -> str:
        content_blocks = getattr(response, "content", [])
        parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict):
                text = block.get("text") or block.get("value")
            else:
                text = getattr(block, "text", None) or getattr(block, "value", None)
            if text:
                parts.append(text)
        return "".join(parts)

    def _extract_usage(self, response: Any) -> dict[str, int]:
        usage_data = getattr(response, "usage", None)
        prompt_tokens = self._extract_input_tokens(usage_data, default=0)
        completion_tokens = self._extract_output_tokens(usage_data, default=0)
        total_tokens = self._extract_total_tokens(usage_data)

        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        return {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
        }

    def _extract_input_tokens(self, usage: Any, default: int) -> int:
        if usage is None:
            return default
        if isinstance(usage, dict):
            value = usage.get("input_tokens") or usage.get("prompt_tokens")
        else:
            value = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
        return int(value) if value is not None else default

    def _extract_output_tokens(self, usage: Any, default: int) -> int:
        if usage is None:
            return default
        if isinstance(usage, dict):
            value = usage.get("output_tokens") or usage.get("completion_tokens")
        else:
            value = getattr(usage, "output_tokens", None) or getattr(
                usage, "completion_tokens", None
            )
        return int(value) if value is not None else default

    def _extract_total_tokens(self, usage: Any) -> int | None:
        if usage is None:
            return None
        if isinstance(usage, dict):
            value = usage.get("total_tokens")
        else:
            value = getattr(usage, "total_tokens", None)
        return int(value) if value is not None else None

    def _is_token_limit_error(self, error: Exception) -> bool:
        message = str(error).lower()
        if "token" in message and ("limit" in message or "max" in message):
            return True

        body = getattr(error, "body", None)
        if isinstance(body, dict):
            error_obj = body.get("error")
            if isinstance(error_obj, dict):
                nested_message = str(error_obj.get("message", "")).lower()
                if "token" in nested_message and (
                    "limit" in nested_message or "max" in nested_message
                ):
                    return True

        return False
