"""Unit tests for Claude (Anthropic) provider adapter."""

from __future__ import annotations

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Provide a lightweight anthropic stub if the SDK is unavailable in the test environment.
if "anthropic" not in sys.modules:  # pragma: no cover - test bootstrap
    anthropic_stub = types.ModuleType("anthropic")

    class _BaseAnthropicError(Exception):
        def __init__(self, message: str = "", status_code: int | None = None, body: object | None = None):
            super().__init__(message)
            self.status_code = status_code
            self.body = body

    class RateLimitError(_BaseAnthropicError):
        pass

    class APIError(_BaseAnthropicError):
        pass

    class APIStatusError(APIError):
        pass

    class AsyncAnthropic:  # pragma: no cover - stub only
        def __init__(self, *args, **kwargs):
            self.messages = SimpleNamespace()

    class Anthropic:  # pragma: no cover - stub only
        def __init__(self, *args, **kwargs):
            self.messages = SimpleNamespace()

    anthropic_stub.AsyncAnthropic = AsyncAnthropic
    anthropic_stub.Anthropic = Anthropic
    anthropic_stub.RateLimitError = RateLimitError
    anthropic_stub.APIError = APIError
    anthropic_stub.APIStatusError = APIStatusError

    sys.modules["anthropic"] = anthropic_stub

from llm_providers import (  # noqa: E402 (import after stub injection)
    ClaudeAPIKeyMissingError,
    ClaudeProvider,
    ClaudeProviderError,
    ClaudeRateLimitExceededError,
    ClaudeTokenLimitExceededError,
)


@pytest.fixture
def anthropic_clients():
    """Patch Anthropic clients used by ClaudeProvider."""

    async_client = Mock()
    async_client.messages = Mock()
    async_client.messages.create = AsyncMock()

    sync_client = Mock()
    sync_client.messages = Mock()
    sync_client.messages.count_tokens = Mock(return_value=SimpleNamespace(input_tokens=12))

    with patch(
        "llm_providers.claude_provider.AsyncAnthropic",
        return_value=async_client,
    ) as mock_async, patch(
        "llm_providers.claude_provider.Anthropic",
        return_value=sync_client,
    ) as mock_sync:
        yield {
            "async_client": async_client,
            "sync_client": sync_client,
            "mock_async_cls": mock_async,
            "mock_sync_cls": mock_sync,
        }


class TestClaudeProviderInit:
    """Tests for ClaudeProvider initialisation."""

    def test_init_with_api_key_parameter(self, anthropic_clients):
        provider = ClaudeProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.model_name == ClaudeProvider.DEFAULT_MODEL
        assert provider.temperature == ClaudeProvider.DEFAULT_TEMPERATURE
        assert provider.max_tokens == ClaudeProvider.DEFAULT_MAX_TOKENS

        anthropic_clients["mock_async_cls"].assert_called_once_with(api_key="test-key")
        anthropic_clients["mock_sync_cls"].assert_called_once_with(api_key="test-key")

    def test_init_with_environment_variable(self, anthropic_clients):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}, clear=True):
            provider = ClaudeProvider()
            assert provider.api_key == "env-key"

    def test_init_without_api_key_raises_error(self, anthropic_clients):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ClaudeAPIKeyMissingError):
                ClaudeProvider()

    def test_init_with_invalid_temperature_raises_error(self, anthropic_clients):
        with pytest.raises(ValueError):
            ClaudeProvider(api_key="test-key", temperature=-0.1)
        with pytest.raises(ValueError):
            ClaudeProvider(api_key="test-key", temperature=1.5)

    def test_init_with_invalid_max_tokens_raises_error(self, anthropic_clients):
        with pytest.raises(ValueError):
            ClaudeProvider(api_key="test-key", max_tokens=0)
        with pytest.raises(ValueError):
            ClaudeProvider(api_key="test-key", max_tokens=-5)

    def test_init_with_max_tokens_above_limit(self, anthropic_clients):
        with pytest.raises(ValueError):
            ClaudeProvider(
                api_key="test-key",
                model_name="claude-3-sonnet-20240229",
                max_tokens=250_000,
            )

    def test_supported_models_defined(self, anthropic_clients):
        assert "claude-3-opus-20240229" in ClaudeProvider.SUPPORTED_MODELS
        assert "claude-3-sonnet-20240229" in ClaudeProvider.SUPPORTED_MODELS
        assert "claude-3-haiku-20240307" in ClaudeProvider.SUPPORTED_MODELS
        assert "claude-3-5-sonnet-20241022" in ClaudeProvider.SUPPORTED_MODELS


