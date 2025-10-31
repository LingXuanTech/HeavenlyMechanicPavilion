"""Local data vendor plugin."""

from typing import List, Optional

from tradingagents.dataflows import local
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class LocalPlugin(DataVendorPlugin):
    """Plugin for local/cached data sources."""

    @property
    def name(self) -> str:
        return "local"

    @property
    def provider(self) -> str:
        return "local"

    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.STOCK_DATA,
            PluginCapability.INDICATORS,
            PluginCapability.BALANCE_SHEET,
            PluginCapability.CASHFLOW,
            PluginCapability.INCOME_STATEMENT,
            PluginCapability.NEWS,
            PluginCapability.GLOBAL_NEWS,
            PluginCapability.INSIDER_SENTIMENT,
            PluginCapability.INSIDER_TRANSACTIONS,
        ]

    @property
    def description(self) -> str:
        return "Local data provider using cached/offline data sources (Finnhub, SimFin, Reddit)"

    @property
    def priority(self) -> int:
        return 100

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        """Get stock price data from local sources."""
        return local.get_YFin_data(symbol, start_date, end_date)

    def get_indicators(
        self, symbol: str, start_date: str, end_date: str, indicators: Optional[List[str]] = None
    ) -> str:
        """Get technical indicators from local sources."""
        from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window

        return get_stock_stats_indicators_window(symbol, start_date, end_date)

    def get_balance_sheet(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get balance sheet data from local sources."""
        return local.get_simfin_balance_sheet(ticker, freq, curr_date)

    def get_cashflow(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get cash flow data from local sources."""
        return local.get_simfin_cashflow(ticker, freq, curr_date)

    def get_income_statement(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get income statement data from local sources."""
        return local.get_simfin_income_statements(ticker, freq, curr_date)

    def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> str:
        """Get news from local sources (Finnhub, Reddit, Google)."""
        results = []

        if symbol:
            try:
                finnhub_news = local.get_finnhub_news(symbol)
                if finnhub_news:
                    results.append(finnhub_news)
            except Exception:
                pass

            try:
                reddit_news = local.get_reddit_company_news(symbol)
                if reddit_news:
                    results.append(reddit_news)
            except Exception:
                pass

            try:
                from tradingagents.dataflows.google import get_google_news

                google_news = get_google_news(symbol)
                if google_news:
                    results.append(google_news)
            except Exception:
                pass

        return "\n\n".join(results) if results else "No news available"

    def get_global_news(self, limit: int = 10) -> str:
        """Get global news from local sources."""
        return local.get_reddit_global_news(limit)

    def get_insider_sentiment(self, symbol: str) -> str:
        """Get insider sentiment from local sources."""
        return local.get_finnhub_company_insider_sentiment(symbol)

    def get_insider_transactions(self, ticker: str) -> str:
        """Get insider transactions from local sources."""
        return local.get_finnhub_company_insider_transactions(ticker)
