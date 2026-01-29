"""Trader - 交易员

基于投资计划制定交易决策，返回结构化输出。
"""

import functools
from langchain_core.prompts import ChatPromptTemplate
import structlog

from tradingagents.agents.utils.output_schemas import TraderOutput

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation."""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("trader")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default trader prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_trader(llm, memory):
    """创建 Trader 节点

    Args:
        llm: LangChain LLM 实例
        memory: FinancialSituationMemory 实例

    Returns:
        trader_node: LangGraph 节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a trader. Generate a structured trade decision. "
            "Include entry zone, target price, stop loss, and position sizing."
        ),
        (
            "user",
            "Trading Context:\n{trading_context}\n\n"
            "Please provide a structured trade decision."
        ),
    ])

    def trader_node(state, name):
        """Trader 节点函数"""
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # 获取向量记忆
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for rec in past_memories:
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        # 获取系统提示词并构建原始消息
        system_prompt = _get_system_prompt()
        messages = [
            {
                "role": "system",
                "content": f"""{system_prompt}

Learn from past decisions:
{past_memory_str}""",
            },
            {
                "role": "user",
                "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
            },
        ]

        # 第一阶段：获取原始决策
        raw_result = llm.invoke(messages)
        raw_content = raw_result.content

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(TraderOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "trading_context": raw_content,
            })

            # 将结构化结果转为 JSON
            structured_json = structured_result.model_dump_json(indent=2)

            # 组合最终输出（保持向后兼容）
            final_content = f"{raw_content}\n\n[Structured Output]\n{structured_json}"

            logger.info(
                "Trader structured output generated",
                decision=structured_result.decision,
                confidence=structured_result.confidence,
                position_size=structured_result.position_size,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
            )
            final_content = raw_content

        return {
            "messages": [raw_result],
            "trader_investment_plan": final_content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
