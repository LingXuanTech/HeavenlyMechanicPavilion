"""Unit tests for agent LLM configuration factory."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_openai import ChatOpenAI

from tradingagents.llm_providers import (
    clear_llm_cache,
    get_llm_for_agent,
    get_llm_for_agent_by_name,
)


@pytest.fixture
def mock_agent_config():
    """Mock agent config."""
    config = MagicMock()
    config.id = 1
    config.name = "test_agent"
    return config


@pytest.fixture
def mock_llm_config():
    """Mock LLM config."""
    config = MagicMock()
    config.agent_id = 1
    config.provider = "openai"
    config.model_name = "gpt-4o"
    config.temperature = 0.8
    config.max_tokens = 1500
    config.top_p = 0.9
    config.enabled = True
    return config


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    manager = MagicMock()
    session_mock = MagicMock()
    
    async def mock_get_session():
        yield session_mock
    
    manager.get_session = mock_get_session
    return manager


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear LLM cache before each test."""
    clear_llm_cache()
    yield
    clear_llm_cache()


@pytest.fixture(autouse=True)
def mock_openai_api_key():
    """Mock OpenAI API key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
        yield


class TestAgentLLMFactory:
    """Test the agent LLM factory functions."""

    @pytest.mark.asyncio
    async def test_get_llm_for_agent_with_config(
        self, mock_db_manager, mock_llm_config
    ):
        """Test getting LLM for agent with config."""
        # Mock the async query function to return our mock config
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            return_value=mock_llm_config,
        ):
            llm = get_llm_for_agent(1, mock_db_manager)
            
            # Verify it's a ChatOpenAI instance
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4o"
            assert llm.temperature == 0.8

    @pytest.mark.asyncio
    async def test_get_llm_for_agent_without_config(self, mock_db_manager):
        """Test getting LLM for agent without config (uses default)."""
        # Mock the async query function to return None
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            return_value=None,
        ):
            llm = get_llm_for_agent(1, mock_db_manager)
            
            # Should return default LLM
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_llm_for_agent_by_name(
        self, mock_db_manager, mock_agent_config, mock_llm_config
    ):
        """Test getting LLM for agent by name."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_by_name",
            new_callable=AsyncMock,
            return_value=mock_agent_config,
        ), patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            return_value=mock_llm_config,
        ):
            llm = get_llm_for_agent_by_name("test_agent", mock_db_manager)
            
            # Verify correct LLM is returned
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4o"

    @pytest.mark.asyncio
    async def test_get_llm_for_nonexistent_agent_by_name(self, mock_db_manager):
        """Test getting LLM for nonexistent agent name."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_by_name",
            new_callable=AsyncMock,
            return_value=None,
        ):
            llm = get_llm_for_agent_by_name("nonexistent", mock_db_manager)
            
            # Should return default LLM
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_llm_caching(self, mock_db_manager, mock_llm_config):
        """Test that LLM instances are cached."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            return_value=mock_llm_config,
        ) as mock_query:
            # Get LLM twice with same agent_id
            llm1 = get_llm_for_agent(1, mock_db_manager)
            llm2 = get_llm_for_agent(1, mock_db_manager)
            
            # Should be same instance (cached)
            assert llm1 is llm2
            
            # Query should only be called once (on first call)
            assert mock_query.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_clearing(self, mock_db_manager, mock_llm_config):
        """Test clearing the cache."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            return_value=mock_llm_config,
        ) as mock_query:
            # Get LLM
            llm1 = get_llm_for_agent(1, mock_db_manager)
            
            # Clear cache
            clear_llm_cache()
            
            # Get LLM again
            llm2 = get_llm_for_agent(1, mock_db_manager)
            
            # Should be different instances
            assert llm1 is not llm2
            
            # Query should be called twice (once for each call)
            assert mock_query.call_count == 2

    @pytest.mark.asyncio
    async def test_get_llm_with_database_error(self, mock_db_manager):
        """Test handling database errors gracefully."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory._query_agent_llm_config",
            new_callable=AsyncMock,
            side_effect=Exception("Database error"),
        ):
            # Should return default LLM on error
            llm = get_llm_for_agent(1, mock_db_manager)
            
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_llm_without_db_manager(self):
        """Test getting LLM without providing db_manager."""
        with patch(
            "tradingagents.llm_providers.agent_llm_factory.get_db_manager",
            side_effect=Exception("DB not initialized"),
        ):
            # Should return default LLM when DB manager not available
            llm = get_llm_for_agent(1)
            
            assert isinstance(llm, ChatOpenAI)
            assert llm.model_name == "gpt-4"
