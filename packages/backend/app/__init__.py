"""FastAPI application exposing the TradingAgents graph services."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the legacy ``tradingagents`` package from ``src`` remains importable when
# running the FastAPI application directly via uvicorn.
_SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if _SRC_PATH.exists() and str(_SRC_PATH) not in sys.path:  # pragma: no cover - env guard
    sys.path.append(str(_SRC_PATH))
