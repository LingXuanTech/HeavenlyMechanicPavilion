"""Tests for TradingAgentsGraph LLM configuration integration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from tradingagents.graph.llm_integration import (
    create_agent_llm_runtime,
    create_trading_graph_with_llm_runtime,
)


@pytest.fixture(autouse=True)
def mock_openai_api_key():
    """Mock OpenAI API key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
        yield


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    manager = MagicMock()
    
    async def mock_get_session():
        session = MagicMock()
        # Mock execute to return empty results
        result = MagicMock()
        result.scalars().all.return_value = []
        result.one.return_value = (None, 0, None, 0)
        session.execute.return_value = result
        yield session
    
    manager.get_session = mock_get_session
    return manager


@pytest.fixture
def base_config():
    """Base trading configuration."""
    return {
        "project_dir": "/tmp/test",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-4o-mini",
        "deep_think_llm": "gpt-4o",
        "temperature": 0.7,
    }


class TestLLMIntegration:
    """Test LLM configuration integration with TradingAgentsGraph."""

    def test_create_agent_llm_runtime_success(self, base_config, mock_db_manager):
        """Test creating AgentLLMRuntime successfully."""
        runtime = create_agent_llm_runtime(base_config, mock_db_manager)
        
        assert runtime is not None
        # Runtime should have the expected attributes
        assert hasattr(runtime, 'get_llm')
        assert hasattr(runtime, 'refresh_if_needed')

    def test_create_agent_llm_runtime_no_db_manager(self, base_config):
        """Test creating runtime without db_manager (should try to get global)."""
        with patch("tradingagents.graph.llm_integration.get_db_manager", side_effect=Exception("No DB")):
            runtime = create_agent_llm_runtime(base_config, None)
            
            # Should return None when DB not available
            assert runtime is None

    def test_create_trading_graph_with_runtime(self, base_config, mock_db_manager):
        """Test creating TradingAgentsGraph with LLM runtime."""
        with patch("tradingagents.graph.llm_integration.TradingAgentsGraph") as MockGraph:
            graph = create_trading_graph_with_llm_runtime(
                base_config,
                selected_analysts=["market"],
                debug=False,
                db_manager=mock_db_manager,
            )
            
            # Verify TradingAgentsGraph was created with correct parameters
            MockGraph.assert_called_once()
            call_kwargs = MockGraph.call_args.kwargs
            
            assert call_kwargs["selected_analysts"] == ["market"]
            assert call_kwargs["debug"] is False
            assert call_kwargs["config"] == base_config
            assert call_kwargs["llm_runtime"] is not None

    def test_create_trading_graph_without_db(self, base_config):
        """Test creating TradingAgentsGraph without database."""
        with patch("tradingagents.graph.llm_integration.get_db_manager", side_effect=Exception("No DB")):
            with patch("tradingagents.graph.llm_integration.TradingAgentsGraph") as MockGraph:
                graph = create_trading_graph_with_llm_runtime(
                    base_config,
                    db_manager=None,
                )
                
                # Should still create graph, but with llm_runtime=None
                MockGraph.assert_called_once()
                call_kwargs = MockGraph.call_args.kwargs
                assert call_kwargs["llm_runtime"] is None

    def test_runtime_get_llm_method(self, base_config, mock_db_manager):
        """Test that runtime can get LLM for agents."""
        runtime = create_agent_llm_runtime(base_config, mock_db_manager)
        
        if runtime is not None:
            # Try to get LLM for an agent
            llm = runtime.get_llm("market_analyst", "quick")
            
            # Should return None for non-existent agent, not crash
            # (since our mock DB returns empty results)
            assert llm is None


class TestTradingGraphLLMResolution:
    """Test that TradingAgentsGraph properly resolves LLMs."""

    def test_graph_resolves_llm_with_runtime(self, base_config):
        """Test that graph uses llm_runtime when available."""
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        # Create a mock runtime
        mock_runtime = MagicMock()
        mock_llm = MagicMock()
        mock_runtime.get_llm.return_value = mock_llm
        
        # Create graph with runtime
        with patch("tradingagents.graph.trading_graph.FinancialSituationMemory"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"],
                config=base_config,
                llm_runtime=mock_runtime,
            )
            
            # Resolve an LLM
            llm = graph._resolve_llm("market_analyst", "quick")
            
            # Should have called runtime.get_llm
            mock_runtime.get_llm.assert_called_with("market_analyst", "quick")
            assert llm == mock_llm

    def test_graph_falls_back_without_runtime(self, base_config):
        """Test that graph falls back to default LLMs when runtime not available."""
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        
        # Create graph without runtime
        with patch("tradingagents.graph.trading_graph.FinancialSituationMemory"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"],
                config=base_config,
                llm_runtime=None,
            )
            
            # Resolve an LLM
            llm = graph._resolve_llm("market_analyst", "quick")
            
            # Should return a fallback LLM
            assert llm is not None
