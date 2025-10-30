"""Factory for creating LLM provider instances."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import BaseLLMProvider
from .claude_provider import ClaudeProvider
from .deepseek_provider import DeepSeekProvider
from .exceptions import ProviderNotFoundError
from .grok_provider import GrokProvider
from .openai_provider import OpenAIProvider
from .registry import ProviderType

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating LLM provider instances."""

    _provider_classes = {
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.DEEPSEEK: DeepSeekProvider,
        ProviderType.GROK: GrokProvider,
        ProviderType.CLAUDE: ClaudeProvider,
    }

    @classmethod
    def create_provider(
        cls,
        provider_type: ProviderType | str,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseLLMProvider:
        """Create a provider instance.

        Args:
            provider_type: The type of provider to create
            api_key: API key for the provider
            model_name: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters

        Returns:
            BaseLLMProvider: The created provider instance

        Raises:
            ProviderNotFoundError: If the provider type is not supported
        """
        # Convert string to ProviderType if necessary
        if isinstance(provider_type, str):
            try:
                provider_type = ProviderType(provider_type.lower())
            except ValueError:
                raise ProviderNotFoundError(
                    f"Provider '{provider_type}' not found. "
                    f"Available providers: {[p.value for p in ProviderType]}"
                )

        provider_class = cls._provider_classes.get(provider_type)
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider {provider_type} not found. "
                f"Available providers: {list(cls._provider_classes.keys())}"
            )

        logger.info(f"Creating {provider_type} provider with model {model_name}")
        return provider_class(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs,
        )

    @classmethod
    def register_provider(
        cls,
        provider_type: ProviderType,
        provider_class: type[BaseLLMProvider],
    ) -> None:
        """Register a new provider class.

        Args:
            provider_type: The provider type
            provider_class: The provider class to register
        """
        cls._provider_classes[provider_type] = provider_class
        logger.info(f"Registered provider: {provider_type}")

    @classmethod
    def list_providers(cls) -> list[ProviderType]:
        """List all registered provider types.

        Returns:
            list[ProviderType]: List of provider types
        """
        return list(cls._provider_classes.keys())
