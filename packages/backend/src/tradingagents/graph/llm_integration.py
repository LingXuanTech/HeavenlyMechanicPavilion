"""Integration helpers for agent LLM configuration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_agent_llm_runtime(
    base_config: Dict[str, Any],
    db_manager: Optional[Any] = None,
) -> Optional[Any]:
    """Create an AgentLLMRuntime instance for use with TradingAgentsGraph.

    This function creates the runtime manager that reads agent LLM configurations
    from the database and provides configured LLM instances to agents.

    Args:
        base_config: Base configuration dict (e.g., DEFAULT_CONFIG)
        db_manager: Optional database manager. If None, will try to get global instance.

    Returns:
        AgentLLMRuntime instance or None if creation fails
    """
    try:
        # Import here to avoid circular dependencies
        from app.services.llm_runtime import AgentLLMRuntime

        if db_manager is None:
            try:
                from app.db import get_db_manager

                db_manager = get_db_manager()
            except Exception as exc:
                logger.warning(f"Could not get database manager: {exc}")
                return None

        # Create the runtime
        runtime = AgentLLMRuntime(base_config)

        # Do an initial load
        runtime.refresh_if_needed(force=True)

        logger.info("AgentLLMRuntime created and initialized")
        return runtime

    except Exception as exc:
        logger.error(f"Failed to create AgentLLMRuntime: {exc}")
        return None


def create_trading_graph_with_llm_runtime(
    base_config: Dict[str, Any],
    selected_analysts=None,
    debug: bool = False,
    use_plugin_system: bool = False,
    db_manager: Optional[Any] = None,
) -> Any:
    """Create a TradingAgentsGraph with AgentLLMRuntime integration.

    This is a convenience function that:
    1. Creates an AgentLLMRuntime from database config
    2. Initializes TradingAgentsGraph with that runtime
    3. Agents will use their configured LLMs from the database

    Args:
        base_config: Base configuration dict
        selected_analysts: List of analyst types to include
        debug: Whether to run in debug mode
        use_plugin_system: Whether to use the plugin system
        db_manager: Optional database manager

    Returns:
        TradingAgentsGraph instance
    """
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    if selected_analysts is None:
        selected_analysts = ["market", "social", "news", "fundamentals"]

    # Try to create runtime
    llm_runtime = create_agent_llm_runtime(base_config, db_manager)

    if llm_runtime is None:
        logger.warning("AgentLLMRuntime not available, agents will use default LLMs")
    else:
        logger.info("TradingAgentsGraph will use database-configured LLMs")

    # Create and return graph with runtime
    return TradingAgentsGraph(
        selected_analysts=selected_analysts,
        debug=debug,
        config=base_config,
        use_plugin_system=use_plugin_system,
        llm_runtime=llm_runtime,
    )
