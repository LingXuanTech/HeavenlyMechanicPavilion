# Legacy functions
from .analysts.fundamentals_analyst import create_fundamentals_analyst
from .analysts.market_analyst import create_market_analyst
from .analysts.news_analyst import create_news_analyst
from .analysts.social_media_analyst import create_social_media_analyst

# New plugin system
from .database_plugin import DatabaseAgentPlugin, create_plugin_from_db_config
from .managers.research_manager import create_research_manager
from .managers.risk_manager import create_risk_manager
from .plugin_base import AgentCapability, AgentPlugin, AgentRole
from .plugin_registry import (
    AgentPluginRegistry,
    get_agent_registry,
    initialize_agent_registry,
)
from .plugins import (
    BearResearcherPlugin,
    BullResearcherPlugin,
    FundamentalsAnalystPlugin,
    MarketAnalystPlugin,
    NeutralAnalystPlugin,
    NewsAnalystPlugin,
    ResearchManagerPlugin,
    RiskManagerPlugin,
    RiskyAnalystPlugin,
    SafeAnalystPlugin,
    SocialAnalystPlugin,
    TraderPlugin,
)
from .researchers.bear_researcher import create_bear_researcher
from .researchers.bull_researcher import create_bull_researcher
from .risk_mgmt.aggresive_debator import create_risky_debator
from .risk_mgmt.conservative_debator import create_safe_debator
from .risk_mgmt.neutral_debator import create_neutral_debator
from .trader.trader import create_trader
from .utils.agent_states import AgentState, InvestDebateState, RiskDebateState
from .utils.agent_utils import create_msg_delete
from .utils.memory import FinancialSituationMemory

__all__ = [
    "FinancialSituationMemory",
    "AgentState",
    "create_msg_delete",
    "InvestDebateState",
    "RiskDebateState",
    "create_bear_researcher",
    "create_bull_researcher",
    "create_research_manager",
    "create_fundamentals_analyst",
    "create_market_analyst",
    "create_neutral_debator",
    "create_news_analyst",
    "create_risky_debator",
    "create_risk_manager",
    "create_safe_debator",
    "create_social_media_analyst",
    "create_trader",
    # Plugin system
    "AgentPlugin",
    "AgentRole",
    "AgentCapability",
    "AgentPluginRegistry",
    "get_agent_registry",
    "initialize_agent_registry",
    "DatabaseAgentPlugin",
    "create_plugin_from_db_config",
    "MarketAnalystPlugin",
    "SocialAnalystPlugin",
    "NewsAnalystPlugin",
    "FundamentalsAnalystPlugin",
    "BullResearcherPlugin",
    "BearResearcherPlugin",
    "ResearchManagerPlugin",
    "TraderPlugin",
    "RiskyAnalystPlugin",
    "SafeAnalystPlugin",
    "NeutralAnalystPlugin",
    "RiskManagerPlugin",
]
