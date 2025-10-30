"""LLM provider abstractions and factory for TradingAgents."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Type

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from openai import OpenAI

try:  # pragma: no cover - optional dependency for type checking
    import anthropic
except Exception:  # pragma: no cover - graceful fallback if absent
    anthropic = None  # type: ignore

from .models import AgentLLMRuntimeConfig
from .usage import LLMUsageCallbackHandler, LLMUsageTracker


class ProviderConfigurationError(RuntimeError):
    """Raised when provider configuration, such as missing API key, is invalid."""


@dataclass
class ProviderMetadata:
    """Metadata exposed for UI consumption."""

    id: str
    name: str
    models: List[str]
    supports_streaming: bool
    default_base_url: Optional[str]


class BaseLLMProvider:
    """Base class for provider-specific adapters."""

    name: str = "base"
    display_name: str = "Base Provider"
    env_key: Optional[str] = None
    base_url_env_key: Optional[str] = None
    default_base_url: Optional[str] = None
    models: List[str] = []
    supports_streaming: bool = False

    def __init__(self, *, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.base_url = base_url or self._load_base_url()

    def _load_api_key(self) -> Optional[str]:
        if self.env_key:
            return os.getenv(self.env_key)
        return None

    def _load_base_url(self) -> Optional[str]:
        if self.base_url_env_key:
            return os.getenv(self.base_url_env_key) or self.default_base_url
        return self.default_base_url

    def ensure_api_key(self) -> None:
        if not self.api_key:
            raise ProviderConfigurationError(
                f"API key not configured for provider '{self.name}'. "
                f"Set environment variable {self.env_key} or provide an override."
            )

    def create_chat_model(
        self,
        *,
        config: AgentLLMRuntimeConfig,
        tracker: LLMUsageTracker,
        streaming: bool = False,
    ) -> BaseChatModel:
        """Create a langchain ChatModel for the provider."""
        raise NotImplementedError

    def list_models(self) -> List[str]:
        return self.models

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            id=self.name,
            name=self.display_name,
            models=self.list_models(),
            supports_streaming=self.supports_streaming,
            default_base_url=self.default_base_url,
        )

    def validate_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate that an API key is accepted by the upstream provider."""
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    display_name = "OpenAI"
    env_key = "OPENAI_API_KEY"
    base_url_env_key = "OPENAI_BASE_URL"
    default_base_url = "https://api.openai.com/v1"
    models = ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"]
    supports_streaming = True

    def create_chat_model(
        self,
        *,
        config: AgentLLMRuntimeConfig,
        tracker: LLMUsageTracker,
        streaming: bool = False,
    ) -> BaseChatModel:
        self.ensure_api_key()
        params = {
            "api_key": self.api_key,
            "model": config.model,
            "temperature": config.temperature,
            "streaming": streaming,
            "callbacks": [
                LLMUsageCallbackHandler(
                    tracker=tracker,
                    agent_id=config.agent_id,
                    agent_name=config.agent_name,
                    provider=self.name,
                    model=config.model,
                    cost_per_1k_tokens=config.cost_per_1k_tokens,
                )
            ],
        }
        if self.base_url:
            params["base_url"] = self.base_url
        if config.max_tokens is not None:
            params["max_tokens"] = config.max_tokens
        if config.top_p is not None:
            params["top_p"] = config.top_p
        return ChatOpenAI(**params)

    def validate_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        base_url = self.base_url or self.default_base_url
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            client.models.list()
            return True, None
        except Exception as exc:  # pragma: no cover - network/HTTP errors
            return False, str(exc)


class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"
    display_name = "DeepSeek"
    env_key = "DEEPSEEK_API_KEY"
    base_url_env_key = "DEEPSEEK_BASE_URL"
    default_base_url = "https://api.deepseek.com/v1"
    models = ["deepseek-chat", "deepseek-coder"]


