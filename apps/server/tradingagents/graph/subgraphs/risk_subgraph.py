"""风险评估子图 (RiskSubGraph)

封装三方风险辩论逻辑：
- Risky Analyst: 激进观点
- Safe Analyst: 保守观点
- Neutral Analyst: 中立观点
- Risk Judge: 最终裁决

私有状态：
- risk_debate_state: 风险辩论进度和历史

输出：
- final_trade_decision: Risk Judge 的最终决策
"""

from typing import Any, Optional
from langgraph.graph import END, StateGraph, START
import structlog

from tradingagents.agents.utils.agent_states import AgentState

logger = structlog.get_logger(__name__)


class RiskSubGraph:
    """风险评估三方辩论子图

    封装风险评估的完整流程：
    1. Risky Analyst 提出激进观点
    2. Safe Analyst 提出保守观点
    3. Neutral Analyst 提供中立评价
    4. 多轮轮转（max_risk_discuss_rounds 控制）
    5. Risk Judge 最终裁决

    轮转逻辑：
    - Risky -> Safe -> Neutral -> Risky -> ...
    - count >= 3 * max_rounds 时 -> Risk Judge 裁决
    """

    def __init__(
        self,
        quick_thinking_llm,
        deep_thinking_llm,
        risk_manager_memory,
        max_risk_discuss_rounds: int = 1,
    ):
        """
        Args:
            quick_thinking_llm: 快速推理 LLM（三方分析师）
            deep_thinking_llm: 深度推理 LLM（Risk Judge）
            risk_manager_memory: Risk Manager 记忆
            max_risk_discuss_rounds: 风险讨论轮数（每轮3人各发言一次）
        """
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.risk_manager_memory = risk_manager_memory
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def _should_continue_risk(self, state: AgentState) -> str:
        """风险讨论轮转逻辑

        Returns:
            下一个节点名: "Risky", "Safe", "Neutral", 或 "Judge"
        """
        risk_state = state.get("risk_debate_state", {})
        count = risk_state.get("count", 0)
        latest_speaker = risk_state.get("latest_speaker", "")

        if count >= 3 * self.max_risk_discuss_rounds:
            logger.info(
                "RiskSubGraph: discussion complete",
                rounds=count,
                max_rounds=self.max_risk_discuss_rounds,
            )
            return "Judge"

        if latest_speaker.startswith("Risky"):
            return "Safe"
        if latest_speaker.startswith("Safe"):
            return "Neutral"
        return "Risky"

    def compile(self) -> Any:
        """编译风险评估子图

        Returns:
            编译后的 LangGraph CompiledGraph
        """
        # 延迟导入避免循环依赖
        from tradingagents.agents import (
            create_risky_debator,
            create_neutral_debator,
            create_safe_debator,
            create_risk_manager,
        )

        risky_node = create_risky_debator(self.quick_thinking_llm)
        safe_node = create_safe_debator(self.quick_thinking_llm)
        neutral_node = create_neutral_debator(self.quick_thinking_llm)
        judge_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("Risky", risky_node)
        workflow.add_node("Safe", safe_node)
        workflow.add_node("Neutral", neutral_node)
        workflow.add_node("Judge", judge_node)

        # 边定义
        # START -> Risky（总是从激进方开始）
        workflow.add_edge(START, "Risky")

        # 三方轮转条件边
        workflow.add_conditional_edges(
            "Risky",
            self._should_continue_risk,
            {
                "Safe": "Safe",
                "Judge": "Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe",
            self._should_continue_risk,
            {
                "Neutral": "Neutral",
                "Judge": "Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral",
            self._should_continue_risk,
            {
                "Risky": "Risky",
                "Judge": "Judge",
            },
        )

        # Judge -> END
        workflow.add_edge("Judge", END)

        logger.info(
            "RiskSubGraph compiled",
            max_rounds=self.max_risk_discuss_rounds,
        )

        return workflow.compile()
