# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional
import time

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode
import structlog

from tradingagents.agents import *
from tradingagents.agents.analysts.scout_agent import create_scout_agent
from tradingagents.agents.analysts.macro_analyst import create_macro_analyst
from tradingagents.agents.analysts.portfolio_agent import create_portfolio_agent
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

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor

logger = structlog.get_logger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=None,
        debug=False,
        config: Dict[str, Any] = None,
        market: str = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include. If None, auto-selects based on market.
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            market: Market identifier (US, HK, CN). Used to auto-select analysts if selected_analysts is None.
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.market = market

        # Auto-select analysts based on market if not specified
        if selected_analysts is None:
            selected_analysts = self._get_default_analysts(market)

        self.selected_analysts = selected_analysts

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs via unified ai_config_service
        try:
            from services.ai_config_service import ai_config_service
            self.deep_thinking_llm = ai_config_service.get_llm("deep_think")
            self.quick_thinking_llm = ai_config_service.get_llm("quick_think")
        except Exception as e:
            # 降级到原有的 config 方式（兼容 CLI 模式等）
            if self.config["llm_provider"].lower() in ["openai", "ollama", "openrouter"]:
                self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
                self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
            elif self.config["llm_provider"].lower() == "anthropic":
                self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
                self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
            elif self.config["llm_provider"].lower() == "google":
                self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
                self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
            else:
                raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
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
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        # 默认使用 Planner + L2 完整分析模式（可通过 config 配置）
        use_planner = self.config.get("use_planner", True)
        analysis_level = self.config.get("analysis_level", "L2")
        use_subgraphs = self.config.get("use_subgraphs", False)

        if use_subgraphs:
            logger.info("Using SubGraph architecture", use_planner=use_planner, analysis_level=analysis_level)
            self.graph = self.graph_setup.setup_graph_with_subgraphs(
                selected_analysts,
                use_planner=use_planner,
                analysis_level=analysis_level
            )
        else:
            self.graph = self.graph_setup.setup_graph(
                selected_analysts,
                use_planner=use_planner,
                analysis_level=analysis_level
            )
        
    def _get_default_analysts(self, market: str) -> List[str]:
        """Get default analyst list based on market using MarketAnalystRouter.

        Args:
            market: Market identifier (US, HK, CN)

        Returns:
            List of analyst types to use for this market
        """
        try:
            from services.market_analyst_router import MarketAnalystRouter, Market

            # 将字符串 market 转换为 Market 枚举
            market_enum = Market(market) if market else Market.US
            preset = MarketAnalystRouter.get_analysts_by_market(market_enum)
            logger.info("Analysts selected via MarketAnalystRouter", market=market, analysts=preset)
            return preset
        except Exception as e:
            logger.warning("MarketAnalystRouter unavailable, using fallback", error=str(e))
            # Fallback: 保持原有逻辑
            base_analysts = ["market", "social", "news", "fundamentals"]
            if market == "CN":
                return base_analysts + ["sentiment", "policy", "fund_flow"]
            elif market == "HK":
                return base_analysts + ["sentiment"]
            else:
                return base_analysts

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

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date.

        Args:
            company_name: Stock symbol to analyze
            trade_date: Date of analysis

        Returns:
            Tuple of (final_state, processed_signal)
        """
        self.ticker = company_name
        start_time = time.time()

        logger.info("Starting analysis", symbol=company_name, date=trade_date)

        # 设置 LangSmith 追踪标签
        self._setup_langsmith_tracing(company_name, trade_date)

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date, market=self.market or "US"
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

        elapsed = time.time() - start_time
        logger.info(
            "Analysis completed",
            symbol=company_name,
            elapsed_seconds=round(elapsed, 2),
        )

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"])

    def _setup_langsmith_tracing(self, company_name: str, trade_date: str):
        """设置 LangSmith 追踪上下文"""
        try:
            from services.langsmith_service import langsmith_service

            if langsmith_service.is_enabled():
                # 设置运行名称和标签
                os.environ["LANGCHAIN_RUN_NAME"] = f"analyze_{company_name}_{trade_date}"
                os.environ["LANGCHAIN_TAGS"] = f"stock_analysis,symbol={company_name}"
                logger.debug("LangSmith tracing enabled", symbol=company_name)
        except Exception as e:
            logger.debug("LangSmith not available", error=str(e))

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market": final_state.get("market", "US"),
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            # A-share focused reports
            "retail_sentiment_report": final_state.get("retail_sentiment_report", ""),
            "policy_report": final_state.get("policy_report", ""),
            "china_flow_data": final_state.get("china_flow_data", ""),
            # Planner/Scout/Macro/Portfolio reports
            "macro_report": final_state.get("macro_report", ""),
            "portfolio_report": final_state.get("portfolio_report", ""),
            "scout_report": final_state.get("scout_report", ""),
            "opportunities": final_state.get("opportunities", []),
            "recommended_analysts": final_state.get("recommended_analysts", []),
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
