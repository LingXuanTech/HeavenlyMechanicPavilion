"""Minimal example that runs the TradingAgents graph."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure the project sources are importable when running the script directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


def main() -> None:
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
