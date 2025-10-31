# TradingAgents/graph/trading_graph.py

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *

# Import the new abstract tool methods from specialized modules
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.news_data_tools import (
    get_global_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_news,
)
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG

from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .reflection import Reflector
from .setup import GraphSetup
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


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

        # Log runtime manager status
        if self.llm_runtime:
            logger.info("AgentLLMRuntime available for dynamic LLM configuration")
        else:
            logger.info("No runtime manager provided, using default LLMs only")

        # Update the interface's config
        set_config(self.config)

        # Initialize agent registry if using plugin system
        if self.use_plugin_system:
            from tradingagents.agents import get_agent_registry
            from tradingagents.agents.plugin_loader import register_built_in_plugins

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
        """Create baseline LLM instances used when runtime configs are unavailable.

        Note: This is only used as a last resort fallback when llm_runtime is not provided.
        The preferred approach is to inject an LLMRuntimeManager instance.
        """
        defaults: Dict[str, Any] = {}

        # Simplified fallback - just create basic OpenAI instances
        try:
            quick_model = self.config.get("quick_think_llm", "gpt-4o-mini")
            deep_model = self.config.get("deep_think_llm", "gpt-4-turbo")

            defaults["quick"] = ChatOpenAI(model=quick_model)
            defaults["deep"] = ChatOpenAI(model=deep_model)

            logger.info(f"Initialized fallback LLMs: quick={quick_model}, deep={deep_model}")
        except Exception as exc:
            logger.error("Failed to initialize fallback LLMs: %s", exc)

        return defaults

    def _resolve_llm(self, agent_name: str, llm_type: str = "quick") -> Any:
        """Resolve the LLM instance for a specific agent.

        This method follows a priority order:
        1. Try to get agent-specific LLM from runtime manager (if provided)
        2. Fall back to default LLMs based on llm_type

        Args:
            agent_name: Name of the agent requesting the LLM
            llm_type: Type of LLM - "quick" or "deep" (used for fallback only)

        Returns:
            A LangChain ChatModel instance

        Raises:
            ValueError: If no LLM can be resolved
        """
        # First priority: Use runtime manager if available
        if self.llm_runtime:
            try:
                llm = self.llm_runtime.get_llm(agent_name, llm_type)
                logger.debug(f"Resolved LLM for {agent_name} via runtime manager")
                return llm
            except Exception as exc:
                logger.warning(
                    f"Runtime LLM resolution failed for {agent_name}: {exc}. "
                    f"Falling back to default {llm_type} LLM"
                )

        # Fallback: Use default LLMs
        fallback = self._default_llms.get(llm_type)
        if fallback is None:
            raise ValueError(
                f"No LLM available for agent '{agent_name}'. "
                f"llm_runtime not provided and fallback '{llm_type}' not initialized."
            )

        logger.debug(f"Using fallback {llm_type} LLM for {agent_name}")
        return fallback

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(company_name, trade_date)
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
                "current_response": final_state["investment_debate_state"]["current_response"],
                "judge_decision": final_state["investment_debate_state"]["judge_decision"],
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
        self.reflector.reflect_bull_researcher(self.curr_state, returns_losses, self.bull_memory)
        self.reflector.reflect_bear_researcher(self.curr_state, returns_losses, self.bear_memory)
        self.reflector.reflect_trader(self.curr_state, returns_losses, self.trader_memory)
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