class GrokProvider(OpenAIProvider):
    name = "grok"
    display_name = "Grok (xAI)"
    env_key = "GROK_API_KEY"
    base_url_env_key = "GROK_BASE_URL"
    default_base_url = "https://api.x.ai/v1"
    models = ["grok-beta", "grok-2"]

    def create_chat_model(
        self,
        *,
        config: AgentLLMRuntimeConfig,
        tracker: LLMUsageTracker,
        streaming: bool = False,
    ) -> BaseChatModel:
        # xAI currently expects HTTP Bearer auth; ChatOpenAI supports this via api_key
        return super().create_chat_model(config=config, tracker=tracker, streaming=streaming)


class ClaudeProvider(BaseLLMProvider):
    name = "claude"
    display_name = "Claude (Anthropic)"
    env_key = "ANTHROPIC_API_KEY"
    base_url_env_key = "ANTHROPIC_BASE_URL"
    default_base_url = None
    models = [
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-3.5-sonnet",
    ]
    supports_streaming = True

    def create_chat_model(
        self,
        *,
        config: AgentLLMRuntimeConfig,
        tracker: LLMUsageTracker,
        streaming: bool = False,
    ) -> BaseChatModel:
        self.ensure_api_key()
        params = {
            "api_key": self.api_key,
            "model": config.model,
            "temperature": config.temperature,
            "streaming": streaming,
            "callbacks": [
                LLMUsageCallbackHandler(
                    tracker=tracker,
                    agent_id=config.agent_id,
                    agent_name=config.agent_name,
                    provider=self.name,
                    model=config.model,
                    cost_per_1k_tokens=config.cost_per_1k_tokens,
                )
            ],
        }
        if self.base_url:
            params["base_url"] = self.base_url
        if config.max_tokens is not None:
            # LangChain Anthropic uses max_tokens_to_sample for completion cap
            params["max_tokens_to_sample"] = config.max_tokens
        if config.top_p is not None:
            params["top_p"] = config.top_p
        return ChatAnthropic(**params)

    def validate_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        if anthropic is None:  # pragma: no cover - dependency missing
            return False, "anthropic package is not installed"
        try:
            client = anthropic.Anthropic(api_key=api_key)
            client.models.list()
            return True, None
        except Exception as exc:  # pragma: no cover - network/HTTP errors
            return False, str(exc)


PROVIDER_CLASSES: Dict[str, Type[BaseLLMProvider]] = {
    OpenAIProvider.name: OpenAIProvider,
    DeepSeekProvider.name: DeepSeekProvider,
    GrokProvider.name: GrokProvider,
    ClaudeProvider.name: ClaudeProvider,
}


class LLMProviderFactory:
    """Factory to manage provider instances and metadata."""

    def __init__(self):
        self._providers: Dict[str, Type[BaseLLMProvider]] = PROVIDER_CLASSES

    def list_providers(self) -> List[ProviderMetadata]:
        return [cls().metadata() for cls in self._providers.values()]

    def list_models(self, provider: str) -> List[str]:
        cls = self._providers.get(provider)
        if not cls:
            raise ProviderConfigurationError(f"Unknown provider '{provider}'")
        return cls().list_models()

    def validate_key(self, provider: str, api_key: str) -> Tuple[bool, Optional[str]]:
        cls = self._providers.get(provider)
        if not cls:
            raise ProviderConfigurationError(f"Unknown provider '{provider}'")
        return cls(base_url=None).validate_key(api_key)

    def create_chat_model(
        self,
        config: AgentLLMRuntimeConfig,
        tracker: LLMUsageTracker,
        *,
        streaming: bool = False,
    ) -> BaseChatModel:
        cls = self._providers.get(config.provider)
        if not cls:
            raise ProviderConfigurationError(f"Unknown provider '{config.provider}'")
        provider = cls(api_key=config.api_key)
        return provider.create_chat_model(config=config, tracker=tracker, streaming=streaming)

    def ensure_reachable(self, provider: str) -> bool:
        """Best-effort reachability check for provider base URL."""
        cls = self._providers.get(provider)
        if not cls:
            raise ProviderConfigurationError(f"Unknown provider '{provider}'")
        base_url = cls().default_base_url
        if not base_url:
            return True
        try:  # pragma: no cover - simple network health check
            response = httpx.head(base_url, timeout=3.0)
            return response.status_code < 500
        except Exception:
            return False
