# TradingAgents/graph/setup.py

from typing import Any, Callable, Dict

from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_bear_researcher,
    create_bull_researcher,
    create_fundamentals_analyst,
    create_market_analyst,
    create_msg_delete,
    create_neutral_debator,
    create_news_analyst,
    create_risk_manager,
    create_risky_debator,
    create_safe_debator,
    create_social_media_analyst,
    create_trader,
)
from tradingagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        *,
        llm_resolver: Callable[[str, str], Any],
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        agent_registry=None,
    ) -> None:
        """Initialize with required components."""
        self._llm_resolver = llm_resolver
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.agent_registry = agent_registry

    def _resolve(self, agent_name: str, llm_type: str) -> Any:
        return self._llm_resolver(agent_name, llm_type)

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph."""
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        analyst_specs = {
            "market": ("market_analyst", create_market_analyst, "market"),
            "social": ("social_analyst", create_social_media_analyst, "social"),
            "news": ("news_analyst", create_news_analyst, "news"),
            "fundamentals": ("fundamentals_analyst", create_fundamentals_analyst, "fundamentals"),
        }

        analyst_nodes: Dict[str, Any] = {}
        delete_nodes: Dict[str, Any] = {}
        tool_nodes: Dict[str, ToolNode] = {}

        for analyst_key in selected_analysts:
            if analyst_key not in analyst_specs:
                continue
            agent_name, factory, tool_key = analyst_specs[analyst_key]
            analyst_llm = self._resolve(agent_name, "quick")
            analyst_nodes[analyst_key] = factory(analyst_llm)
            delete_nodes[analyst_key] = create_msg_delete()
            tool_nodes[analyst_key] = self.tool_nodes[tool_key]

        bull_researcher_node = create_bull_researcher(
            self._resolve("bull_researcher", "quick"), self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self._resolve("bear_researcher", "quick"), self.bear_memory
        )
        research_manager_node = create_research_manager(
            self._resolve("research_manager", "deep"), self.invest_judge_memory
        )
        trader_node = create_trader(
            self._resolve("trader", "quick"), self.trader_memory
        )

        risky_analyst = create_risky_debator(self._resolve("risky_analyst", "quick"))
        neutral_analyst = create_neutral_debator(self._resolve("neutral_analyst", "quick"))
        safe_analyst = create_safe_debator(self._resolve("safe_analyst", "quick"))
        risk_manager_node = create_risk_manager(
            self._resolve("risk_manager", "deep"), self.risk_manager_memory
        )

        workflow = StateGraph(AgentState)

        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i + 1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, "Bull Researcher")

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

        workflow.add_edge("Risk Judge", END)

        return workflow.compile()
