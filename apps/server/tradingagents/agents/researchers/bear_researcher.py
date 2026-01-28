"""Bear Researcher - 空头研究员

负责在投资辩论中为看跌立场辩护，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import ResearcherOutput

logger = structlog.get_logger(__name__)


def create_bear_researcher(llm, memory):
    """创建 Bear Researcher 节点

    Args:
        llm: LangChain LLM 实例
        memory: FinancialSituationMemory 实例

    Returns:
        bear_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a Bear Analyst. Generate a structured bearish argument. "
            "Focus on risks, challenges, competitive weaknesses, and negative indicators."
        ),
        (
            "user",
            "Bear Argument Context:\n{argument_context}\n\n"
            "Please provide a structured bearish analysis."
        ),
    ])

    def bear_node(state) -> dict:
        """Bear Researcher 节点函数"""
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # 历史反思信息
        historical_reflection = state.get("historical_reflection", "")

        # 获取向量记忆
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"

        # 组合反思上下文
        reflection_context = ""
        if historical_reflection:
            reflection_context = f"\n\n=== Historical Analysis Reflection ===\n{historical_reflection}\n"
        if past_memory_str:
            reflection_context += f"\n=== Past Recommendations ===\n{past_memory_str}"

        # 原始 prompt
        raw_prompt = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators.

Key points to focus on:
- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news.
- Bull Counterpoints: Critically analyze the bull argument, exposing weaknesses or over-optimistic assumptions.
- Historical Learning: Consider the historical analysis patterns and lessons learned.

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history: {history}
Last bull argument: {current_response}
{reflection_context}

Deliver a compelling bear argument that refutes the bull's claims.
"""

        # 第一阶段：获取原始辩论内容
        raw_response = llm.invoke(raw_prompt)
        raw_argument = raw_response.content

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(ResearcherOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "argument_context": raw_argument,
            })

            # 将结构化结果转为 JSON
            structured_json = structured_result.model_dump_json(indent=2)

            # 组合格式化的论点
            argument = f"Bear Analyst: {raw_argument}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Bear researcher structured output generated",
                thesis=structured_result.thesis[:50] + "...",
                confidence=structured_result.confidence,
                num_arguments=len(structured_result.arguments),
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            argument = f"Bear Analyst: {raw_argument}"

        # 更新辩论状态
        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
