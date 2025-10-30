"""Unit tests for OpenAI provider adapter."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from llm_providers import (
    APIKeyMissingError,
    OpenAIProvider,
    OpenAIProviderError,
    RateLimitExceededError,
    TokenLimitExceededError,
)


class TestOpenAIProviderInit:
    """Tests for OpenAIProvider initialization."""

    def test_init_with_api_key_parameter(self):
        """Test initialization with API key parameter."""
        provider = OpenAIProvider(api_key="test-key-123")
        assert provider.api_key == "test-key-123"
        assert provider.model_name == "gpt-4o-mini"
        assert provider.temperature == 0.7
        assert provider.max_tokens is None

    def test_init_with_environment_variable(self):
        """Test initialization with API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-456"}):
            provider = OpenAIProvider()
            assert provider.api_key == "env-key-456"

    def test_init_without_api_key_raises_error(self):
        """Test initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(APIKeyMissingError) as exc_info:
                OpenAIProvider()
            assert "API key is required" in str(exc_info.value)

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        provider = OpenAIProvider(
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            api_key="test-key",
        )
        assert provider.model_name == "gpt-4"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 1000

    def test_init_with_invalid_temperature_raises_error(self):
        """Test initialization with invalid temperature."""
        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider(temperature=-0.1, api_key="test-key")
        assert "Temperature must be between" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider(temperature=2.5, api_key="test-key")
        assert "Temperature must be between" in str(exc_info.value)

    def test_init_with_invalid_max_tokens_raises_error(self):
        """Test initialization with invalid max_tokens."""
        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider(max_tokens=-100, api_key="test-key")
        assert "max_tokens must be positive" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider(max_tokens=0, api_key="test-key")
        assert "max_tokens must be positive" in str(exc_info.value)

    def test_init_with_max_tokens_exceeding_model_limit(self):
        """Test initialization with max_tokens exceeding model limit."""
        with pytest.raises(ValueError) as exc_info:
            OpenAIProvider(
                model_name="gpt-3.5-turbo",
                max_tokens=20000,
                api_key="test-key",
            )
        assert "exceeds model limit" in str(exc_info.value)

    def test_supported_models(self):
        """Test that supported models are defined."""
        assert "gpt-4" in OpenAIProvider.SUPPORTED_MODELS
        assert "gpt-4-turbo" in OpenAIProvider.SUPPORTED_MODELS
        assert "gpt-3.5-turbo" in OpenAIProvider.SUPPORTED_MODELS
        assert "gpt-4o-mini" in OpenAIProvider.SUPPORTED_MODELS


class TestOpenAIProviderChat:
    """Tests for OpenAIProvider chat method."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing."""
        return OpenAIProvider(api_key="test-key", model_name="gpt-4o-mini")

    @pytest.fixture
    def mock_completion(self):
        """Create a mock completion response."""
        mock_response = Mock()
        mock_response.model = "gpt-4o-mini"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! How can I help you?"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 8
        mock_response.usage.total_tokens = 18
        return mock_response

    @pytest.mark.asyncio
    async def test_chat_basic(self, provider, mock_completion):
        """Test basic chat completion."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_completion,
        ) as mock_create:
            messages = [{"role": "user", "content": "Hello"}]
            response = await provider.chat(messages)

            # Verify API was called correctly
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["messages"] == messages
            assert call_kwargs["temperature"] == 0.7

            # Verify response structure
            assert response["content"] == "Hello! How can I help you?"
            assert response["model"] == "gpt-4o-mini"
            assert response["usage"]["prompt_tokens"] == 10
            assert response["usage"]["completion_tokens"] == 8
            assert response["usage"]["total_tokens"] == 18
            assert response["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_max_tokens(self, mock_completion):
        """Test chat with max_tokens parameter."""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-4o-mini",
            max_tokens=100,
        )

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_completion,
        ) as mock_create:
            messages = [{"role": "user", "content": "Hello"}]
            await provider.chat(messages)

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_chat_with_additional_kwargs(self, provider, mock_completion):
        """Test chat with additional parameters."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_completion,
        ) as mock_create:
            messages = [{"role": "user", "content": "Hello"}]
            await provider.chat(messages, top_p=0.9, frequency_penalty=0.5)

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["top_p"] == 0.9
            assert call_kwargs["frequency_penalty"] == 0.5

    @pytest.mark.asyncio
    async def test_chat_rate_limit_error(self, provider):
        """Test chat with rate limit error."""
        from openai import RateLimitError

        mock_error = RateLimitError(
            "Rate limit exceeded",
            response=Mock(status_code=429),
            body=None,
        )

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=mock_error,
        ):
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(RateLimitExceededError) as exc_info:
                await provider.chat(messages)
            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_token_limit_error(self, provider):
        """Test chat with token limit error."""
        from openai import OpenAIError

        mock_error = OpenAIError("Token limit exceeded for this request")

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=mock_error,
        ):
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(TokenLimitExceededError) as exc_info:
                await provider.chat(messages)
            assert "Token limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_generic_openai_error(self, provider):
        """Test chat with generic OpenAI error."""
        from openai import OpenAIError

        mock_error = OpenAIError("Something went wrong")

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=mock_error,
        ):
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(OpenAIProviderError) as exc_info:
                await provider.chat(messages)
            assert "OpenAI API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_unexpected_error(self, provider):
        """Test chat with unexpected error."""
        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=ValueError("Unexpected issue"),
        ):
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(OpenAIProviderError) as exc_info:
                await provider.chat(messages)
            assert "Unexpected error" in str(exc_info.value)


