"""Base class for data vendor plugins."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class PluginCapability(str, Enum):
    """Capabilities that a plugin can provide."""

    STOCK_DATA = "stock_data"
    INDICATORS = "indicators"
    FUNDAMENTALS = "fundamentals"
    BALANCE_SHEET = "balance_sheet"
    CASHFLOW = "cashflow"
    INCOME_STATEMENT = "income_statement"
    NEWS = "news"
    GLOBAL_NEWS = "global_news"
    INSIDER_SENTIMENT = "insider_sentiment"
    INSIDER_TRANSACTIONS = "insider_transactions"


class DataVendorPlugin(ABC):
    """Abstract base class for data vendor plugins.

    Each vendor plugin must implement this interface to integrate
    with the TradingAgents data vendor system.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin with optional configuration.

        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
        self._validate_config()

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the vendor plugin."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return the provider name (e.g., 'yfinance', 'alpha_vantage')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[PluginCapability]:
        """Return list of capabilities this plugin provides."""
        pass

    @property
    def description(self) -> str:
        """Return a human-readable description of the plugin."""
        return f"{self.provider} data vendor plugin"

    @property
    def version(self) -> str:
        """Return the plugin version."""
        return "1.0.0"

    @property
    def priority(self) -> int:
        """Return the default priority for this plugin (lower is higher priority).

        Can be overridden by configuration.
        """
        return 100

    def _validate_config(self) -> None:
        """Validate the plugin configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def supports(self, capability: PluginCapability) -> bool:
        """Check if this plugin supports a given capability.

        Args:
            capability: The capability to check

        Returns:
            bool: True if the capability is supported
        """
        return capability in self.capabilities

    def get_rate_limits(self) -> Dict[str, int]:
        """Return rate limit information for this vendor.

        Returns:
            Dict with 'per_minute' and 'per_day' keys
        """
        return {
            "per_minute": self.config.get("rate_limit_per_minute"),
            "per_day": self.config.get("rate_limit_per_day"),
        }

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        """Get stock price data (OHLCV).

        Args:
            symbol: Ticker symbol
            start_date: Start date in yyyy-mm-dd format
            end_date: End date in yyyy-mm-dd format

        Returns:
            Formatted string with stock data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support stock data retrieval")

    def get_indicators(
        self, symbol: str, start_date: str, end_date: str, indicators: Optional[List[str]] = None
    ) -> str:
        """Get technical indicators.

        Args:
            symbol: Ticker symbol
            start_date: Start date in yyyy-mm-dd format
            end_date: End date in yyyy-mm-dd format
            indicators: List of indicator names to retrieve

        Returns:
            Formatted string with indicator data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support technical indicators")

    def get_fundamentals(self, ticker: str, curr_date: str) -> str:
        """Get fundamental data for a company.

        Args:
            ticker: Ticker symbol
            curr_date: Current date in yyyy-mm-dd format

        Returns:
            Formatted string with fundamental data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support fundamental data retrieval")

    def get_balance_sheet(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get balance sheet data.

        Args:
            ticker: Ticker symbol
            freq: Reporting frequency (annual/quarterly)
            curr_date: Current date in yyyy-mm-dd format

        Returns:
            Formatted string with balance sheet data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support balance sheet retrieval")

    def get_cashflow(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get cash flow statement data.

        Args:
            ticker: Ticker symbol
            freq: Reporting frequency (annual/quarterly)
            curr_date: Current date in yyyy-mm-dd format

        Returns:
            Formatted string with cash flow data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support cash flow retrieval")

    def get_income_statement(
        self, ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None
    ) -> str:
        """Get income statement data.

        Args:
            ticker: Ticker symbol
            freq: Reporting frequency (annual/quarterly)
            curr_date: Current date in yyyy-mm-dd format

        Returns:
            Formatted string with income statement data

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support income statement retrieval")

    def get_news(self, symbol: Optional[str] = None, limit: int = 10) -> str:
        """Get news articles.

        Args:
            symbol: Ticker symbol (None for global news)
            limit: Maximum number of articles to retrieve

        Returns:
            Formatted string with news articles

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support news retrieval")

    def get_global_news(self, limit: int = 10) -> str:
        """Get global/market news.

        Args:
            limit: Maximum number of articles to retrieve

        Returns:
            Formatted string with news articles

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support global news retrieval")

    def get_insider_sentiment(self, symbol: str) -> str:
        """Get insider sentiment data.

        Args:
            symbol: Ticker symbol

        Returns:
            Formatted string with insider sentiment

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support insider sentiment retrieval")

    def get_insider_transactions(self, ticker: str) -> str:
        """Get insider transaction data.

        Args:
            ticker: Ticker symbol

        Returns:
            Formatted string with insider transactions

        Raises:
            NotImplementedError: If not supported by this plugin
        """
        raise NotImplementedError(f"{self.name} does not support insider transactions retrieval")
