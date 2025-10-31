"""Unit tests for provider registry."""

from __future__ import annotations

import pytest
from tradingagents.llm_providers.registry import (
    PROVIDER_REGISTRY,
    ProviderType,
    calculate_cost,
    get_model_info,
    get_provider_info,
    list_models,
    list_providers,
)


class TestProviderRegistry:
    """Tests for provider registry."""

    def test_list_providers(self):
        """Test listing all providers."""
        providers = list_providers()
        assert len(providers) == 4
        assert ProviderType.OPENAI in providers
        assert ProviderType.DEEPSEEK in providers
        assert ProviderType.GROK in providers
        assert ProviderType.CLAUDE in providers

    def test_get_provider_info_openai(self):
        """Test getting OpenAI provider info."""
        info = get_provider_info(ProviderType.OPENAI)
        assert info.name == "OpenAI"
        assert info.provider_type == ProviderType.OPENAI
        assert info.base_url is None
        assert len(info.models) > 0

    def test_get_provider_info_deepseek(self):
        """Test getting DeepSeek provider info."""
        info = get_provider_info(ProviderType.DEEPSEEK)
        assert info.name == "DeepSeek"
        assert info.base_url == "https://api.deepseek.com/v1"

    def test_get_provider_info_invalid(self):
        """Test getting invalid provider raises error."""
        with pytest.raises(ValueError):
            get_provider_info("invalid")

    def test_list_models_openai(self):
        """Test listing OpenAI models."""
        models = list_models(ProviderType.OPENAI)
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    def test_list_models_claude(self):
        """Test listing Claude models."""
        models = list_models(ProviderType.CLAUDE)
        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models

    def test_get_model_info_openai(self):
        """Test getting OpenAI model info."""
        model_info = get_model_info(ProviderType.OPENAI, "gpt-4o-mini")
        assert model_info.name == "gpt-4o-mini"
        assert model_info.context_window == 128000
        assert model_info.supports_streaming is True
        assert model_info.cost_per_1k_input_tokens > 0

    def test_get_model_info_invalid_model(self):
        """Test getting invalid model raises error."""
        with pytest.raises(ValueError):
            get_model_info(ProviderType.OPENAI, "invalid-model")

    def test_calculate_cost(self):
        """Test cost calculation."""
        cost = calculate_cost(
            provider_type=ProviderType.OPENAI,
            model_name="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        assert cost > 0
        # gpt-4o-mini: $0.00015 per 1K input, $0.0006 per 1K output
        expected_cost = (1000 / 1000) * 0.00015 + (500 / 1000) * 0.0006
        assert abs(cost - expected_cost) < 0.0001

    def test_model_capabilities(self):
        """Test model capabilities."""
        # Test vision support
        gpt4o = get_model_info(ProviderType.OPENAI, "gpt-4o")
        assert gpt4o.supports_vision is True

        deepseek = get_model_info(ProviderType.DEEPSEEK, "deepseek-chat")
        assert deepseek.supports_vision is False

        # Test function calling
        claude = get_model_info(ProviderType.CLAUDE, "claude-3-5-sonnet-20241022")
        assert claude.supports_function_calling is True

    def test_all_providers_have_models(self):
        """Test that all providers have at least one model."""
        for provider_type in PROVIDER_REGISTRY:
            info = get_provider_info(provider_type)
            assert len(info.models) > 0
            for model_name, model_info in info.models.items():
                assert model_info.name == model_name
                assert model_info.context_window > 0
                assert model_info.cost_per_1k_input_tokens >= 0
                assert model_info.cost_per_1k_output_tokens >= 0
