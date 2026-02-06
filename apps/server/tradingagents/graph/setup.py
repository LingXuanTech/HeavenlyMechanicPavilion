# TradingAgents/graph/setup.py

from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
import structlog

from tradingagents.agents import *
from tradingagents.agents.analysts.planner_agent import create_planner_agent
from tradingagents.agents.analysts.macro_analyst import create_macro_analyst
from tradingagents.agents.analysts.portfolio_agent import create_portfolio_agent
from tradingagents.agents.analysts.sentiment_agent import create_sentiment_agent, create_sentiment_tools_node
from tradingagents.agents.analysts.policy_agent import create_policy_agent, create_policy_tools_node
from tradingagents.agents.analysts.fund_flow_agent import create_fund_flow_agent, create_fund_flow_tools_node
from tradingagents.agents.utils.agent_states import (
    AgentState,
    AnalystType,
    get_all_reports,
    get_missing_reports,
)

from .conditional_logic import ConditionalLogic
from .resilience import AnalystNodeFactory, ResilientNodeWrapper
from .subgraphs import AnalystSubGraph, DebateSubGraph, RiskSubGraph

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
        enable_resilience: bool = True,
        custom_timeouts: Optional[Dict[str, float]] = None,
    ):
        """Initialize with required components.

        Args:
            quick_thinking_llm: Fast LLM for quick analysis
            deep_thinking_llm: Deep LLM for complex reasoning
            tool_nodes: Tool nodes for each analyst type
            bull_memory: Bull researcher memory
            bear_memory: Bear researcher memory
            trader_memory: Trader memory
            invest_judge_memory: Investment judge memory
            risk_manager_memory: Risk manager memory
            conditional_logic: Conditional logic handler
            enable_resilience: Enable timeout and graceful degradation (default: True)
            custom_timeouts: Custom timeout settings per analyst type (seconds)
        """
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.enable_resilience = enable_resilience
        self.custom_timeouts = custom_timeouts or {}

    def _create_parallel_router(self):
        """创建并行路由器节点（空操作，仅用于分支起点）"""
        def parallel_router_node(state):
            # 使用 Planner 推荐的分析师（如果有），否则使用默认
            recommended = state.get("recommended_analysts", [])
            if recommended:
                logger.info("Parallel router: using Planner recommendations", analysts=recommended)
            else:
                logger.info("Parallel router: starting parallel execution with static selection")
            return state
        return parallel_router_node

    def _create_dynamic_router(self, all_analysts: List[str]):
        """创建动态路由函数，根据 recommended_analysts 决定激活哪些分析师

        Args:
            all_analysts: 所有可用的分析师类型列表

        Returns:
            路由函数
        """
        def route_to_analysts(state) -> List[str]:
            """根据 state 中的 recommended_analysts 返回要激活的节点"""
            recommended = state.get("recommended_analysts", [])
            if not recommended:
                # 如果 Planner 没有推荐，使用全部
                recommended = all_analysts

            # 返回要激活的节点名称列表
            active_nodes = []
            for analyst_type in recommended:
                if analyst_type in all_analysts:
                    active_nodes.append(f"{analyst_type.capitalize()} Analyst")

            logger.debug("Dynamic router activating analysts", active=active_nodes)
            return active_nodes

        return route_to_analysts

    def _create_analyst_sync(self):
        """创建分析师汇聚点节点"""
        def sync_analysts_node(state):
            """验证所有分析报告并清理消息"""
            # 使用动态工具函数获取报告状态
            all_reports = get_all_reports(state)
            missing = get_missing_reports(state)

            # 检查降级报告
            degraded = [
                k for k, v in all_reports.items()
                if v and "unavailable" in v.lower()
            ]

            if missing:
                logger.warning("Analyst sync: missing reports", missing=missing)
            elif degraded:
                logger.warning("Analyst sync: degraded reports", degraded=degraded)
            else:
                logger.info("Analyst sync: all required reports received")

            # 记录可选报告状态
            optional_received = [
                k for k in AnalystType.CN_ONLY
                if k in all_reports and all_reports[k]
            ]
            if optional_received:
                logger.info("Analyst sync: optional reports received", reports=optional_received)

            # 清理堆积的消息（保留最后 3 条）
            messages = state.get("messages", [])
            sync_message = "All analysts completed."
            if degraded:
                sync_message += f" Note: {len(degraded)} report(s) degraded: {', '.join(degraded)}."
            sync_message += " Proceeding to debate."

            if len(messages) > 3:
                removal_ops = [RemoveMessage(id=m.id) for m in messages[:-3] if hasattr(m, 'id') and m.id]
                return {
                    "messages": removal_ops + [HumanMessage(content=sync_message)]
                }

            return {"messages": [HumanMessage(content=sync_message)]}

        return sync_analysts_node

    def setup_graph(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        use_planner: bool = True,
        analysis_level: str = "L2",
    ):
        """Set up and compile the agent workflow graph with parallel analyst execution.

        Args:
            selected_analysts (list): List of analyst types to include (used when use_planner=False
                or as fallback). Options are:
                - "market": Market analyst (technical analysis)
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
                - "macro": Macro economic analyst
                - "sentiment": Retail sentiment analyst (FOMO/FUD detection)
                - "policy": Policy analyst (A-share regulations, CN market only)
                - "fund_flow": Fund flow analyst (North money + LHB, CN market only)
            use_planner (bool): Whether to use Planner for dynamic analyst selection.
                - True (default): Planner runs first and recommends analysts
                - False: Use static selected_analysts
            analysis_level (str): Analysis depth level.
                - "L1": Quick scan (Market + News + Macro only, no debate)
                - "L2": Full analysis (all selected analysts + debate)
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        logger.info(
            "Setting up graph",
            analysts=selected_analysts,
            use_planner=use_planner,
            analysis_level=analysis_level,
            resilience=self.enable_resilience,
        )

        # L1 模式：简化分析师集合
        if analysis_level == "L1":
            selected_analysts = ["market", "news", "macro"]
            use_planner = False  # L1 模式不使用 Planner
            logger.info("L1 mode: using quick scan analysts", analysts=selected_analysts)

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            node = create_market_analyst(self.quick_thinking_llm)
            analyst_nodes["market"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "market", self.custom_timeouts.get("market"))
                if self.enable_resilience else node
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            node = create_social_media_analyst(self.quick_thinking_llm)
            analyst_nodes["social"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "social", self.custom_timeouts.get("social"))
                if self.enable_resilience else node
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            node = create_news_analyst(self.quick_thinking_llm)
            analyst_nodes["news"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "news", self.custom_timeouts.get("news"))
                if self.enable_resilience else node
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            node = create_fundamentals_analyst(self.quick_thinking_llm)
            analyst_nodes["fundamentals"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "fundamentals", self.custom_timeouts.get("fundamentals"))
                if self.enable_resilience else node
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # New A-share focused analysts
        if "sentiment" in selected_analysts:
            node = create_sentiment_agent(self.quick_thinking_llm)
            analyst_nodes["sentiment"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "sentiment", self.custom_timeouts.get("sentiment"))
                if self.enable_resilience else node
            )
            delete_nodes["sentiment"] = create_msg_delete()
            tool_nodes["sentiment"] = create_sentiment_tools_node(self.quick_thinking_llm)

        if "policy" in selected_analysts:
            node = create_policy_agent(self.quick_thinking_llm)
            analyst_nodes["policy"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "policy", self.custom_timeouts.get("policy"))
                if self.enable_resilience else node
            )
            delete_nodes["policy"] = create_msg_delete()
            tool_nodes["policy"] = create_policy_tools_node(self.quick_thinking_llm)

        # 资金流向分析师（北向资金 + 龙虎榜）
        if "fund_flow" in selected_analysts:
            node = create_fund_flow_agent(self.quick_thinking_llm)
            analyst_nodes["fund_flow"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "fund_flow", self.custom_timeouts.get("fund_flow"))
                if self.enable_resilience else node
            )
            delete_nodes["fund_flow"] = create_msg_delete()
            tool_nodes["fund_flow"] = create_fund_flow_tools_node(self.quick_thinking_llm)

        # Macro 分析师（现在可以并行执行）
        if "macro" in selected_analysts:
            node = create_macro_analyst(self.quick_thinking_llm)
            analyst_nodes["macro"] = (
                AnalystNodeFactory.wrap_analyst_node(node, "macro", self.custom_timeouts.get("macro"))
                if self.enable_resilience else node
            )
            delete_nodes["macro"] = create_msg_delete()
            # Macro 使用与 news 相同的工具（全球新闻等）
            tool_nodes["macro"] = self.tool_nodes.get("news", ToolNode([]))

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

        # Add Planner node (replaces old Scout Agent)
        planner_node = create_planner_agent(self.quick_thinking_llm, default_analysts=selected_analysts)
        portfolio_node = create_portfolio_agent(self.quick_thinking_llm)

        if use_planner:
            workflow.add_node("Planner", planner_node)
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

        # Add other nodes (only for L2 full analysis)
        if analysis_level == "L2":
            workflow.add_node("Bull Researcher", bull_researcher_node)
            workflow.add_node("Bear Researcher", bear_researcher_node)
            workflow.add_node("Research Manager", research_manager_node)
            workflow.add_node("Trader", trader_node)
            workflow.add_node("Risky Analyst", risky_analyst)
            workflow.add_node("Neutral Analyst", neutral_analyst)
            workflow.add_node("Safe Analyst", safe_analyst)
            workflow.add_node("Risk Judge", risk_manager_node)

        # ============ 边定义 ============

        # 1. Start: Planner (if enabled) or direct to Parallel Router
        if use_planner:
            workflow.add_edge(START, "Planner")
            workflow.add_edge("Planner", "Analyst Parallel Router")
        else:
            workflow.add_edge(START, "Analyst Parallel Router")

        # 2. Parallel Router -> 所有分析师 (并行扇出)
        for analyst_type in selected_analysts:
            if analyst_type in analyst_nodes:  # 确保节点存在
                workflow.add_edge(
                    "Analyst Parallel Router",
                    f"{analyst_type.capitalize()} Analyst"
                )

        # 3. 每个分析师的工具调用和消息清理
        for analyst_type in selected_analysts:
            if analyst_type not in analyst_nodes:
                continue

            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # 条件边：如果有 tool_calls 执行工具，否则清空消息
            should_continue_method = getattr(
                self.conditional_logic,
                f"should_continue_{analyst_type}",
                self.conditional_logic.should_continue_market  # fallback
            )
            workflow.add_conditional_edges(
                current_analyst,
                should_continue_method,
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

        # 4. 所有清理节点 -> 汇聚点 (并行扇入)
        for analyst_type in selected_analysts:
            if analyst_type in analyst_nodes:
                current_clear = f"Msg Clear {analyst_type.capitalize()}"
                workflow.add_edge(current_clear, "Analyst Results Sync")

        # 5. 根据分析级别决定后续流程
        if analysis_level == "L1":
            # L1 模式：直接到 Portfolio Agent 然后结束
            workflow.add_edge("Analyst Results Sync", "Portfolio Agent")
            workflow.add_edge("Portfolio Agent", END)
        else:
            # L2 模式：完整辩论流程
            workflow.add_edge("Analyst Results Sync", "Bull Researcher")

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

        logger.info(
            "Graph setup complete",
            use_planner=use_planner,
            analysis_level=analysis_level,
            analyst_count=len(analyst_nodes),
        )

        # Compile and return
        return workflow.compile()

    def setup_graph_with_subgraphs(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        use_planner: bool = True,
        analysis_level: str = "L2",
    ):
        """使用 SubGraph 架构构建工作流图

        将分析师、辩论、风险评估分别封装为独立子图，
        主图只负责编排子图的执行顺序。

        架构：
        ```
        MainGraph
          ├─ Planner (可选)
          ├─ AnalystSubGraph (并行分析师执行)
          ├─ Trader
          ├─ DebateSubGraph (Bull vs Bear 辩论)  [L2 only]
          ├─ RiskSubGraph (三方风险辩论)  [L2 only]
          └─ Portfolio Agent
        ```

        Args:
            selected_analysts: 选定的分析师列表
            use_planner: 是否使用 Planner
            analysis_level: 分析级别 (L1/L2)

        Returns:
            编译后的 CompiledGraph
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        logger.info(
            "Setting up graph with SubGraphs",
            analysts=selected_analysts,
            use_planner=use_planner,
            analysis_level=analysis_level,
        )

        # L1 模式：简化分析师集合
        if analysis_level == "L1":
            selected_analysts = ["market", "news", "macro"]
            use_planner = False
            logger.info("L1 mode: quick scan", analysts=selected_analysts)

        # 构建子图
        analyst_subgraph = AnalystSubGraph(
            quick_thinking_llm=self.quick_thinking_llm,
            tool_nodes=self.tool_nodes,
            conditional_logic=self.conditional_logic,
            selected_analysts=selected_analysts,
            enable_resilience=self.enable_resilience,
            custom_timeouts=self.custom_timeouts,
        ).compile()

        # 主图
        workflow = StateGraph(AgentState)

        # Planner 节点（可选）
        if use_planner:
            planner_node = create_planner_agent(
                self.quick_thinking_llm,
                default_analysts=selected_analysts,
            )
            workflow.add_node("Planner", planner_node)

        # 分析师子图作为节点
        workflow.add_node("Analysts", analyst_subgraph)

        # Portfolio Agent
        portfolio_node = create_portfolio_agent(self.quick_thinking_llm)
        workflow.add_node("Portfolio Agent", portfolio_node)

        if analysis_level == "L2":
            # Trader 节点
            trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)
            workflow.add_node("Trader", trader_node)

            # 辩论子图
            debate_subgraph = DebateSubGraph(
                quick_thinking_llm=self.quick_thinking_llm,
                deep_thinking_llm=self.deep_thinking_llm,
                bull_memory=self.bull_memory,
                bear_memory=self.bear_memory,
                invest_judge_memory=self.invest_judge_memory,
                max_debate_rounds=self.conditional_logic.max_debate_rounds,
            ).compile()
            workflow.add_node("Debate", debate_subgraph)

            # 风险评估子图
            risk_subgraph = RiskSubGraph(
                quick_thinking_llm=self.quick_thinking_llm,
                deep_thinking_llm=self.deep_thinking_llm,
                risk_manager_memory=self.risk_manager_memory,
                max_risk_discuss_rounds=self.conditional_logic.max_risk_discuss_rounds,
            ).compile()
            workflow.add_node("Risk", risk_subgraph)

        # ============ 边定义 ============

        # START -> Planner 或 Analysts
        if use_planner:
            workflow.add_edge(START, "Planner")
            workflow.add_edge("Planner", "Analysts")
        else:
            workflow.add_edge(START, "Analysts")

        if analysis_level == "L1":
            # L1: Analysts -> Portfolio -> END
            workflow.add_edge("Analysts", "Portfolio Agent")
            workflow.add_edge("Portfolio Agent", END)
        else:
            # L2: Analysts -> Debate -> Trader -> Risk -> Portfolio -> END
            workflow.add_edge("Analysts", "Debate")
            workflow.add_edge("Debate", "Trader")
            workflow.add_edge("Trader", "Risk")
            workflow.add_edge("Risk", "Portfolio Agent")
            workflow.add_edge("Portfolio Agent", END)

        logger.info(
            "SubGraph-based graph setup complete",
            use_planner=use_planner,
            analysis_level=analysis_level,
            mode="subgraph",
        )

        return workflow.compile()
