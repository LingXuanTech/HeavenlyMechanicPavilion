"""OpenAI vendor plugin."""

from typing import Any, Dict, List, Optional

from tradingagents.dataflows import openai
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class OpenAIPlugin(DataVendorPlugin):
    """Plugin for OpenAI-based data vendor."""
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def provider(self) -> str:
        return "openai"
    
    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.FUNDAMENTALS,
            PluginCapability.NEWS,
            PluginCapability.GLOBAL_NEWS,
        ]
    
    @property
    def description(self) -> str:
        return "OpenAI-powered data provider for news and fundamental analysis"
    
    @property
    def priority(self) -> int:
        return 70
    
    def get_fundamentals(self, ticker: str, curr_date: str) -> str:
        """Get fundamental data using OpenAI."""
        return openai.get_fundamentals_openai(ticker, curr_date)
    
    def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> str:
        """Get news using OpenAI."""
        if symbol:
            return openai.get_stock_news_openai(symbol, limit)
        return self.get_global_news(limit)
    
    def get_global_news(self, limit: int = 10) -> str:
        """Get global news using OpenAI."""
        return openai.get_global_news_openai(limit)
