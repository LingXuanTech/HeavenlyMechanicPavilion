"""Command line entry point for ad-hoc experimentation."""

from __future__ import annotations

from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def main() -> None:
    """Run a demo propagation with a sample configuration."""
    load_dotenv()

    config = DEFAULT_CONFIG.copy()
    config["deep_think_llm"] = "gpt-4o-mini"
    config["quick_think_llm"] = "gpt-4o-mini"
    config["max_debate_rounds"] = 1
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "alpha_vantage",
        "news_data": "alpha_vantage",
    }

    trading_graph = TradingAgentsGraph(debug=True, config=config)
    _, decision = trading_graph.propagate("NVDA", "2024-05-10")
    print(decision)


if __name__ == "__main__":
    main()
