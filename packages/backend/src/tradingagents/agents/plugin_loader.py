"""Helper functions for loading and registering built-in agent plugins."""

import logging
from typing import Optional

from .plugin_registry import AgentPluginRegistry, get_agent_registry
from .plugins import (
    MarketAnalystPlugin,
    SocialAnalystPlugin,
    NewsAnalystPlugin,
    FundamentalsAnalystPlugin,
    BullResearcherPlugin,
    BearResearcherPlugin,
    ResearchManagerPlugin,
    TraderPlugin,
    RiskyAnalystPlugin,
    SafeAnalystPlugin,
    NeutralAnalystPlugin,
    RiskManagerPlugin,
)


logger = logging.getLogger(__name__)


def register_built_in_plugins(
    registry: Optional[AgentPluginRegistry] = None
) -> AgentPluginRegistry:
    """Register all built-in agent plugins with the registry.
    
    Args:
        registry: Optional registry instance. If None, uses global singleton.
        
    Returns:
        AgentPluginRegistry: The registry with all plugins registered
    """
    if registry is None:
        registry = get_agent_registry()
    
    # Register analyst plugins
    registry.register_plugin(MarketAnalystPlugin)
    registry.register_plugin(SocialAnalystPlugin)
    registry.register_plugin(NewsAnalystPlugin)
    registry.register_plugin(FundamentalsAnalystPlugin)
    
    # Register researcher plugins
    registry.register_plugin(BullResearcherPlugin)
    registry.register_plugin(BearResearcherPlugin)
    
    # Register manager plugins
    registry.register_plugin(ResearchManagerPlugin)
    registry.register_plugin(RiskManagerPlugin)
    
    # Register trader plugin
    registry.register_plugin(TraderPlugin)
    
    # Register risk analyst plugins
    registry.register_plugin(RiskyAnalystPlugin)
    registry.register_plugin(SafeAnalystPlugin)
    registry.register_plugin(NeutralAnalystPlugin)
    
    logger.info(f"Registered {len(registry.list_plugins())} built-in agent plugins")
    
    return registry


def get_default_analyst_slots() -> list[str]:
    """Get the default analyst slot names.
    
    Returns:
        List of default analyst slots
    """
    return ["market", "social", "news", "fundamentals"]


def get_required_agents() -> list[str]:
    """Get the list of required agent names for the core workflow.
    
    Returns:
        List of required agent names
    """
    return [
        "bull_researcher",
        "bear_researcher",
        "research_manager",
        "trader",
        "risky_analyst",
        "safe_analyst",
        "neutral_analyst",
        "risk_manager",
    ]
