"""Service layer integrating the TradingAgents graph with FastAPI endpoints."""

from __future__ import annotations

import asyncio
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from .events import SessionEventManager

DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"]


class TradingGraphService:
    """Wrapper around ``TradingAgentsGraph`` exposing API focused actions."""

    def __init__(
        self,
        event_manager: SessionEventManager,
        *,
        config_overrides: Optional[Dict[str, Any]] = None,
        max_workers: int = 2,
    ) -> None:
        self._event_manager = event_manager
        self._base_config = deepcopy(DEFAULT_CONFIG)
        if config_overrides:
            self._base_config.update(config_overrides)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, Future] = {}

    # ------------------------------------------------------------------
    # Health & configuration helpers
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        """Return a simple health summary."""

        status = "ok"
        details = {
            "llm_provider": self._base_config.get("llm_provider"),
            "deep_think_llm": self._base_config.get("deep_think_llm"),
            "quick_think_llm": self._base_config.get("quick_think_llm"),
        }
        return {"status": status, "details": details}

    def configuration(self) -> Dict[str, Any]:
        """Expose the configuration used when instantiating the graph."""

        return deepcopy(self._base_config)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    async def run_session(
        self,
        *,
        ticker: str,
        trade_date: date,
        selected_analysts: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Kick off a graph run and return the session metadata."""

        session_id = str(uuid4())
        await self._event_manager.create_stream(session_id)

        loop = asyncio.get_running_loop()
        analysts = list(selected_analysts) if selected_analysts else DEFAULT_ANALYSTS

        def _execute() -> None:
            self._event_manager.publish(
                session_id,
                {
                    "type": "status",
                    "message": "session_started",
                    "ticker": ticker,
                    "trade_date": trade_date.isoformat(),
                },
            )

            graph = TradingAgentsGraph(
                selected_analysts=analysts,
                config=deepcopy(self._base_config),
            )

            try:
                final_state, processed_signal = graph.propagate(
                    ticker, trade_date.isoformat()
                )
                self._event_manager.publish(
                    session_id,
                    {
                        "type": "result",
                        "final_trade_decision": final_state.get("final_trade_decision"),
                        "processed_signal": processed_signal,
                        "investment_plan": final_state.get("investment_plan"),
                    },
                )
                self._event_manager.publish(
                    session_id,
                    {
                        "type": "completed",
                        "message": "session_completed",
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                self._event_manager.publish(
                    session_id,
                    {
                        "type": "error",
                        "message": str(exc),
                    },
                )
            finally:
                self._event_manager.close(session_id)

        future: Future = loop.run_in_executor(self._executor, _execute)
        self._tasks[session_id] = future
        future.add_done_callback(lambda _: self._tasks.pop(session_id, None))

        return {
            "session_id": session_id,
            "stream_endpoint": f"/sessions/{session_id}/events",
        }

    async def ensure_session_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Return the queue for an existing session."""

        return await self._event_manager.get_stream(session_id)
