"""Bull Researcher - 多头研究员

负责在投资辩论中为看涨立场辩护，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import ResearcherOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are a Bull Analyst advocating for investing in the stock. Your task is to build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators.

Key points to focus on:
- Growth Potential: Highlight the company's market opportunities, revenue projections, and scalability.
- Competitive Advantages: Emphasize factors like unique products, strong branding, or dominant market positioning.
- Positive Indicators: Use financial health, industry trends, and recent positive news as evidence.
- Bear Counterpoints: Critically analyze the bear argument with specific data and sound reasoning.
- Historical Learning: Consider the historical analysis patterns and lessons learned.

Deliver a compelling bull argument that refutes the bear's concerns."""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("bull_researcher")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default bull researcher prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_bull_researcher(llm, memory):
    """创建 Bull Researcher 节点

    Args:
        llm: LangChain LLM 实例
        memory: FinancialSituationMemory 实例

    Returns:
        bull_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a Bull Analyst. Generate a structured bullish argument. "
            "Focus on growth potential, competitive advantages, and positive indicators."
        ),
        (
            "user",
            "Bull Argument Context:\n{argument_context}\n\n"
            "Please provide a structured bullish analysis."
        ),
    ])

    def bull_node(state) -> dict:
        """Bull Researcher 节点函数"""
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

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

        # 从配置服务获取系统提示词
        system_prompt = _get_system_prompt()

        # 构建完整 prompt（系统提示 + 上下文数据）
        raw_prompt = f"""{system_prompt}

Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history: {history}
Last bear argument: {current_response}
{reflection_context}
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

            # 组合格式化的论点（保持向后兼容）
            argument = f"Bull Analyst: {raw_argument}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Bull researcher structured output generated",
                thesis=structured_result.thesis[:50] + "...",
                confidence=structured_result.confidence,
                num_arguments=len(structured_result.arguments),
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            argument = f"Bull Analyst: {raw_argument}"

        # 更新辩论状态
        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
