"""Provider factory for creating LLM provider instances."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from tradingagents.llm_providers.registry import ProviderType

if TYPE_CHECKING:
    from tradingagents.llm_providers.base import BaseLLMProvider


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def _get_provider_classes():
        """Get provider class mapping (lazy import for better testability)."""
        from tradingagents.llm_providers.claude_provider import ClaudeProvider
        from tradingagents.llm_providers.deepseek_provider import DeepSeekProvider
        from tradingagents.llm_providers.grok_provider import GrokProvider
        from tradingagents.llm_providers.openai_provider import OpenAIProvider

        return {
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.DEEPSEEK: DeepSeekProvider,
            ProviderType.GROK: GrokProvider,
            ProviderType.CLAUDE: ClaudeProvider,
        }

    @staticmethod
    def create_provider(
        provider_type: Union[ProviderType, str],
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> BaseLLMProvider:
        """Create a provider instance.

        Args:
            provider_type: The provider type (ProviderType enum or string)
            api_key: The API key for the provider
            model_name: The model name to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter

        Returns:
            A provider instance

        Raises:
            ValueError: If provider type is unknown
        """
        if isinstance(provider_type, str):
            try:
                provider_type = ProviderType(provider_type.lower())
            except ValueError:
                raise ValueError(f"Unknown provider: {provider_type}")

        provider_classes = ProviderFactory._get_provider_classes()

        if provider_type not in provider_classes:
            raise ValueError(f"Unknown provider: {provider_type}")

        provider_class = provider_classes[provider_type]
        return provider_class(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

    @staticmethod
    def list_providers() -> list[ProviderType]:
        """List all supported providers."""
        provider_classes = ProviderFactory._get_provider_classes()
        return list(provider_classes.keys())
