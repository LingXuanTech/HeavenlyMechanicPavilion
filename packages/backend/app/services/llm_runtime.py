"""Agent LLM Runtime Manager for dynamic LLM resolution and caching."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class AgentLLMRuntime:
    """Manages LLM instances with database-backed configuration and caching.
    
    This class provides dynamic LLM resolution for agents, loading their
    configurations from the database and caching instances for performance.
    """
    
    def __init__(self, base_config: Dict[str, Any]):
        """Initialize the Agent LLM Runtime.
        
        Args:
            base_config: Base configuration dict containing default LLM settings
        """
        self.base_config = base_config
        self._cache: Dict[str, Any] = {}  # Cache format: "agent_name:config_hash" -> LLM instance
        self._config_cache: Dict[str, Dict[str, Any]] = {}  # agent_name -> config dict
        self._last_refresh: Optional[datetime] = None
        self._refresh_interval = timedelta(minutes=5)  # Refresh config every 5 minutes
        self._repository = None  # Lazy-initialized
        
    @property
    def repository(self):
        """Lazy-load the agent config repository."""
        if self._repository is None:
            try:
                from ..db import get_session
                from ..repositories.agent_config import AgentConfigRepository
                
                session = next(get_session())
                self._repository = AgentConfigRepository(session)
            except Exception as e:
                logger.warning(f"Could not initialize repository: {e}")
        return self._repository
    
    def refresh_if_needed(self, force: bool = False) -> None:
        """Refresh agent configurations from database if needed.
        
        Args:
            force: If True, force refresh regardless of interval
        """
        now = datetime.now()
        should_refresh = (
            force or
            self._last_refresh is None or
            (now - self._last_refresh) > self._refresh_interval
        )
        
        if not should_refresh:
            return
        
        logger.info("Refreshing agent LLM configurations from database")
        
        try:
            if self.repository:
                # Load all agent configs
                configs = self.repository.get_all()
                for config in configs:
                    if config.llm_config_json:
                        try:
                            llm_config = json.loads(config.llm_config_json)
                            self._config_cache[config.name] = llm_config
                            logger.debug(f"Loaded config for agent: {config.name}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in config for {config.name}: {e}")
                
                self._last_refresh = now
                logger.info(f"Refreshed {len(self._config_cache)} agent configurations")
            else:
                logger.warning("Repository not available, using base config only")
        except Exception as e:
            logger.error(f"Error refreshing configurations: {e}")
    
    def provider_status(self) -> Dict[str, Any]:
        """Get status of configured providers.
        
        Returns:
            Dict with provider status information
        """
        status = {
            "cached_instances": len(self._cache),
            "cached_configs": len(self._config_cache),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "base_provider": self.base_config.get("llm_provider", "openai"),
        }
        
        # Count providers in use
        providers = {}
        for config in self._config_cache.values():
            provider = config.get("provider", "unknown")
            providers[provider] = providers.get(provider, 0) + 1
        status["providers_in_use"] = providers
        
        return status
    
    def get_llm(self, agent_name: str, llm_type: str = "quick") -> Any:
        """Get an LLM instance for a specific agent.
        
        This method first tries to load agent-specific configuration from the database.
        If not found, it falls back to environment-based default configuration.
        
        Args:
            agent_name: The name of the agent requesting the LLM
            llm_type: The type of LLM needed ("quick" or "deep") - used only for fallback
            
        Returns:
            A LangChain ChatModel instance configured for the agent
            
        Raises:
            ValueError: If no valid configuration can be found
        """
        # Try to use cached config first
        if agent_name in self._config_cache:
            llm_config = self._config_cache[agent_name]
            return self._create_llm_from_config(llm_config, agent_name)
        
        # Fallback to environment-based configuration
        return self._create_default_llm(llm_type)
    
    def _create_llm_from_config(self, config: Dict[str, Any], agent_name: str) -> Any:
        """Create an LLM instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with provider, model, etc.
            agent_name: Agent name for cache key generation
            
        Returns:
            A LangChain ChatModel instance
        """
        # Generate cache key
        config_str = json.dumps(config, sort_keys=True)
        cache_key = f"{agent_name}:{hash(config_str)}"
        
        # Return cached instance if available
        if cache_key in self._cache:
            logger.debug(f"Using cached LLM for {agent_name}")
            return self._cache[cache_key]
        
        # Extract configuration
        provider = config.get("provider", "openai").lower()
        model = config.get("model", "gpt-4o-mini")
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens")
        base_url = config.get("base_url")
        
        # Get API key from environment variable
        api_key_env = config.get("api_key_env")
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                logger.warning(f"API key environment variable {api_key_env} not found")
                api_key = None
        else:
            api_key = self._get_default_api_key(provider)
        
        # Create LLM instance based on provider
        llm = self._instantiate_llm(
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url,
        )
        
        # Cache the instance
        self._cache[cache_key] = llm
        logger.info(f"Created and cached {provider} LLM ({model}) for {agent_name}")
        
        return llm
    
    def _create_default_llm(self, llm_type: str) -> Any:
        """Create a default LLM based on environment variables.
        
        Args:
            llm_type: "quick" or "deep"
            
        Returns:
            A LangChain ChatModel instance
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        
        if llm_type == "deep":
            model = os.getenv("DEEP_THINK_LLM", "gpt-4-turbo")
        else:
            model = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")
        
        api_key = self._get_default_api_key(provider)
        base_url = os.getenv("BACKEND_URL")
        
        cache_key = f"default:{provider}:{model}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        llm = self._instantiate_llm(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        
        self._cache[cache_key] = llm
        logger.info(f"Created default {provider} LLM ({model}) for {llm_type}")
        
        return llm
    
    def _instantiate_llm(
        self,
        provider: str,
        model: str,
        api_key: Optional[str],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> Any:
        """Instantiate a LangChain ChatModel based on provider.
        
        Args:
            provider: Provider name (openai, anthropic, google, deepseek)
            model: Model name
            api_key: API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            base_url: Optional custom base URL
            
        Returns:
            A LangChain ChatModel instance
            
        Raises:
            ValueError: If provider is not supported
        """
        kwargs: Dict[str, Any] = {
            "model": model,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if api_key:
            kwargs["api_key"] = api_key
        
        if provider in {"openai", "deepseek"}:
            if base_url:
                kwargs["base_url"] = base_url
            return ChatOpenAI(**kwargs)
        
        elif provider == "anthropic":
            if base_url:
                kwargs["base_url"] = base_url
            return ChatAnthropic(**kwargs)
        
        elif provider == "google":
            return ChatGoogleGenerativeAI(**kwargs)
        
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: openai, anthropic, google, deepseek"
            )
    
    def _get_default_api_key(self, provider: str) -> Optional[str]:
        """Get default API key for a provider from environment.
        
        Args:
            provider: Provider name
            
        Returns:
            API key from environment or None
        """
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        
        env_var = env_var_map.get(provider)
        if env_var:
            return os.getenv(env_var)
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the LLM instance cache."""
        self._cache.clear()
        logger.info("Cleared LLM cache")
    
    def get_cache_size(self) -> int:
        """Get the number of cached LLM instances.
        
        Returns:
            Number of cached instances
        """
        return len(self._cache)