class TestOpenAIProviderTokenCounting:
    """Tests for OpenAIProvider token counting."""

    @pytest.fixture
    def provider(self):
        """Create a provider instance for testing."""
        return OpenAIProvider(api_key="test-key")

    def test_count_tokens_basic(self, provider):
        """Test basic token counting."""
        text = "Hello, how are you?"
        token_count = provider.count_tokens(text)
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_empty_string(self, provider):
        """Test token counting with empty string."""
        token_count = provider.count_tokens("")
        assert token_count == 0

    def test_count_tokens_long_text(self, provider):
        """Test token counting with long text."""
        text = " ".join(["word"] * 1000)
        token_count = provider.count_tokens(text)
        assert token_count > 0
        # Should be roughly 1000 tokens (one token per word approximately)
        assert 500 < token_count < 1500

    def test_count_tokens_with_encoding_error(self, provider):
        """Test token counting fallback when encoding fails."""
        with patch.object(provider.encoding, "encode", side_effect=Exception("Encoding error")):
            text = "This is a test"
            token_count = provider.count_tokens(text)
            # Should use fallback (len / 4)
            assert token_count == len(text) // 4


class TestOpenAIProviderHelpers:
    """Tests for OpenAIProvider helper methods."""

    def test_get_model_limit(self):
        """Test getting model token limit."""
        provider = OpenAIProvider(api_key="test-key", model_name="gpt-4")
        limit = provider.get_model_limit()
        assert limit == 8192

        provider = OpenAIProvider(api_key="test-key", model_name="gpt-4-turbo")
        limit = provider.get_model_limit()
        assert limit == 128000

        provider = OpenAIProvider(api_key="test-key", model_name="gpt-3.5-turbo")
        limit = provider.get_model_limit()
        assert limit == 16385

    def test_repr(self):
        """Test string representation."""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=1000,
        )
        repr_str = repr(provider)
        assert "OpenAIProvider" in repr_str
        assert "gpt-4" in repr_str
        assert "0.5" in repr_str
        assert "1000" in repr_str


class TestOpenAIProviderModelConfigurations:
    """Tests for different model configurations."""

    @pytest.mark.asyncio
    async def test_gpt4_configuration(self):
        """Test GPT-4 model configuration."""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-4",
            temperature=0.3,
        )
        assert provider.model_name == "gpt-4"
        assert provider.temperature == 0.3

    @pytest.mark.asyncio
    async def test_gpt4_turbo_configuration(self):
        """Test GPT-4 Turbo model configuration."""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-4-turbo",
            temperature=0.8,
        )
        assert provider.model_name == "gpt-4-turbo"
        assert provider.temperature == 0.8

    @pytest.mark.asyncio
    async def test_gpt35_turbo_configuration(self):
        """Test GPT-3.5 Turbo model configuration."""
        provider = OpenAIProvider(
            api_key="test-key",
            model_name="gpt-3.5-turbo",
            temperature=1.0,
        )
        assert provider.model_name == "gpt-3.5-turbo"
        assert provider.temperature == 1.0

    def test_unsupported_model_warning(self):
        """Test that unsupported models log a warning but still work."""
        with patch("llm_providers.openai_provider.logger") as mock_logger:
            provider = OpenAIProvider(
                api_key="test-key",
                model_name="gpt-5-hypothetical",
            )
            assert provider.model_name == "gpt-5-hypothetical"
            # Should log a warning
            mock_logger.warning.assert_called()
