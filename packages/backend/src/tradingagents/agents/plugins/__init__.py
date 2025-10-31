"""Built-in agent plugin implementations."""

from .bear_researcher_plugin import BearResearcherPlugin
from .bull_researcher_plugin import BullResearcherPlugin
from .fundamentals_analyst_plugin import FundamentalsAnalystPlugin
from .market_analyst_plugin import MarketAnalystPlugin
from .neutral_analyst_plugin import NeutralAnalystPlugin
from .news_analyst_plugin import NewsAnalystPlugin
from .research_manager_plugin import ResearchManagerPlugin
from .risk_manager_plugin import RiskManagerPlugin
from .risky_analyst_plugin import RiskyAnalystPlugin
from .safe_analyst_plugin import SafeAnalystPlugin
from .social_analyst_plugin import SocialAnalystPlugin
from .trader_plugin import TraderPlugin

__all__ = [
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
