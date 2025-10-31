"""YFinance vendor plugin."""

from typing import List, Optional

from tradingagents.dataflows import y_finance
from tradingagents.plugins.base import DataVendorPlugin, PluginCapability


class YFinancePlugin(DataVendorPlugin):
    """Plugin for Yahoo Finance data vendor."""

    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def provider(self) -> str:
        return "yfinance"

    @property
    def capabilities(self) -> List[PluginCapability]:
        return [
            PluginCapability.STOCK_DATA,
            PluginCapability.INDICATORS,
            PluginCapability.BALANCE_SHEET,
            PluginCapability.CASHFLOW,
            PluginCapability.INCOME_STATEMENT,
            PluginCapability.INSIDER_TRANSACTIONS,
        ]

    @property
    def description(self) -> str:
        return "Yahoo Finance data provider for stocks, fundamentals, and technical indicators"

    @property
    def priority(self) -> int:
        return 50

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        """Get stock price data from Yahoo Finance."""
        return y_finance.get_YFin_data_online(symbol, start_date, end_date)

    def get_indicators(
        self, symbol: str, start_date: str, end_date: str, indicators: Optional[List[str]] = None
    ) -> str:
        """Get technical indicators from Yahoo Finance."""
        return y_finance.get_stock_stats_indicators_window(symbol, start_date, end_date)

    def get_balance_sheet(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get balance sheet data from Yahoo Finance."""
        return y_finance.get_balance_sheet(ticker, freq, curr_date)

    def get_cashflow(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get cash flow data from Yahoo Finance."""
        return y_finance.get_cashflow(ticker, freq, curr_date)

    def get_income_statement(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get income statement data from Yahoo Finance."""
        return y_finance.get_income_statement(ticker, freq, curr_date)

    def get_insider_transactions(self, ticker: str) -> str:
        """Get insider transactions from Yahoo Finance."""
        return y_finance.get_insider_transactions(ticker)
