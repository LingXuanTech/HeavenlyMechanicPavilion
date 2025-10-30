"""Integration tests for agent LLM configuration factory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from langchain_openai import ChatOpenAI

from app.db import AgentConfig, AgentLLMConfig
from tradingagents.llm_providers import (
    clear_llm_cache,
    get_llm_for_agent,
    get_llm_for_agent_by_name,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import DatabaseManager


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def async_session(test_db):
    """Provide async session for tests."""
    async for session in test_db.get_session():
        yield session


@pytest.fixture
def db_manager(test_db):
    """Provide database manager for tests."""
    return test_db


class TestLLMConfigFactory:
    """Test the LLM configuration factory functions."""

    async def test_get_llm_for_agent_with_config(
        self, async_session: AsyncSession, db_manager
    ):
        """Test getting LLM for agent with database config."""
        # Create an agent
        agent = AgentConfig(
            name="test_market_analyst",
            agent_type="analyst",
            role="market",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            is_active=True,
        )
        async_session.add(agent)
        await async_session.flush()

        # Create LLM config for the agent
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4o",
            temperature=0.8,
            max_tokens=1500,
            enabled=True,
        )
        async_session.add(llm_config)
        await async_session.commit()

        # Clear cache to ensure fresh query
        clear_llm_cache()

        # Get LLM for agent
        llm = get_llm_for_agent(agent.id, db_manager)

        # Verify it's a ChatOpenAI instance
        assert isinstance(llm, ChatOpenAI)
        # Verify it has the configured model
        assert llm.model_name == "gpt-4o"
        # Verify temperature setting
        assert llm.temperature == 0.8

    async def test_get_llm_for_agent_without_config(
        self, async_session: AsyncSession, db_manager
    ):
        """Test getting LLM for agent without database config (should use default)."""
        # Create an agent without LLM config
        agent = AgentConfig(
            name="test_bull_researcher",
            agent_type="researcher",
            role="bull",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            is_active=True,
        )
        async_session.add(agent)
        await async_session.commit()

        # Clear cache
        clear_llm_cache()

        # Get LLM for agent (should return default)
        llm = get_llm_for_agent(agent.id, db_manager)

        # Verify it's a ChatOpenAI instance
        assert isinstance(llm, ChatOpenAI)
        # Default should be gpt-4
        assert llm.model_name == "gpt-4"

    async def test_get_llm_for_agent_by_name(
        self, async_session: AsyncSession, db_manager
    ):
        """Test getting LLM for agent by name."""
        # Create an agent
        agent = AgentConfig(
            name="test_trader",
            agent_type="trader",
            role="trader",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            is_active=True,
        )
        async_session.add(agent)
        await async_session.flush()

        # Create LLM config
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4-turbo",
            temperature=0.5,
            enabled=True,
        )
        async_session.add(llm_config)
        await async_session.commit()

        # Clear cache
        clear_llm_cache()

        # Get LLM by agent name
        llm = get_llm_for_agent_by_name("test_trader", db_manager)

        # Verify it's configured correctly
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-4-turbo"
        assert llm.temperature == 0.5

    async def test_get_llm_for_nonexistent_agent(self, db_manager):
        """Test getting LLM for non-existent agent (should return default)."""
        # Clear cache
        clear_llm_cache()

        # Try to get LLM for non-existent agent name
        llm = get_llm_for_agent_by_name("nonexistent_agent", db_manager)

        # Should return default
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-4"

    async def test_llm_caching(self, async_session: AsyncSession, db_manager):
        """Test that LLM instances are cached."""
        # Create an agent with config
        agent = AgentConfig(
            name="test_caching_agent",
            agent_type="analyst",
            role="market",
            is_active=True,
        )
        async_session.add(agent)
        await async_session.flush()

        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.7,
            enabled=True,
        )
        async_session.add(llm_config)
        await async_session.commit()

        # Clear cache
        clear_llm_cache()

        # Get LLM twice
        llm1 = get_llm_for_agent(agent.id, db_manager)
        llm2 = get_llm_for_agent(agent.id, db_manager)

        # Should be the same instance (cached)
        assert llm1 is llm2

    async def test_disabled_config_uses_default(
        self, async_session: AsyncSession, db_manager
    ):
        """Test that disabled LLM config falls back to default."""
        # Create an agent
        agent = AgentConfig(
            name="test_disabled_config",
            agent_type="analyst",
            role="news",
            is_active=True,
        )
        async_session.add(agent)
        await async_session.flush()

        # Create disabled LLM config
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4o",
            temperature=0.9,
            enabled=False,  # Disabled
        )
        async_session.add(llm_config)
        await async_session.commit()

        # Clear cache
        clear_llm_cache()

        # Get LLM for agent
        llm = get_llm_for_agent(agent.id, db_manager)

        # Should use default since config is disabled
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-4"

    async def test_multiple_agents_different_configs(
        self, async_session: AsyncSession, db_manager
    ):
        """Test multiple agents with different configurations."""
        # Create two agents with different configs
        agent1 = AgentConfig(
            name="fast_agent",
            agent_type="analyst",
            role="market",
            is_active=True,
        )
        agent2 = AgentConfig(
            name="slow_agent",
            agent_type="analyst",
            role="fundamentals",
            is_active=True,
        )
        async_session.add_all([agent1, agent2])
        await async_session.flush()

        config1 = AgentLLMConfig(
            agent_id=agent1.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.3,
            enabled=True,
        )
        config2 = AgentLLMConfig(
            agent_id=agent2.id,
            provider="openai",
            model_name="gpt-4o",
            temperature=0.9,
            max_tokens=2000,
            enabled=True,
        )
        async_session.add_all([config1, config2])
        await async_session.commit()

        # Clear cache
        clear_llm_cache()

        # Get LLMs for both agents
        llm1 = get_llm_for_agent(agent1.id, db_manager)
        llm2 = get_llm_for_agent(agent2.id, db_manager)

        # Verify each has its own config
        assert llm1.model_name == "gpt-4o-mini"
        assert llm1.temperature == 0.3

        assert llm2.model_name == "gpt-4o"
        assert llm2.temperature == 0.9