class TestClaudeProviderChat:
    """Tests for ClaudeProvider chat interface."""

    @pytest.fixture
    def provider(self, anthropic_clients):
        return ClaudeProvider(api_key="test-key")

    @pytest.fixture
    def mock_response(self):
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Hello from Claude")],
            model="claude-3-5-sonnet-20241022",
            usage=SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
            stop_reason="end_turn",
        )

    @pytest.mark.asyncio
    async def test_chat_basic(self, provider, anthropic_clients, mock_response):
        anthropic_clients["async_client"].messages.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hello"},
        ]
        response = await provider.chat(messages)

        call_kwargs = anthropic_clients["async_client"].messages.create.call_args.kwargs
        assert call_kwargs["model"] == provider.model_name
        assert call_kwargs["temperature"] == provider.temperature
        assert call_kwargs["max_tokens"] == provider.max_tokens
        assert call_kwargs["system"] == "Be helpful."
        assert call_kwargs["messages"] == [
            {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
        ]

        assert response["content"] == "Hello from Claude"
        assert response["model"] == provider.model_name
        assert response["usage"] == {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
        assert response["finish_reason"] == "end_turn"

    @pytest.mark.asyncio
    async def test_chat_combines_multiple_system_messages(
        self, provider, anthropic_clients, mock_response
    ):
        anthropic_clients["async_client"].messages.create.return_value = mock_response

        messages = [
            {"role": "system", "content": "First"},
            {"role": "system", "content": "Second"},
            {"role": "user", "content": "Hello"},
        ]

        await provider.chat(messages)
        call_kwargs = anthropic_clients["async_client"].messages.create.call_args.kwargs
        assert call_kwargs["system"] == "First\nSecond"

    @pytest.mark.asyncio
    async def test_chat_with_overrides(
        self, provider, anthropic_clients, mock_response
    ):
        anthropic_clients["async_client"].messages.create.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        response = await provider.chat(
            messages,
            temperature=0.3,
            max_tokens=256,
            top_p=0.9,
        )

        call_kwargs = anthropic_clients["async_client"].messages.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["top_p"] == 0.9
        assert response["content"] == "Hello from Claude"

    @pytest.mark.asyncio
    async def test_chat_requires_non_system_messages(self, provider):
        with pytest.raises(ValueError):
            await provider.chat([{"role": "system", "content": "Only system"}])

    @pytest.mark.asyncio
    async def test_chat_rejects_unsupported_roles(self, provider):
        with pytest.raises(ValueError):
            await provider.chat([{"role": "tool", "content": "content"}])

    @pytest.mark.asyncio
    async def test_chat_rate_limit_error(self, provider, anthropic_clients):
        from llm_providers.claude_provider import RateLimitError

        anthropic_clients["async_client"].messages.create.side_effect = RateLimitError(
            "Rate limit exceeded",
            status_code=429,
        )

        with patch("llm_providers.claude_provider.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
            with pytest.raises(ClaudeRateLimitExceededError):
                await provider.chat(
                    [{"role": "user", "content": "Hello"}],
                    retries=2,
                )

        assert anthropic_clients["async_client"].messages.create.await_count == 2
        sleep_mock.assert_awaited()

    @pytest.mark.asyncio
    async def test_chat_token_limit_error(self, provider, anthropic_clients):
        from llm_providers.claude_provider import APIError

        anthropic_clients["async_client"].messages.create.side_effect = APIError(
            "Maximum tokens exceeded",
        )

        with pytest.raises(ClaudeTokenLimitExceededError):
            await provider.chat([{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_chat_generic_api_error(self, provider, anthropic_clients):
        from llm_providers.claude_provider import APIError

        anthropic_clients["async_client"].messages.create.side_effect = APIError(
            "Something went wrong",
        )

        with pytest.raises(ClaudeProviderError):
            await provider.chat([{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_chat_unexpected_error(self, provider, anthropic_clients):
        anthropic_clients["async_client"].messages.create.side_effect = ValueError(
            "Unexpected issue"
        )

        with pytest.raises(ClaudeProviderError):
            await provider.chat([{"role": "user", "content": "Hello"}])


class TestClaudeProviderTokenCounting:
    """Tests for ClaudeProvider token counting."""

    @pytest.fixture
    def provider(self, anthropic_clients):
        return ClaudeProvider(api_key="test-key")

    def test_count_tokens_success(self, provider, anthropic_clients):
        anthropic_clients["sync_client"].messages.count_tokens.return_value = SimpleNamespace(
            input_tokens=42
        )
        assert provider.count_tokens("Hello Claude") == 42

    def test_count_tokens_with_dict_response(self, provider, anthropic_clients):
        anthropic_clients["sync_client"].messages.count_tokens.return_value = {
            "input_tokens": 21,
        }
        assert provider.count_tokens("Hello Claude") == 21

    def test_count_tokens_empty_string(self, provider, anthropic_clients):
        assert provider.count_tokens("") == 0

    def test_count_tokens_fallback_on_error(self, provider, anthropic_clients):
        anthropic_clients["sync_client"].messages.count_tokens.side_effect = RuntimeError(
            "Counting failed"
        )
        text = "fallback text"
        assert provider.count_tokens(text) == len(text) // 4


class TestClaudeProviderHelpers:
    """Tests for helper methods."""

    @pytest.fixture
    def provider(self, anthropic_clients):
        return ClaudeProvider(api_key="test-key", model_name="claude-3-opus-20240229")

    def test_get_model_limit(self, provider):
        assert provider.get_model_limit() == ClaudeProvider.SUPPORTED_MODELS[
            "claude-3-opus-20240229"
        ]

    def test_repr(self, provider):
        repr_str = repr(provider)
        assert "ClaudeProvider" in repr_str
        assert "claude-3-opus-20240229" in repr_str
