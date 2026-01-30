"""辩论子图 (DebateSubGraph)

封装 Bull vs Bear 研究员辩论逻辑：
- Bull Researcher 提出看涨论点
- Bear Researcher 反驳
- 多轮对抗辩论（可配置轮数）
- Research Manager 汇总裁决

私有状态：
- investment_debate_state: 辩论进度和历史
- debate_round: 当前轮次

输出：
- investment_plan: Research Manager 的决策
"""

from typing import Any, Dict, Optional
from langgraph.graph import END, StateGraph, START
import structlog

from tradingagents.agents.utils.agent_states import AgentState

logger = structlog.get_logger(__name__)


class DebateSubGraph:
    """Bull vs Bear 辩论子图

    封装投资辩论的完整流程：
    1. Bull Researcher 提出看涨观点
    2. Bear Researcher 反驳
    3. 多轮对抗（max_debate_rounds 控制）
    4. Research Manager 汇总裁决

    辩论轮转逻辑：
    - count < 2 * max_rounds: 继续辩论
    - Bull 回合后 → Bear 接手
    - Bear 回合后 → Bull 接手
    - 达到上限 → Research Manager 裁决
    """

    def __init__(
        self,
        quick_thinking_llm,
        deep_thinking_llm,
        bull_memory,
        bear_memory,
        invest_judge_memory,
        max_debate_rounds: int = 1,
    ):
        """
        Args:
            quick_thinking_llm: 快速推理 LLM（Bull/Bear）
            deep_thinking_llm: 深度推理 LLM（Research Manager）
            bull_memory: Bull Researcher 记忆
            bear_memory: Bear Researcher 记忆
            invest_judge_memory: Research Manager 记忆
            max_debate_rounds: 辩论轮数（每轮包含 Bull+Bear 各一次发言）
        """
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.invest_judge_memory = invest_judge_memory
        self.max_debate_rounds = max_debate_rounds

    def _should_continue_debate(self, state: AgentState) -> str:
        """辩论轮转逻辑

        Returns:
            下一个节点名: "Bear", "Bull", 或 "Manager"
        """
        debate_state = state.get("investment_debate_state", {})
        count = debate_state.get("count", 0)
        current_response = debate_state.get("current_response", "")

        if count >= 2 * self.max_debate_rounds:
            logger.info(
                "DebateSubGraph: debate complete",
                rounds=count,
                max_rounds=self.max_debate_rounds,
            )
            return "Manager"

        if current_response.startswith("Bull"):
            return "Bear"
        return "Bull"

    def compile(self) -> Any:
        """编译辩论子图

        Returns:
            编译后的 LangGraph CompiledGraph
        """
        # 延迟导入避免循环依赖
        from tradingagents.agents import (
            create_bull_researcher,
            create_bear_researcher,
            create_research_manager,
        )

        bull_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )

        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("Bull", bull_node)
        workflow.add_node("Bear", bear_node)
        workflow.add_node("Manager", manager_node)

        # 边定义
        # START -> Bull（辩论总是从 Bull 开始）
        workflow.add_edge(START, "Bull")

        # Bull <-> Bear 条件轮转
        workflow.add_conditional_edges(
            "Bull",
            self._should_continue_debate,
            {
                "Bear": "Bear",
                "Manager": "Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear",
            self._should_continue_debate,
            {
                "Bull": "Bull",
                "Manager": "Manager",
            },
        )

        # Manager -> END
        workflow.add_edge("Manager", END)

        logger.info(
            "DebateSubGraph compiled",
            max_rounds=self.max_debate_rounds,
        )

        return workflow.compile()
