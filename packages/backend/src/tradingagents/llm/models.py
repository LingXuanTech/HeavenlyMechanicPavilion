"""Data models for LLM runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AgentLLMRuntimeConfig:
    """Runtime configuration for an agent's LLM."""

    agent_id: Optional[int]
    agent_name: str
    llm_type: str
    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    api_key: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    cost_per_1k_tokens: Optional[float] = None
    enabled: bool = True

    def for_agent(
        self,
        agent_name: str,
        agent_id: Optional[int],
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> "AgentLLMRuntimeConfig":
        """Return a new config tailored for a specific agent identity."""
        return AgentLLMRuntimeConfig(
            agent_id=agent_id,
            agent_name=agent_name,
            llm_type=self.llm_type,
            provider=provider or self.provider,
            model=model or self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            api_key=api_key if api_key is not None else self.api_key,
            fallback_provider=self.fallback_provider,
            fallback_model=self.fallback_model,
            cost_per_1k_tokens=self.cost_per_1k_tokens,
            enabled=self.enabled,
        )


@dataclass
class LLMRuntimeBundle:
    """Bundle of default and per-agent runtime configs."""

    defaults: Dict[str, AgentLLMRuntimeConfig] = field(default_factory=dict)
    agent_overrides: Dict[str, AgentLLMRuntimeConfig] = field(default_factory=dict)

    def get_for_agent(self, agent_name: str, llm_type: str) -> AgentLLMRuntimeConfig:
        """Return the runtime configuration for an agent, falling back to type defaults."""
        config = self.agent_overrides.get(agent_name)
        if config and config.enabled:
            return config
        if llm_type in self.defaults:
            return self.defaults[llm_type]
        raise KeyError(f"No LLM configuration found for agent '{agent_name}' (type {llm_type})")
