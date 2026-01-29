"""Conservative Risk Debater - 保守风险分析师

在风险辩论中主张低风险保守策略，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import RiskDebaterOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """As the Safe/Conservative Risk Analyst, your primary objective is to protect assets, minimize volatility, and ensure steady, reliable growth.

Your task is to actively counter the arguments of the Risky and Neutral Analysts, highlighting where their views may overlook potential threats. Build a convincing case for a low-risk approach.

Question their optimism and emphasize potential downsides they may have overlooked. Speak conversationally without special formatting."""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("conservative_debator")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default conservative debator prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_safe_debator(llm):
    """创建 Safe Debater 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        safe_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a conservative risk analyst. Generate a structured argument for risk mitigation and capital preservation. "
            "Focus on potential downsides and counter aggressive arguments."
        ),
        (
            "user",
            "Safe Argument Context:\n{argument_context}\n\n"
            "Please provide a structured conservative risk argument."
        ),
    ])

    def safe_node(state) -> dict:
        """Safe Debater 节点函数"""
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 获取系统提示词并构建原始 prompt
        system_prompt = _get_system_prompt()
        raw_prompt = f"""{system_prompt}

Here is the trader's decision:
{trader_decision}

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Conversation history: {history}
Last risky analyst argument: {current_risky_response}
Last neutral analyst argument: {current_neutral_response}

If there are no responses from others, present your point without hallucinating."""

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
            argument = f"Safe Analyst: {raw_argument}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Safe debater structured output generated",
                position=structured_result.position,
                confidence=structured_result.confidence,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            argument = f"Safe Analyst: {raw_argument}"

        # 更新风险辩论状态
        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get("current_risky_response", ""),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
