"""Neutral Risk Debater - 中立风险分析师

在风险辩论中提供平衡视角，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import RiskDebaterOutput

logger = structlog.get_logger(__name__)


def create_neutral_debator(llm):
    """创建 Neutral Debater 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        neutral_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a neutral risk analyst. Generate a structured balanced argument. "
            "Weigh both potential benefits and risks, offering a moderate perspective."
        ),
        (
            "user",
            "Neutral Argument Context:\n{argument_context}\n\n"
            "Please provide a structured balanced risk argument."
        ),
    ])

    def neutral_node(state) -> dict:
        """Neutral Debater 节点函数"""
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 原始 prompt
        raw_prompt = f"""As the Neutral Risk Analyst, your role is to provide a balanced perspective, weighing both the potential benefits and risks of the trader's decision.

Here is the trader's decision:
{trader_decision}

Your task is to challenge both the Risky and Safe Analysts, pointing out where each may be overly optimistic or overly cautious. Support a moderate, sustainable strategy.

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Conversation history: {history}
Last risky analyst argument: {current_risky_response}
Last safe analyst argument: {current_safe_response}

If there are no responses from others, present your point without hallucinating.

Analyze both sides critically, showing why a balanced view leads to the most reliable outcomes. Speak conversationally without special formatting."""

        # 第一阶段：获取原始论点
        raw_response = llm.invoke(raw_prompt)
        raw_argument = raw_response.content

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(RiskDebaterOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "argument_context": raw_argument,
            })

            structured_json = structured_result.model_dump_json(indent=2)
            argument = f"Neutral Analyst: {raw_argument}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Neutral debater structured output generated",
                position=structured_result.position,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            argument = f"Neutral Analyst: {raw_argument}"

        # 更新风险辩论状态
        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_risky_response": risk_debate_state.get("current_risky_response", ""),
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
