"""Risk Manager - 风险经理

评估风险辩论并做出最终交易决策，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import RiskManagerOutput

logger = structlog.get_logger(__name__)


def create_risk_manager(llm, memory):
    """创建 Risk Manager 节点

    Args:
        llm: LangChain LLM 实例
        memory: FinancialSituationMemory 实例

    Returns:
        risk_manager_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a risk manager. Generate a structured final trade decision with risk assessment. "
            "Include risk score, volatility status, and risk mitigation measures."
        ),
        (
            "user",
            "Risk Decision Context:\n{decision_context}\n\n"
            "Please provide a structured risk-adjusted trade decision."
        ),
    ])

    def risk_manager_node(state) -> dict:
        """Risk Manager 节点函数"""
        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        # 获取向量记忆
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"

        # 原始 prompt
        raw_prompt = f"""As the Risk Management Judge and Debate Facilitator, your goal is to evaluate the debate between three risk analysts—Risky, Neutral, and Safe/Conservative—and determine the best course of action for the trader.

Your decision must result in a clear recommendation: Buy, Sell, or Hold. Choose Hold only if strongly justified by specific arguments, not as a fallback when all sides seem valid.

Guidelines for Decision-Making:
1. **Summarize Key Arguments**: Extract the strongest points from each analyst.
2. **Provide Rationale**: Support your recommendation with direct quotes and counterarguments.
3. **Refine the Trader's Plan**: Start with the trader's original plan, **{trader_plan}**, and adjust based on risk insights.
4. **Learn from Past Mistakes**: Use lessons from **{past_memory_str}** to improve this decision.

Deliverables:
- A clear and actionable recommendation: Buy, Sell, or Hold.
- Detailed reasoning anchored in the debate and past reflections.

---

**Analysts Debate History:**
{history}

---

Focus on actionable insights and continuous improvement."""

        # 第一阶段：获取原始决策
        raw_response = llm.invoke(raw_prompt)
        raw_content = raw_response.content

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(RiskManagerOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "decision_context": raw_content,
            })

            # 将结构化结果转为 JSON
            structured_json = structured_result.model_dump_json(indent=2)

            # 组合最终输出
            final_content = f"{raw_content}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Risk manager structured output generated",
                final_decision=structured_result.final_decision,
                risk_score=structured_result.risk_assessment.score,
                verdict=structured_result.risk_assessment.verdict,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            final_content = raw_content

        # 更新风险辩论状态
        new_risk_debate_state = {
            "judge_decision": final_content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_content,
        }

    return risk_manager_node
