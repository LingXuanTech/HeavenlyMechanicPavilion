"""Alpha Vantage vendor plugin."""

from typing import Dict, List, Optional

from tradingagents.dataflows import alpha_vantage
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class AlphaVantagePlugin(DataVendorPlugin):
    """Plugin for Alpha Vantage data vendor."""

    @property
    def name(self) -> str:
        return "alpha_vantage"

    @property
    def provider(self) -> str:
        return "alpha_vantage"

    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.STOCK_DATA,
            PluginCapability.INDICATORS,
            PluginCapability.FUNDAMENTALS,
            PluginCapability.BALANCE_SHEET,
            PluginCapability.CASHFLOW,
            PluginCapability.INCOME_STATEMENT,
            PluginCapability.INSIDER_TRANSACTIONS,
            PluginCapability.NEWS,
        ]

    @property
    def description(self) -> str:
        return (
            "Alpha Vantage data provider for stocks, fundamentals, news, and technical indicators"
        )

    @property
    def priority(self) -> int:
        return 60

    def get_rate_limits(self) -> Dict[str, int]:
        """Alpha Vantage has strict rate limits."""
        return {
            "per_minute": self.config.get("rate_limit_per_minute", 5),
            "per_day": self.config.get("rate_limit_per_day", 500),
        }

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        """Get stock price data from Alpha Vantage."""
        return alpha_vantage.get_stock(symbol, start_date, end_date)

    def get_indicators(
        self, symbol: str, start_date: str, end_date: str, indicators: Optional[List[str]] = None
    ) -> str:
        """Get technical indicators from Alpha Vantage."""
        return alpha_vantage.get_indicator(symbol, start_date, end_date)

    def get_fundamentals(self, ticker: str, curr_date: str) -> str:
        """Get fundamental data from Alpha Vantage."""
        return alpha_vantage.get_fundamentals(ticker, curr_date)

    def get_balance_sheet(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get balance sheet data from Alpha Vantage."""
        return alpha_vantage.get_balance_sheet(ticker, freq, curr_date)

    def get_cashflow(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get cash flow data from Alpha Vantage."""
        return alpha_vantage.get_cashflow(ticker, freq, curr_date)

    def get_income_statement(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get income statement data from Alpha Vantage."""
        return alpha_vantage.get_income_statement(ticker, freq, curr_date)

    def get_insider_transactions(self, ticker: str) -> str:
        """Get insider transactions from Alpha Vantage."""
        return alpha_vantage.get_insider_transactions(ticker)

    def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> str:
        """Get news from Alpha Vantage."""
        return alpha_vantage.get_news(symbol, limit)
