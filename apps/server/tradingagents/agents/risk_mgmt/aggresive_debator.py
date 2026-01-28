"""Aggressive Risk Debater - 激进风险分析师

在风险辩论中主张高风险高回报策略，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import RiskDebaterOutput

logger = structlog.get_logger(__name__)


def create_risky_debator(llm):
    """创建 Risky Debater 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        risky_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an aggressive risk analyst. Generate a structured argument for high-risk high-reward strategies. "
            "Focus on growth potential and counter conservative arguments."
        ),
        (
            "user",
            "Risky Argument Context:\n{argument_context}\n\n"
            "Please provide a structured aggressive risk argument."
        ),
    ])

    def risky_node(state) -> dict:
        """Risky Debater 节点函数"""
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 原始 prompt
        raw_prompt = f"""As the Risky Risk Analyst, your role is to actively champion high-reward, high-risk opportunities, emphasizing bold strategies and competitive advantages.

Here is the trader's decision:
{trader_decision}

Your task is to create a compelling case for the trader's decision by questioning and critiquing the conservative and neutral stances. Use data-driven rebuttals and persuasive reasoning.

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Conversation history: {history}
Last conservative analyst argument: {current_safe_response}
Last neutral analyst argument: {current_neutral_response}

If there are no responses from others, present your point without hallucinating.

Challenge each counterpoint to underscore why a high-risk approach is optimal. Speak conversationally without special formatting."""

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
            argument = f"Risky Analyst: {raw_argument}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Risky debater structured output generated",
                position=structured_result.position,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            argument = f"Risky Analyst: {raw_argument}"

        # 更新风险辩论状态
        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risky_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Risky",
            "current_risky_response": argument,
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risky_node
