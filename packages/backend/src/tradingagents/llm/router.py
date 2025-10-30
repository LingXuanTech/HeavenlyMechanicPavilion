"""Runtime orchestration utilities for agent-specific LLM selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel

from .models import AgentLLMRuntimeConfig, LLMRuntimeBundle
from .providers import LLMProviderFactory, ProviderConfigurationError
from .usage import LLMUsageTracker


@dataclass
class AgentLLMContext:
    """Holds instantiated chat models (primary + optional fallback) for an agent."""

    agent_name: str
    llm_type: str
    primary_config: AgentLLMRuntimeConfig
    primary_model: BaseChatModel
    fallback_config: Optional[AgentLLMRuntimeConfig] = None
    fallback_model: Optional[BaseChatModel] = None

    def iter_models(self) -> Iterable[Tuple[AgentLLMRuntimeConfig, BaseChatModel]]:
        yield self.primary_config, self.primary_model
        if self.fallback_model and self.fallback_config:
            yield self.fallback_config, self.fallback_model


class AgentLLMOrchestrator:
    """Builds and caches LLM contexts for agents using runtime configuration."""

    def __init__(
        self,
        runtime_bundle: LLMRuntimeBundle,
        *,
        provider_factory: Optional[LLMProviderFactory] = None,
        tracker: Optional[LLMUsageTracker] = None,
    ) -> None:
        self._bundle = runtime_bundle
        self._factory = provider_factory or LLMProviderFactory()
        self._tracker = tracker or LLMUsageTracker()
        self._cache: Dict[Tuple[str, str], AgentLLMContext] = {}

    @property
    def tracker(self) -> LLMUsageTracker:
        return self._tracker

    def reset_cache(self) -> None:
        self._cache.clear()

    def get_context(
        self,
        agent_name: str,
        llm_type: str,
        *,
        agent_id: Optional[int] = None,
        streaming: bool = False,
    ) -> AgentLLMContext:
        """Return an instantiated LLM context for an agent."""
        cache_key = (agent_name, llm_type)
        if cache_key in self._cache:
            return self._cache[cache_key]

        raw_config = self._resolve_config(agent_name, llm_type)
        runtime_config = raw_config.for_agent(agent_name, agent_id)
        primary_model = self._factory.create_chat_model(runtime_config, self._tracker, streaming=streaming)

        fallback_config: Optional[AgentLLMRuntimeConfig] = None
        fallback_model: Optional[BaseChatModel] = None
        if raw_config.fallback_provider and raw_config.fallback_model:
            fallback_api_key = runtime_config.api_key if raw_config.fallback_provider == runtime_config.provider else None
            fallback_config = runtime_config.for_agent(
                agent_name,
                agent_id,
                provider=raw_config.fallback_provider,
                model=raw_config.fallback_model,
                api_key=fallback_api_key,
            )
            fallback_config.fallback_provider = None
            fallback_config.fallback_model = None
            try:
                fallback_model = self._factory.create_chat_model(
                    fallback_config,
                    self._tracker,
                    streaming=streaming,
                )
            except ProviderConfigurationError:
                fallback_config = None
                fallback_model = None

        context = AgentLLMContext(
            agent_name=agent_name,
            llm_type=llm_type,
            primary_config=runtime_config,
            primary_model=primary_model,
            fallback_config=fallback_config,
            fallback_model=fallback_model,
        )
        self._cache[cache_key] = context
        return context

    def _resolve_config(self, agent_name: str, llm_type: str) -> AgentLLMRuntimeConfig:
        config = self._bundle.agent_overrides.get(agent_name)
        if config and config.enabled:
            return config
        if llm_type in self._bundle.defaults:
            return self._bundle.defaults[llm_type]
        raise ProviderConfigurationError(
            f"No LLM configuration found for agent '{agent_name}' with type '{llm_type}'"
        )
