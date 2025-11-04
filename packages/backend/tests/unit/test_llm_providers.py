"""Unit tests for LLM provider implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tradingagents.llm_providers import (
    APIKeyMissingError,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
    LLMMessage,
    OpenAIProvider,
    ProviderFactory,
    ProviderType,
)


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @pytest.fixture
    def mock_chat_openai(self):
        """Mock ChatOpenAI client."""
        with patch("tradingagents.llm_providers.openai_provider.ChatOpenAI") as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def provider(self, mock_chat_openai):
        """Create OpenAI provider instance."""
        return OpenAIProvider(api_key="test-key", model_name="gpt-4o-mini", temperature=0.7)

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(APIKeyMissingError):
            OpenAIProvider(api_key="", model_name="gpt-4o-mini")

    def test_init_with_api_key(self, provider):
        """Test successful initialization."""
        assert provider.model_name == "gpt-4o-mini"
        assert provider.temperature == 0.7

    @pytest.mark.asyncio
    async def test_chat(self, provider, mock_chat_openai):
        """Test chat completion."""
        # Mock response
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.response_metadata = {
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        }
        mock_chat_openai.ainvoke = AsyncMock(return_value=mock_response)

        # Test chat
        messages = [LLMMessage(role="user", content="Hello")]
        response = await provider.chat(messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_stream(self, provider, mock_chat_openai):
        """Test streaming completion."""

        # Mock stream chunks
        async def mock_astream(*args, **kwargs):
            for text in ["Hello", " ", "World"]:
                chunk = Mock()
                chunk.content = text
                yield chunk

        mock_chat_openai.astream = mock_astream

        # Test stream
        messages = [LLMMessage(role="user", content="Hello")]
        chunks = []
        async for chunk in provider.stream(messages):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello World"

    def test_count_tokens(self, provider):
        """Test token counting."""
        text = "This is a test"
        tokens = provider.count_tokens(text)
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_health_check(self, provider, mock_chat_openai):
        """Test health check."""
        mock_response = Mock()
        mock_response.content = "pong"
        mock_response.response_metadata = {"token_usage": {}}
        mock_chat_openai.ainvoke = AsyncMock(return_value=mock_response)

        is_healthy = await provider.health_check()
        assert is_healthy is True


class TestDeepSeekProvider:
    """Tests for DeepSeekProvider."""

    @pytest.fixture
    def mock_chat_openai(self):
        """Mock ChatOpenAI client."""
        with patch("tradingagents.llm_providers.deepseek_provider.ChatOpenAI") as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def provider(self, mock_chat_openai):
        """Create DeepSeek provider instance."""
        return DeepSeekProvider(api_key="test-key", model_name="deepseek-chat", temperature=0.7)

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(APIKeyMissingError):
            DeepSeekProvider(api_key="", model_name="deepseek-chat")

    def test_init_with_api_key(self, provider):
        """Test successful initialization."""
        assert provider.model_name == "deepseek-chat"
        assert provider.temperature == 0.7

    @pytest.mark.asyncio
    async def test_chat(self, provider, mock_chat_openai):
        """Test chat completion."""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.response_metadata = {
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        }
        mock_chat_openai.ainvoke = AsyncMock(return_value=mock_response)

        messages = [LLMMessage(role="user", content="Hello")]
        response = await provider.chat(messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 15


class TestGrokProvider:
    """Tests for GrokProvider."""

    @pytest.fixture
    def mock_chat_openai(self):
        """Mock ChatOpenAI client."""
        with patch("tradingagents.llm_providers.grok_provider.ChatOpenAI") as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def provider(self, mock_chat_openai):
        """Create Grok provider instance."""
        return GrokProvider(api_key="test-key", model_name="grok-beta", temperature=0.7)

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(APIKeyMissingError):
            GrokProvider(api_key="", model_name="grok-beta")

    def test_init_with_api_key(self, provider):
        """Test successful initialization."""
        assert provider.model_name == "grok-beta"
        assert provider.temperature == 0.7


class TestClaudeProvider:
    """Tests for ClaudeProvider."""

    @pytest.fixture
    def mock_chat_anthropic(self):
        """Mock ChatAnthropic client."""
        with patch("tradingagents.llm_providers.claude_provider.ChatAnthropic") as mock:
            mock_instance = Mock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_async_anthropic(self):
        """Mock AsyncAnthropic client."""
        with patch("tradingagents.llm_providers.claude_provider.AsyncAnthropic") as mock:
            yield mock

    @pytest.fixture
    def provider(self, mock_chat_anthropic, mock_async_anthropic):
        """Create Claude provider instance."""
        return ClaudeProvider(
            api_key="test-key",
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.7,
        )

    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with pytest.raises(APIKeyMissingError):
            ClaudeProvider(api_key="", model_name="claude-3-5-sonnet-20241022")

    def test_init_with_api_key(self, provider):
        """Test successful initialization."""
        assert provider.model_name == "claude-3-5-sonnet-20241022"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 1024

    @pytest.mark.asyncio
    async def test_chat(self, provider, mock_chat_anthropic):
        """Test chat completion."""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.response_metadata = {"usage": {"input_tokens": 10, "output_tokens": 5}}
        mock_chat_anthropic.ainvoke = AsyncMock(return_value=mock_response)

        messages = [LLMMessage(role="user", content="Hello")]
        response = await provider.chat(messages)

        assert response.content == "Test response"
        assert response.usage["total_tokens"] == 15


class TestProviderFactory:
    """Tests for ProviderFactory."""

    @pytest.fixture
    def mock_providers(self):
        """Mock all provider classes."""
        with (
            patch("tradingagents.llm_providers.openai_provider.OpenAIProvider") as mock_openai,
            patch(
                "tradingagents.llm_providers.deepseek_provider.DeepSeekProvider"
            ) as mock_deepseek,
            patch("tradingagents.llm_providers.grok_provider.GrokProvider") as mock_grok,
            patch("tradingagents.llm_providers.claude_provider.ClaudeProvider") as mock_claude,
        ):
            yield {
                "openai": mock_openai,
                "deepseek": mock_deepseek,
                "grok": mock_grok,
                "claude": mock_claude,
            }

    def test_create_openai_provider(self, mock_providers):
        """Test creating OpenAI provider."""
        ProviderFactory.create_provider(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model_name="gpt-4o-mini",
        )
        mock_providers["openai"].assert_called_once()

    def test_create_provider_from_string(self, mock_providers):
        """Test creating provider from string."""
        ProviderFactory.create_provider(
            provider_type="openai", api_key="test-key", model_name="gpt-4o-mini"
        )
        mock_providers["openai"].assert_called_once()

    def test_list_providers(self):
        """Test listing providers."""
        providers = ProviderFactory.list_providers()
        assert len(providers) == 4
        assert ProviderType.OPENAI in providers
        assert ProviderType.DEEPSEEK in providers
        assert ProviderType.GROK in providers
        assert ProviderType.CLAUDE in providers
