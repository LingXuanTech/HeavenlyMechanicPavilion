# TradingAgents/graph/propagation.py

from typing import Dict, Any, Optional
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self,
        company_name: str,
        trade_date: str,
        market: str = "US",
        historical_reflection: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph.

        Args:
            company_name: Stock symbol to analyze
            trade_date: Date for the analysis
            market: Market identifier (US, HK, CN)
            historical_reflection: Optional historical analysis context from memory service
        """
        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "market": market,
            "historical_reflection": historical_reflection or "",
            "investment_debate_state": InvestDebateState(
                {"history": "", "current_response": "", "count": 0}
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "history": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                    "count": 0,
                }
            ),
            # Standard analyst reports
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            # A-share focused reports (populated only for CN/HK markets)
            "retail_sentiment_report": "",
            "policy_report": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Get arguments for the graph invocation."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
