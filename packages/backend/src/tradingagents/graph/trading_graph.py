# TradingAgents/graph/trading_graph.py

import logging
import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

# Import the new abstract tool methods from agent_utils
from tradingagents.agents.utils.agent_utils import (
    get_stock_data,
    get_indicators,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news
)

logger = logging.getLogger(__name__)

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
        use_plugin_system: bool = False,
        llm_runtime: Optional[Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            use_plugin_system: Whether to use the new plugin system for agents
            llm_runtime: Optional runtime manager for dynamic LLM resolution
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.use_plugin_system = use_plugin_system
        self.llm_runtime = llm_runtime

        # Update the interface's config
        set_config(self.config)
        
        # Initialize agent registry if using plugin system
        if self.use_plugin_system:
            from tradingagents.agents.plugin_loader import register_built_in_plugins
            from tradingagents.agents import get_agent_registry
            self.agent_registry = get_agent_registry()
            register_built_in_plugins(self.agent_registry)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize fallback LLMs for legacy and error scenarios
        self._default_llms = self._initialize_default_llms()
        self.quick_thinking_llm = self._default_llms.get("quick")
        self.deep_thinking_llm = self._default_llms.get("deep")

        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            llm_resolver=self._resolve_llm,
            tool_nodes=self.tool_nodes,
            bull_memory=self.bull_memory,
            bear_memory=self.bear_memory,
            trader_memory=self.trader_memory,
            invest_judge_memory=self.invest_judge_memory,
            risk_manager_memory=self.risk_manager_memory,
            conditional_logic=self.conditional_logic,
            agent_registry=self.agent_registry if self.use_plugin_system else None,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self._resolve_llm("reflector", "quick"))
        self.signal_processor = SignalProcessor(self._resolve_llm("signal_processor", "quick"))

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Core stock data tools
                    get_stock_data,
                    # Technical indicators
                    get_indicators,
                ]
            ),
            "social": ToolNode(
                [
                    # News tools for social media analysis
                    get_news,
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    get_news,
                    get_global_news,
                    get_insider_sentiment,
                    get_insider_transactions,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_fundamentals,
                    get_balance_sheet,
                    get_cashflow,
                    get_income_statement,
                ]
            ),
        }

    def _initialize_default_llms(self) -> Dict[str, Any]:
        """Create baseline LLM instances used when runtime configs are unavailable."""
        defaults: Dict[str, Any] = {}
        provider = (self.config.get("llm_provider") or "openai").lower()
        backend_url = self.config.get("backend_url")
        quick_model = self.config.get("quick_think_llm")
        deep_model = self.config.get("deep_think_llm")

        try:
            if provider in {"openai", "ollama", "openrouter"}:
                if deep_model:
                    kwargs: Dict[str, Any] = {"model": deep_model}
                    if backend_url:
                        kwargs["base_url"] = backend_url
                    defaults["deep"] = ChatOpenAI(**kwargs)
                if quick_model:
                    kwargs = {"model": quick_model}
                    if backend_url:
                        kwargs["base_url"] = backend_url
                    defaults["quick"] = ChatOpenAI(**kwargs)
            elif provider == "anthropic":
                if deep_model:
                    kwargs = {"model": deep_model}
                    if backend_url:
                        kwargs["base_url"] = backend_url
                    defaults["deep"] = ChatAnthropic(**kwargs)
                if quick_model:
                    kwargs = {"model": quick_model}
                    if backend_url:
                        kwargs["base_url"] = backend_url
                    defaults["quick"] = ChatAnthropic(**kwargs)
            elif provider == "google":
                if deep_model:
                    defaults["deep"] = ChatGoogleGenerativeAI(model=deep_model)
                if quick_model:
                    defaults["quick"] = ChatGoogleGenerativeAI(model=quick_model)
            else:
                logger.warning("Unsupported LLM provider configured: %s", provider)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize default LLMs: %s", exc)

        return defaults

    def _resolve_llm(self, agent_name: str, llm_type: str) -> Any:
        """Resolve the LLM instance for a specific agent."""
        if self.llm_runtime:
            try:
                managed = self.llm_runtime.get_llm(agent_name, llm_type)
                if managed is not None:
                    return managed
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("LLM runtime resolution failed for %s: %s", agent_name, exc)

        fallback = self._default_llms.get(llm_type)
        if fallback is None:
            raise ValueError(f"No fallback LLM configured for type '{llm_type}'")
        return fallback

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"])

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
