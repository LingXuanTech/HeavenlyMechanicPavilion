"""Factory for creating agent-specific LLM instances from database configuration."""

from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from sqlalchemy import select

from .factory import ProviderFactory

logger = logging.getLogger(__name__)

# Cache for LLM instances to avoid recreating them
_llm_cache: Dict[int, Any] = {}
_agent_name_to_id_cache: Dict[str, int] = {}


def _get_api_key_for_provider(provider: str) -> Optional[str]:
    """Get API key for a provider from environment variables.
    
    Args:
        provider: Provider name (openai, deepseek, grok, claude)
        
    Returns:
        API key or None if not found
    """
    provider_lower = provider.lower()
    
    # Map provider names to environment variable names
    env_key_map = {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "grok": "GROK_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }
    
    env_key = env_key_map.get(provider_lower, f"{provider.upper()}_API_KEY")
    return os.getenv(env_key)


async def _get_agent_llm_config_async(agent_id: int, session):
    """Get LLM config for an agent from database (async).
    
    Args:
        agent_id: The agent ID
        session: Database session
        
    Returns:
        AgentLLMConfig or None if not found
    """
    from app.db.models.agent_llm_config import AgentLLMConfig
    
    statement = (
        select(AgentLLMConfig)
        .where(AgentLLMConfig.agent_id == agent_id)
        .where(AgentLLMConfig.enabled == True)  # noqa: E712
        .limit(1)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _get_agent_by_name_async(agent_name: str, session):
    """Get agent config by name from database (async).
    
    Args:
        agent_name: The agent name
        session: Database session
        
    Returns:
        AgentConfig or None if not found
    """
    from app.db.models.agent_config import AgentConfig
    
    statement = select(AgentConfig).where(AgentConfig.name == agent_name)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


def get_llm_for_agent(agent_id: int, db_manager=None) -> Any:
    """Factory function to get LLM instance for an agent from database config.
    
    This function:
    1. Queries the agent_llm_configs table for the agent's configuration
    2. Creates a LangChain LLM instance with those settings
    3. Returns a default OpenAI gpt-4 instance if no config exists
    4. Caches instances to avoid recreating on every call
    
    Args:
        agent_id: The database ID of the agent
        db_manager: Optional database manager (will be imported if not provided)
        
    Returns:
        LangChain LLM instance (e.g., ChatOpenAI)
    """
    # Check cache first
    if agent_id in _llm_cache:
        return _llm_cache[agent_id]
    
    # Get database manager
    if db_manager is None:
        try:
            from app.db import get_db_manager
            db_manager = get_db_manager()
        except Exception as exc:
            logger.warning(f"Could not get database manager: {exc}. Using default LLM.")
            return _create_default_llm()
    
    # Query database for config
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a running loop, we can't use asyncio.run()
            # In this case, we'll use the synchronous fallback
            logger.warning(f"Already in event loop, using synchronous fallback for agent_id={agent_id}")
            return _create_default_llm()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            config = asyncio.run(_query_agent_llm_config(agent_id, db_manager))
        
        if config is None:
            logger.info(f"No LLM config found for agent_id={agent_id}, using default")
            llm = _create_default_llm()
        else:
            logger.info(f"Creating LLM for agent_id={agent_id}: {config.provider}/{config.model_name}")
            llm = _create_llm_from_config(config)
        
        # Cache the instance
        _llm_cache[agent_id] = llm
        return llm
        
    except Exception as exc:
        logger.error(f"Error getting LLM config for agent_id={agent_id}: {exc}")
        return _create_default_llm()


def get_llm_for_agent_by_name(agent_name: str, db_manager=None) -> Any:
    """Factory function to get LLM instance for an agent by name.
    
    This function looks up the agent by name, then gets its LLM configuration.
    
    Args:
        agent_name: The name of the agent (e.g., "market_analyst", "bull_researcher")
        db_manager: Optional database manager (will be imported if not provided)
        
    Returns:
        LangChain LLM instance (e.g., ChatOpenAI)
    """
    # Check name cache first
    if agent_name in _agent_name_to_id_cache:
        agent_id = _agent_name_to_id_cache[agent_name]
        return get_llm_for_agent(agent_id, db_manager)
    
    # Get database manager
    if db_manager is None:
        try:
            from app.db import get_db_manager
            db_manager = get_db_manager()
        except Exception as exc:
            logger.warning(f"Could not get database manager: {exc}. Using default LLM.")
            return _create_default_llm()
    
    # Query database for agent
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a running loop, use synchronous fallback
            logger.warning(f"Already in event loop, using synchronous fallback for agent_name={agent_name}")
            return _create_default_llm()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            agent = asyncio.run(_query_agent_by_name(agent_name, db_manager))
        
        if agent is None:
            logger.warning(f"Agent not found: {agent_name}, using default LLM")
            return _create_default_llm()
        
        # Cache the name-to-id mapping
        _agent_name_to_id_cache[agent_name] = agent.id
        
        # Get LLM config for this agent
        return get_llm_for_agent(agent.id, db_manager)
        
    except Exception as exc:
        logger.error(f"Error getting agent by name '{agent_name}': {exc}")
        return _create_default_llm()


async def _query_agent_llm_config(agent_id: int, db_manager):
    """Query database for agent LLM config (async helper)."""
    async for session in db_manager.get_session():
        return await _get_agent_llm_config_async(agent_id, session)
    return None


async def _query_agent_by_name(agent_name: str, db_manager):
    """Query database for agent by name (async helper)."""
    async for session in db_manager.get_session():
        return await _get_agent_by_name_async(agent_name, session)
    return None


def _create_llm_from_config(config) -> Any:
    """Create LangChain LLM instance from AgentLLMConfig.
    
    Args:
        config: AgentLLMConfig instance
        
    Returns:
        LangChain LLM instance
    """
    provider = config.provider.lower()
    api_key = _get_api_key_for_provider(provider)
    
    if not api_key:
        logger.warning(f"No API key found for provider '{provider}', using default")
        return _create_default_llm()
    
    try:
        # Use ProviderFactory to create provider instance
        provider_instance = ProviderFactory.create_provider(
            provider_type=provider,
            api_key=api_key,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
        )
        
        # Return the LangChain client instance
        return provider_instance.client
        
    except Exception as exc:
        logger.error(f"Failed to create LLM from config: {exc}")
        return _create_default_llm()


def _create_default_llm() -> Any:
    """Create default LLM instance (OpenAI gpt-4).
    
    Returns:
        ChatOpenAI instance with default settings
    """
    api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-testing")
    return ChatOpenAI(
        api_key=api_key,
        model="gpt-4",
        temperature=0.7,
    )


def clear_llm_cache():
    """Clear the LLM instance cache.
    
    This can be called after updating agent LLM configurations to force
    the factory to recreate instances with the new settings.
    """
    global _llm_cache, _agent_name_to_id_cache
    _llm_cache.clear()
    _agent_name_to_id_cache.clear()
    logger.info("LLM cache cleared")
