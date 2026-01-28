"""Macro Analyst - 宏观分析师

分析宏观经济环境和对股票的影响，返回结构化输出。
"""

from langchain_core.prompts import ChatPromptTemplate
import structlog

from services.prompt_manager import prompt_manager
from tradingagents.agents.utils.output_schemas import MacroAnalystOutput

logger = structlog.get_logger(__name__)


def create_macro_analyst(llm):
    """创建 Macro Analyst 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        macro_analyst_node: LangGraph 异步节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a macro analyst. Generate a structured macroeconomic analysis report. "
            "Focus on factors that affect the specific stock being analyzed."
        ),
        (
            "user",
            "Stock: {symbol}\n\nMacroeconomic Context:\n{macro_context}\n\n"
            "Please provide a structured macro analysis."
        ),
    ])

    async def macro_analyst_node(state):
        """Macro Analyst 异步节点函数"""
        symbol = state.get("company_of_interest", "Unknown")
        logger.info("Macro analyst analyzing", symbol=symbol)

        # 获取 prompt 数据
        prompt_data = prompt_manager.get_prompt("macro_analyst", {"symbol": symbol})

        # 第一阶段：获取原始宏观分析
        raw_prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system"]),
            ("user", "请开始分析。")
        ])

        raw_chain = raw_prompt | llm
        raw_response = await raw_chain.ainvoke({})

        # 第二阶段：结构化输出
        try:
            structured_llm = llm.with_structured_output(MacroAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = await structured_chain.ainvoke({
                "symbol": symbol,
                "macro_context": raw_response.content,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Macro analyst structured output generated",
                symbol=symbol,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                environment=structured_result.environment,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
                symbol=symbol,
            )
            report = raw_response.content

        return {
            "macro_report": report
        }

    return macro_analyst_node
