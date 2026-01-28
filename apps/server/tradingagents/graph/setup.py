# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
import structlog

from tradingagents.agents import *
from tradingagents.agents.analysts.scout_agent import create_scout_agent
from tradingagents.agents.analysts.macro_analyst import create_macro_analyst
from tradingagents.agents.analysts.portfolio_agent import create_portfolio_agent
from tradingagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic

logger = structlog.get_logger(__name__)


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic

    def _create_parallel_router(self):
        """创建并行路由器节点（空操作，仅用于分支起点）"""
        def parallel_router_node(state):
            logger.info("Analyst parallel router: starting parallel execution")
            return state
        return parallel_router_node

    def _create_analyst_sync(self):
        """创建分析师汇聚点节点"""
        def sync_analysts_node(state):
            """验证所有分析报告并清理消息"""
            # 验证所有分析报告都已生成
            required_reports = {
                "market_report": state.get("market_report", ""),
                "sentiment_report": state.get("sentiment_report", ""),
                "news_report": state.get("news_report", ""),
                "fundamentals_report": state.get("fundamentals_report", ""),
            }

            missing = [k for k, v in required_reports.items() if not v]
            if missing:
                logger.warning("Analyst sync: missing reports", missing=missing)
            else:
                logger.info("Analyst sync: all reports received")

            # 清理堆积的消息（保留最后 3 条）
            messages = state.get("messages", [])
            if len(messages) > 3:
                removal_ops = [RemoveMessage(id=m.id) for m in messages[:-3]]
                return {
                    "messages": removal_ops + [HumanMessage(content="All analysts completed. Proceeding to debate.")]
                }

            return {"messages": [HumanMessage(content="All analysts completed. Proceeding to debate.")]}

        return sync_analysts_node

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph with parallel analyst execution.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        logger.info("Setting up graph with parallel analysts", analysts=selected_analysts)

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        risky_analyst = create_risky_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add new agents
        scout_node = create_scout_agent(self.quick_thinking_llm)
        macro_node = create_macro_analyst(self.quick_thinking_llm)
        portfolio_node = create_portfolio_agent(self.quick_thinking_llm)

        workflow.add_node("Scout Agent", scout_node)
        workflow.add_node("Macro Analyst", macro_node)
        workflow.add_node("Portfolio Agent", portfolio_node)

        # Add parallel infrastructure nodes
        workflow.add_node("Analyst Parallel Router", self._create_parallel_router())
        workflow.add_node("Analyst Results Sync", self._create_analyst_sync())

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # ============ 新的并行化边定义 ============

        # 1. Start with Macro Analyst
        workflow.add_edge(START, "Macro Analyst")

        # 2. Macro Analyst -> Parallel Router (扇出起点)
        workflow.add_edge("Macro Analyst", "Analyst Parallel Router")

        # 3. Parallel Router -> 所有分析师 (并行扇出)
        for analyst_type in selected_analysts:
            workflow.add_edge(
                "Analyst Parallel Router",
                f"{analyst_type.capitalize()} Analyst"
            )

        # 4. 每个分析师的工具调用和消息清理
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # 条件边：如果有 tool_calls 执行工具，否则清空消息
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

        # 5. 所有清理节点 -> 汇聚点 (并行扇入)
        for analyst_type in selected_analysts:
            current_clear = f"Msg Clear {analyst_type.capitalize()}"
            workflow.add_edge(current_clear, "Analyst Results Sync")

        # 6. 汇聚点 -> Bull Researcher (开始辩论)
        workflow.add_edge("Analyst Results Sync", "Bull Researcher")

        # ============ 剩余边保持不变 ============

        # Add remaining edges for debate
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", "Portfolio Agent")
        workflow.add_edge("Portfolio Agent", END)

        logger.info("Graph setup complete with parallel analyst execution")

        # Compile and return
        return workflow.compile()
