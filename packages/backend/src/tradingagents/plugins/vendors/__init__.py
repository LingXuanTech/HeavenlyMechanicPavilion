"""Built-in vendor plugins."""

from .alpha_vantage import AlphaVantagePlugin
from .google import GooglePlugin
from .local import LocalPlugin
from .openai import OpenAIPlugin
from .yfinance import YFinancePlugin

__all__ = [
    "AlphaVantagePlugin",
    "GooglePlugin",
    "LocalPlugin",
    "OpenAIPlugin",
    "YFinancePlugin",
]
