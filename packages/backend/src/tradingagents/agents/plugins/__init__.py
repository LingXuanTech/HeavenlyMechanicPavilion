"""Built-in agent plugin implementations."""

from .market_analyst_plugin import MarketAnalystPlugin
from .social_analyst_plugin import SocialAnalystPlugin
from .news_analyst_plugin import NewsAnalystPlugin
from .fundamentals_analyst_plugin import FundamentalsAnalystPlugin
from .bull_researcher_plugin import BullResearcherPlugin
from .bear_researcher_plugin import BearResearcherPlugin
from .research_manager_plugin import ResearchManagerPlugin
from .trader_plugin import TraderPlugin
from .risky_analyst_plugin import RiskyAnalystPlugin
from .safe_analyst_plugin import SafeAnalystPlugin
from .neutral_analyst_plugin import NeutralAnalystPlugin
from .risk_manager_plugin import RiskManagerPlugin


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
