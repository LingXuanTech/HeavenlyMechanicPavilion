"""Google vendor plugin."""

from typing import List, Optional

from tradingagents.dataflows import google
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class GooglePlugin(DataVendorPlugin):
    """Plugin for Google News data vendor."""

    @property
    def name(self) -> str:
        return "google"

    @property
    def provider(self) -> str:
        return "google"

    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.NEWS,
        ]

    @property
    def description(self) -> str:
        return "Google News data provider for company news"

    @property
    def priority(self) -> int:
        return 80

    def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> str:
        """Get news from Google News."""
        if not symbol:
            raise ValueError("Google News plugin requires a symbol")
        return google.get_google_news(symbol)
