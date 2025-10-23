"""Quick smoke test for the y_finance dataflow helpers."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradingagents.dataflows.y_finance import get_stock_stats_indicators_window


def main() -> None:
    print("Testing optimized implementation with 30-day lookback:")
    start_time = time.time()
    result = get_stock_stats_indicators_window("AAPL", "macd", "2024-11-01", 30)
    end_time = time.time()

    print(f"Execution time: {end_time - start_time:.2f} seconds")
    print(f"Result length: {len(result)} characters")
    print(result)


if __name__ == "__main__":
    main()
